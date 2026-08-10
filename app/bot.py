"""
Главный класс бота PianoMaster Club с автоматическим доступом
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
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
from handlers.age import AgeHandler
from age_detector import AgeDetector
from age_database import AgeDatabase
from models.whitelist import WhitelistRole
from utils.logger import logger


class PianoMasterBot:
    """Основной класс бота с автоматической активацией доступа"""

    def __init__(self):
        # Проверка конфигурации
        if not config.validate():
            logger.error("Configuration validation failed. Please check .env file")
            logger.error(f"BOT_TOKEN: {'✓' if config.BOT_TOKEN else '✗'}")
            logger.error(f"YOOKASSA_SHOP_ID: {'✓' if config.YOOKASSA_SHOP_ID else '✗'}")
            logger.error(f"YOOKASSA_SECRET_KEY: {'✓' if config.YOOKASSA_SECRET_KEY else '✗'}")
            raise ValueError("Invalid configuration")

        # Подключение к основной базе данных
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

        # Инициализация базы данных для определения возраста фортепиано
        # В __init__ методе:
        AGE_DB_PATH = config.AGE_DB_PATH  # Используем из конфига
        try:
            self.age_db = AgeDatabase(AGE_DB_PATH)
            logger.info(f"Age database connected: {AGE_DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to connect to age database: {e}")
            self.age_db = None

        self.age_detector = AgeDetector(self.age_db) if self.age_db else None

        # Инициализация обработчиков
        self.menu_handler = MenuHandler(self.access_service, self.user_service)
        self.payment_handler = PaymentHandler(
            self.payment_service,
            self.subscription_service,
            self.user_service
        )
        self.calculator_handler = CalculatorHandler(self.access_service, self.user_service)
        self.admin_handler = AdminHandler(self.whitelist_service, self.user_service)
        self.age_handler = AgeHandler(self.age_detector, self.access_service, self.user_service) if self.age_detector else None

        # Инициализация приложения Telegram
        self.app = Application.builder().token(config.BOT_TOKEN).build()
        self._setup_handlers()
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
        """Настройка всех обработчиков"""
        # Команды
        self.app.add_handler(CommandHandler("start", self.menu_handler.handle))
        self.app.add_handler(CommandHandler("menu", self.menu_handler.handle))
        self.app.add_handler(CommandHandler("admin", self.admin_handler.handle))
        self.app.add_handler(CommandHandler("calc", self.calculator_handler.handle))

        if self.age_handler:
            self.app.add_handler(CommandHandler("age", self.age_handler.handle))

        # Калькулятор (ConversationHandler)
        conv_handler = self.calculator_handler.get_conversation_handler()
        self.app.add_handler(conv_handler)

        # Возраст фортепиано (ConversationHandler)
        if self.age_handler:
            age_conv_handler = self.age_handler.get_conversation_handler()
            self.app.add_handler(age_conv_handler)

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

        # Message handler для отмены операций
        self.app.add_handler(MessageHandler(
            filters.Regex(r'^/cancel$'),
            self._handle_cancel
        ))

        # Добавляем обработчик ошибок
        self.app.add_error_handler(self._error_handler)

    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /cancel"""
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
        """Глобальный обработчик ошибок"""
        error_str = str(context.error)

        if "Conflict" in error_str:
            logger.debug(f"Ignored Conflict error: {error_str}")
            return

        if "Can't parse entities" in error_str:
            logger.warning(f"Markdown parse error: {error_str}")
            try:
                if update and update.callback_query:
                    await update.callback_query.answer("Ошибка форматирования")
            except Exception:
                pass
            return

        logger.error(f"Update {update} caused error: {error_str}")

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
        logger.info(f"📩 Получен callback: {data}")

        try:
            if data == "menu":
                await self.menu_handler.handle(update, context)
            elif data == "about":
                await self._show_about(update, context)
            elif data == "subscribe":
                await self.payment_handler.handle(update, context)
            elif data == "start_trial":
                await self.payment_handler.start_trial(update, context)
            elif data == "pay_subscription":
                await self.payment_handler.pay_subscription(update, context)
            elif data.startswith("check_payment_"):
                await self.payment_handler.check_payment(update, context)
            elif data == "calculator":
                await self.calculator_handler.start_calculator(update, context)
            elif data == "new_calculation":
                await self.calculator_handler.new_calculation(update, context)
            elif data == "age" and self.age_handler:
                await self.age_handler.start_age(update, context)
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
        """Информация о проекте"""
        query = update.callback_query
        await query.answer()

        about_text = (
            "🎹 О проекте\n\n"
            "PianoMaster Club — это закрытое сообщество фортепианных мастеров экстра-класса.\n\n"
            "Что мы предлагаем:\n"
            "• Эксклюзивные материалы по ремонту и реставрации\n"
            "• Общение с ведущими мастерами\n"
            "• Калькулятор для изготовления басовых струн\n"
            "• Определение возраста фортепиано по серийному номеру\n"
            "• Закрытые мастер-классы и вебинары\n"
            "• Доступ к редким чертежам и схемам\n\n"
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
        """Справка"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        is_admin = user.id in config.ADMIN_IDS

        lines = [
            "❓ Помощь по PianoMaster Club",
            "",
            "🤖 Бот для фортепианных мастеров экстра-класса",
            "",
            "📋 Основные разделы:",
            "• 📖 О проекте — информация о клубе",
            "• 🎹 Получить доступ — пробный период или подписка",
            "• 🧮 Калькулятор струн — пошаговый расчет",
            "• 📅 Возраст фортепиано — определение года выпуска",
            "• 🔄 Статус доступа — проверка подписки",
            "• 📢 Канал — закрытый канал мастеров",
            "• 💬 Чат — общение с коллегами",
            "",
            "📝 Команды:",
            "/start или /menu — Главное меню",
            "/calc — Калькулятор струн",
            "/age — Возраст фортепиано",
            "/cancel — Отмена операции",
        ]

        if is_admin:
            lines.extend([
                "",
                "👑 Администратор:",
                "/admin — Панель управления",
            ])

        lines.extend([
            "",
            "💡 Советы:",
            "• Доступ открывается автоматически",
            "• Пробный период — 7 дней бесплатно",
            "• Для отмены используйте /cancel",
            "",
            "📧 Поддержка:",
            "• Администратор: @piano_admin",
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
        """Статус доступа пользователя"""
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

        subscription = self.subscription_service.get_by_user(db_user)

        lines = []

        if has_access:
            lines.append("✅ Доступ открыт")
            lines.append("")
            lines.append(access_desc)
            lines.append("")

            if subscription and subscription.is_trial:
                lines.append(f"🔰 Пробный период: {subscription.trial_days_left} дн.")
                lines.append(f"📅 До: {subscription.trial_end.strftime('%d.%m.%Y')}")
                lines.append("")
                lines.append("📢 **Доступ к каналу и чату открыт!**")
            elif subscription and subscription.is_active:
                lines.append(f"📅 Действует до: {subscription.expires_at.strftime('%d.%m.%Y')}")
                lines.append(f"⏳ Осталось: {subscription.days_left} дн.")
                lines.append("")
                lines.append("📢 **Доступ к каналу и чату открыт!**")
            elif subscription and subscription.has_trial_available:
                lines.append("🔰 Доступен пробный период 7 дней!")
                lines.append("")
                lines.append("📢 **Для доступа к каналу и чату активируйте пробный период**")

            if access_type.startswith("whitelist_"):
                role_str = access_type.replace("whitelist_", "")
                try:
                    role = WhitelistRole(role_str)
                    lines.append(f"👑 Роль: {role.display_name}")

                    entry = self.whitelist_service.get_by_user(db_user)
                    if entry and entry.expires_at:
                        lines.append(f"📅 До: {entry.expires_at.strftime('%d.%m.%Y %H:%M')}")
                    if entry and entry.reason:
                        lines.append(f"📝 Причина: {entry.reason}")
                except ValueError:
                    pass
        else:
            lines.extend([
                "❌ Доступ закрыт",
                "",
                "Для доступа к функциям клуба необходимо:",
                "• Начать пробный период (7 дней бесплатно)",
                "• Оформить подписку",
                "• Или быть в белом списке",
                "",
                "📢 **Для доступа к каналу и чату требуется активная подписка или пробный период!**",
                "",
                f"🆔 Ваш ID: {user.id}"
            ])

        status_text = "\n".join(lines)

        keyboard = []
        if not has_access:
            keyboard.append([InlineKeyboardButton("🔰 Получить доступ", callback_data="subscribe")])
        else:
            if subscription and subscription.is_trial:
                keyboard.append([InlineKeyboardButton("💳 Оформить подписку", callback_data="subscribe")])

        if has_access:
            keyboard.append([
                InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
                InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
            ])
            keyboard.append([InlineKeyboardButton("🧮 Калькулятор", callback_data="calculator")])
            keyboard.append([InlineKeyboardButton("📅 Возраст фортепиано", callback_data="age")])

        if is_admin:
            keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data="admin_menu")])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="menu")])

        await query.edit_message_text(
            status_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _check_expired_subscriptions(self):
        """Фоновая проверка истекших подписок и пробных периодов"""
        while True:
            try:
                # Проверка истекших подписок
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
                                    "Для продления нажмите /menu и выберите «Получить доступ»"
                                )
                            except Exception as e:
                                logger.error(f"Failed to notify user {user.telegram_id}: {e}")

                # Проверка пробных периодов, которые истекают скоро
                trials_expiring = self.subscription_service.get_trials_expiring_soon(1)
                for subscription in trials_expiring:
                    user = self.user_service.get(subscription.user_id)
                    if user:
                        try:
                            await self.app.bot.send_message(
                                user.telegram_id,
                                f"🔰 Ваш пробный период заканчивается завтра!\n\n"
                                f"Чтобы продолжить пользоваться клубом, оформите подписку.\n"
                                f"Нажмите /menu и выберите «Получить доступ»"
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify trial user {user.telegram_id}: {e}")

                # Проверка истекших записей в белом списке
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

        try:
            await self.app.bot.delete_webhook()
            logger.info("✅ Webhook deleted")
        except Exception as e:
            logger.warning(f"Webhook deletion failed: {e}")

        asyncio.create_task(self._check_expired_subscriptions())

        logger.info("Starting PianoMaster Club Bot...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        logger.info("✅ Bot is running!")

        while True:
            await asyncio.sleep(1)