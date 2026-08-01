import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from app.config import config
from app.database import Database
from services.user_service import UserService
from services.subscription_service import SubscriptionService
from services.payment_service import PaymentService
from services.whitelist_service import WhitelistService
from services.access_service import AccessService
from services.calculator_service import CalculatorService
from repositories.user_repository import UserRepository
from repositories.subscription_repository import SubscriptionRepository
from repositories.whitelist_repository import WhitelistRepository
from handlers.menu_handler import MenuHandler
from handlers.payment_handler import PaymentHandler
from handlers.calculator_handler import CalculatorHandler
from handlers.admin_handler import AdminHandler
from models.whitelist import WhitelistRole
from utils.logger import setup_logger

logger = setup_logger()


class PianoMasterBot:
    """Основной класс бота"""

    def __init__(self):
        # Проверяем конфигурацию
        if not config.validate():
            logger.error("Configuration validation failed. Please check .env file")
            logger.error(f"BOT_TOKEN: {'✓' if config.BOT_TOKEN else '✗'}")
            logger.error(f"YOOKASSA_SHOP_ID: {'✓' if config.YOOKASSA_SHOP_ID else '✗'}")
            logger.error(f"YOOKASSA_SECRET_KEY: {'✓' if config.YOOKASSA_SECRET_KEY else '✗'}")
            raise ValueError("Invalid configuration")

        # Инициализация базы данных
        try:
            self.db = Database(config.db_path)
            logger.info(f"Database connected: {config.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

        # Инициализация репозиториев
        self.user_repo = UserRepository(self.db)
        self.subscription_repo = SubscriptionRepository(self.db)
        self.whitelist_repo = WhitelistRepository(self.db)

        # Инициализация сервисов
        self.user_service = UserService(self.user_repo)
        self.subscription_service = SubscriptionService(self.subscription_repo)
        self.whitelist_service = WhitelistService(self.whitelist_repo, self.user_repo)
        self.access_service = AccessService(self.subscription_service, self.whitelist_service)
        self.payment_service = PaymentService(
            config.YOOKASSA_SHOP_ID,
            config.YOOKASSA_SECRET_KEY,
            self.subscription_service,
            self.user_service
        )
        self.calculator_service = CalculatorService()

        # Инициализация обработчиков
        self.menu_handler = MenuHandler(self.access_service, self.user_service)
        self.payment_handler = PaymentHandler(
            self.payment_service,
            self.subscription_service,
            self.user_service
        )
        self.calculator_handler = CalculatorHandler(
            self.calculator_service,
            self.access_service,
            self.user_service
        )
        self.admin_handler = AdminHandler(self.whitelist_service, self.user_service)

        # Инициализация приложения
        self.app = Application.builder().token(config.BOT_TOKEN).build()
        self._setup_handlers()

        # Проверяем и инициализируем белый список
        self._initialize_whitelist()

        logger.info("Bot initialized successfully")

    def _initialize_whitelist(self):
        """Инициализация белого списка"""
        try:
            users = self.whitelist_service.get_all_whitelist_users()

            if not users:
                logger.warning("⚠️ Белый список пуст! Добавляем администраторов...")

                added_count = 0
                for admin_id in config.ADMIN_IDS:
                    try:
                        user = self.user_service.get_or_create(
                            telegram_id=admin_id,
                            username=None,
                            first_name=f"Admin_{admin_id}",
                            last_name=None
                        )

                        if not self.whitelist_service.is_in_whitelist(user):
                            self.whitelist_service.add_to_whitelist(
                                user=user,
                                role=WhitelistRole.FOUNDER,
                                reason="Автоматическое добавление администратора",
                                added_by=user,
                                days=None
                            )
                            added_count += 1
                            logger.info(f"✅ Администратор {admin_id} добавлен в белый список")
                    except Exception as e:
                        logger.error(f"Failed to add admin {admin_id}: {e}")

                if added_count > 0:
                    logger.info(f"✅ Добавлено {added_count} администраторов в белый список")
                else:
                    logger.warning("⚠️ Не удалось добавить администраторов в белый список")
            else:
                logger.info(f"✅ Белый список содержит {len(users)} пользователей")

                for user in users:
                    entry = self.whitelist_service.get_by_user(user)
                    if entry:
                        logger.info(f"  • {user.telegram_id} - {entry.role.display_name}")

        except Exception as e:
            logger.error(f"Error initializing whitelist: {e}")

    def _setup_handlers(self):
        """Настройка обработчиков"""
        # Команды
        self.app.add_handler(CommandHandler("start", self.menu_handler.handle))
        self.app.add_handler(CommandHandler("menu", self.menu_handler.handle))
        self.app.add_handler(CommandHandler("admin", self.admin_handler.handle))

        # Callback handlers
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))

        # Message handlers для админ-функций
        self.app.add_handler(MessageHandler(
            filters.Regex(r'^\d+\s+(founder|expert|vip|lifetime|temporary)\s+.+$'),
            self.admin_handler.handle_add_input
        ))
        self.app.add_handler(MessageHandler(
            filters.Regex(r'^\d+$'),
            self.admin_handler.handle_remove_input
        ))

        # Message handler для калькулятора
        self.app.add_handler(MessageHandler(
            filters.Regex(r'^[12]\s+[\d.]+'),
            self.calculator_handler.calculate
        ))

        # Message handler для отмены операций
        self.app.add_handler(MessageHandler(
            filters.Regex(r'^/cancel$'),
            self._handle_cancel
        ))

        # Добавляем обработчик ошибок
        self.app.add_error_handler(self._error_handler)

    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик отмены операций"""
        user = update.effective_user

        if context.user_data.get('waiting_for_whitelist_add'):
            context.user_data.pop('waiting_for_whitelist_add', None)
            self.admin_handler._waiting_for_add.pop(user.id, None)
            await update.message.reply_text(
                "❌ Добавление в белый список отменено",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )
        elif context.user_data.get('waiting_for_whitelist_remove'):
            context.user_data.pop('waiting_for_whitelist_remove', None)
            self.admin_handler._waiting_for_remove.pop(user.id, None)
            await update.message.reply_text(
                "❌ Удаление из белого списка отменено",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )
        else:
            await update.message.reply_text(
                "Нет активных операций для отмены",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )

    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        error_str = str(context.error)
        logger.error(f"Update {update} caused error: {error_str}")

        # Обработка конфликта
        if "Conflict" in error_str:
            logger.error("⚠️ Конфликт бота! Возможно, запущен другой экземпляр.")
            try:
                if update and update.effective_user:
                    await context.bot.send_message(
                        chat_id=update.effective_user.id,
                        text="⚠️ Бот временно недоступен. Попробуйте позже."
                    )
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
            return

        # Обработка ошибок парсинга
        if "Can't parse entities" in error_str:
            logger.warning("⚠️ Ошибка форматирования текста. Используйте обычный текст.")
            try:
                if update and update.callback_query:
                    await update.callback_query.answer("Ошибка форматирования")
            except Exception:
                pass
            return

        # Обработка других ошибок
        try:
            if update and update.effective_user:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="❌ Произошла ошибка. Пожалуйста, попробуйте позже."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback-запросов"""
        query = update.callback_query
        data = query.data

        try:
            if data == "menu":
                await self.menu_handler.handle(update, context)
            elif data == "about":
                await self._show_about(update, context)
            elif data == "subscribe":
                await self.payment_handler.handle(update, context)
            elif data.startswith("check_payment_"):
                await self.payment_handler.check_payment(update, context)
            elif data == "calculator":
                await self.calculator_handler.handle(update, context)
            elif data == "status":
                await self._show_status(update, context)
            elif data == "help":
                await self._show_help(update, context)
            elif data == "admin_menu":
                await self.admin_handler.handle(update, context)
            elif data == "admin_whitelist_list":
                await self.admin_handler.show_list(update, context)
            elif data == "admin_whitelist_add":
                await self.admin_handler.add_user(update, context)
            elif data == "admin_whitelist_remove":
                await self.admin_handler.remove_user(update, context)
            elif data == "admin_whitelist_stats":
                await self.admin_handler.show_stats(update, context)
            elif data == "admin_self_add":
                await self.admin_handler.add_self(update, context)
            else:
                await query.answer("Неизвестная команда")

        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            try:
                await query.answer("Произошла ошибка. Попробуйте позже.")
            except Exception:
                pass

    async def _show_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает информацию о проекте (без Markdown)"""
        query = update.callback_query
        await query.answer()

        about_text = (
            "🎹 О проекте\n\n"
            "PianoMaster Club — это закрытое сообщество фортепианных мастеров экстра-класса.\n\n"
            "Что мы предлагаем:\n"
            "• Эксклюзивные материалы по ремонту и реставрации\n"
            "• Общение с ведущими мастерами\n"
            "• Калькулятор для изготовления басовых струн\n"
            "• Закрытые мастер-классы и вебинары\n\n"
            "Для кого:\n"
            "• Профессиональных мастеров\n"
            "• Техников по настройке\n"
            "• Реставраторов фортепиано\n"
            "• Производителей инструментов"
        )

        keyboard = [
            [
                InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
                InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
            ],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
        ]

        await query.edit_message_text(
            about_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает помощь (без Markdown)"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        is_admin = user.id in config.ADMIN_IDS

        # Собираем текст построчно
        lines = [
            "❓ Помощь по PianoMasterClub",
            "",
            "🤖 Бот для фортепианных мастеров экстра-класса",
            "",
            "📋 Основные разделы:",
            "• 📖 О проекте — информация о клубе",
            "• 🎹 Присоединиться — оформление подписки",
            "• 🔧 Калькулятор струн — расчет басовых струн",
            "• 🔄 Статус доступа — проверка подписки/белого списка",
            "• 📢 Канал — закрытый канал мастеров",
            "• 💬 Чат — общение с коллегами",
            "",
            "📝 Команды:",
            "/start или /menu — Главное меню",
            "/cancel — Отмена текущей операции",
        ]

        if is_admin:
            lines.extend([
                "",
                "👑 Администратор:",
                "/admin — Панель управления",
                "• Добавление/удаление из белого списка",
                "• Просмотр статистики",
            ])

        lines.extend([
            "",
            "💡 Советы:",
            "• Для расчета струн введите: тип сердечник длина общий_диаметр",
            "• Пример: 1 1.2 850 2.5 — одинарная навивка",
            "• Пример: 2 1.2 850 2.5 — двойная навивка",
            "",
            "📧 Поддержка:",
            "• Администратор: @DenPotorsky",
            "• Email: denis-s2@yandex.ru",
        ])

        help_text = "\n".join(lines)

        keyboard = [
            [
                InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
                InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
            ],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="menu")]
        ]

        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _show_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статус доступа (без Markdown)"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        db_user = self.user_service.get_by_telegram_id(user.id)

        if not db_user:
            await query.edit_message_text(
                "❌ Пользователь не найден",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                ])
            )
            return

        has_access, access_type = self.access_service.has_access(db_user)
        access_desc = self.access_service.get_access_description(db_user)

        is_admin = user.id in config.ADMIN_IDS

        lines = []

        if has_access:
            lines.append("✅ Доступ открыт")
            lines.append("")
            lines.append(access_desc)
            lines.append("")

            if access_type.startswith("whitelist_"):
                role_str = access_type.replace("whitelist_", "")
                try:
                    role = WhitelistRole(role_str)
                    lines.append(f"Роль: {role.display_name}")

                    entry = self.whitelist_service.get_by_user(db_user)
                    if entry and entry.expires_at:
                        lines.append(f"Действует до: {entry.expires_at.strftime('%d.%m.%Y %H:%M')}")
                    if entry and entry.reason:
                        lines.append(f"Причина: {entry.reason}")
                except ValueError:
                    pass
            else:
                subscription = self.subscription_service.get_by_user(db_user)
                if subscription:
                    lines.append(f"Активирована: {subscription.starts_at.strftime('%d.%m.%Y')}")
                    lines.append(f"Истекает: {subscription.expires_at.strftime('%d.%m.%Y')}")
                    lines.append(f"Осталось дней: {subscription.days_left}")
        else:
            lines.extend([
                "❌ Доступ закрыт",
                "",
                "Для доступа к функциям клуба необходимо:",
                "• Оформить подписку",
                "• Или быть в белом списке",
                "",
                f"Ваш ID: {user.id}"
            ])

        status_text = "\n".join(lines)

        keyboard = []
        if not has_access:
            keyboard.append([InlineKeyboardButton("🎹 Присоединиться", callback_data="subscribe")])

        if has_access:
            keyboard.append([
                InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
                InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
            ])

        if is_admin:
            keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data="admin_menu")])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="menu")])

        await query.edit_message_text(
            status_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _check_expired_subscriptions(self):
        """Фоновая проверка истекших подписок и белого списка"""
        while True:
            try:
                expired_subscriptions = self.subscription_service.check_expired_subscriptions()
                if expired_subscriptions:
                    logger.info(f"Deactivated {len(expired_subscriptions)} expired subscriptions")

                    for user_id in expired_subscriptions:
                        user = self.user_service.get(user_id)
                        if user:
                            try:
                                await self.app.bot.send_message(
                                    user.telegram_id,
                                    "⏰ Подписка истекла\n\n"
                                    "Ваш доступ к PianoMaster Club завершен.\n"
                                    "Для продления нажмите /menu и выберите «Присоединиться»"
                                )
                            except Exception as e:
                                logger.error(f"Failed to notify user {user.telegram_id}: {e}")

                expired_whitelist = self.whitelist_service.check_expired_entries()
                if expired_whitelist:
                    logger.info(f"Deactivated {len(expired_whitelist)} expired whitelist entries")

                    for entry in expired_whitelist:
                        user = self.user_service.get(entry.user_id)
                        if user:
                            try:
                                await self.app.bot.send_message(
                                    user.telegram_id,
                                    "⏰ Временный доступ истек\n\n"
                                    "Ваш доступ по белому списку завершен.\n"
                                    "Для продолжения оформите подписку или обратитесь к администратору."
                                )
                            except Exception as e:
                                logger.error(f"Failed to notify whitelist user {user.telegram_id}: {e}")

                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"Error in subscription checker: {e}")
                await asyncio.sleep(300)

    async def run(self):
        """Запуск бота"""
        if not config.validate():
            logger.error("Configuration validation failed. Please check .env file")
            return

        # Удаляем вебхук при запуске
        try:
            await self.app.bot.delete_webhook()
            logger.info("✅ Webhook deleted")
        except Exception as e:
            logger.warning(f"Webhook deletion failed: {e}")

        # Запускаем фоновый процесс проверки
        asyncio.create_task(self._check_expired_subscriptions())

        # Запускаем бота
        logger.info("Starting PianoMaster Club Bot...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        logger.info("✅ Bot is running!")

        # Держим бота активным
        while True:
            await asyncio.sleep(1)