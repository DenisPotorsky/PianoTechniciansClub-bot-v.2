"""
Обработчик административных команд с полной статистикой
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base_handler import BaseHandler
from services.whitelist_service import WhitelistService
from services.user_service import UserService
from services.subscription_service import SubscriptionService
from models.whitelist import WhitelistRole
from app.config import config


class AdminHandler(BaseHandler):
    """Обработчик административных команд"""

    def __init__(self, whitelist_service: WhitelistService, user_service: UserService):
        self.whitelist_service = whitelist_service
        self.user_service = user_service
        self._waiting_for_add = {}
        self._waiting_for_remove = {}

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню администратора"""
        user = update.effective_user

        if user.id not in config.ADMIN_IDS:
            if update.message:
                await update.message.reply_text("⛔ У вас нет прав администратора.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Нет прав")
                await update.callback_query.edit_message_text(
                    "⛔ У вас нет прав администратора.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                    ])
                )
            return

        db_user = self.user_service.get_by_telegram_id(user.id)
        if not db_user:
            if update.message:
                await update.message.reply_text("❌ Пользователь не найден")
            return

        can_manage = self.whitelist_service.can_manage_whitelist(db_user)

        keyboard = [
            [InlineKeyboardButton("📋 Список участников", callback_data="admin_whitelist_list")],
            [InlineKeyboardButton("➕ Добавить участника", callback_data="admin_whitelist_add")],
            [InlineKeyboardButton("❌ Удалить участника", callback_data="admin_whitelist_remove")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_whitelist_stats")],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
        ]

        if not can_manage:
            keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data="admin_whitelist_stats")],
                [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
            ]

        text = (
            "👑 Панель администратора\n\n"
            "Управление белым списком и участниками клуба.\n\n"
            f"Ваш ID: {user.id}"
        )

        if update.message:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def show_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает список участников белого списка"""
        query = update.callback_query
        await query.answer()

        users = self.whitelist_service.get_all_whitelist_users()

        if not users:
            await query.edit_message_text(
                "📭 В белом списке пока нет участников.\n\n"
                "Добавьте первого участника через «➕ Добавить участника»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить", callback_data="admin_whitelist_add")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_menu")]
                ])
            )
            return

        text = "📋 Участники белого списка:\n\n"
        for idx, user in enumerate(users, 1):
            entry = self.whitelist_service.get_by_user(user)
            if entry:
                role_name = entry.role.display_name
                expires = f" (до {entry.expires_at.strftime('%d.%m.%Y')})" if entry.expires_at else " (бессрочно)"
                text += f"{idx}. ID: {user.telegram_id} - {user.display_name}\n"
                text += f"   {role_name}{expires}\n"
                if entry.reason:
                    text += f"   Причина: {entry.reason}\n"
                text += "\n"

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить", callback_data="admin_whitelist_add")],
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_menu")]
            ])
        )

    async def add_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса добавления пользователя"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        db_user = self.user_service.get_by_telegram_id(user.id)
        if not db_user or not self.whitelist_service.can_manage_whitelist(db_user):
            await query.edit_message_text(
                "⛔ У вас нет прав для этого действия",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_menu")]
                ])
            )
            return

        self._waiting_for_add[user.id] = True
        context.user_data['waiting_for_whitelist_add'] = True

        roles_text = "\n".join([
            f"• {role.value} - {role.display_name}"
            for role in WhitelistRole
        ])

        await query.edit_message_text(
            f"✏️ Добавление в белый список\n\n"
            f"Введите данные в формате:\n"
            f"telegram_id роль причина\n\n"
            f"Доступные роли:\n{roles_text}\n\n"
            f"Примеры:\n"
            f"123456789 founder Основатель клуба\n"
            f"987654321 expert Ведущий эксперт\n"
            f"555555555 temporary На месяц\n\n"
            f"Для отмены отправьте /cancel",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Отмена", callback_data="admin_menu")]
            ])
        )

    async def handle_add_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода для добавления пользователя"""
        if not update.message:
            return

        user = update.effective_user
        text = update.message.text.strip()

        if text.lower() == '/cancel':
            self._waiting_for_add.pop(user.id, None)
            context.user_data.pop('waiting_for_whitelist_add', None)
            await update.message.reply_text(
                "❌ Операция отменена",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )
            return

        if user.id not in config.ADMIN_IDS:
            await update.message.reply_text("⛔ У вас нет прав для этого действия")
            return

        admin_db = self.user_service.get_by_telegram_id(user.id)
        if not admin_db or not self.whitelist_service.can_manage_whitelist(admin_db):
            await update.message.reply_text("⛔ У вас нет прав для этого действия")
            return

        try:
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                await update.message.reply_text(
                    "❌ Неправильный формат.\n"
                    "Используйте: telegram_id роль причина\n\n"
                    "Пример: 123456789 founder Основатель"
                )
                return

            telegram_id = int(parts[0])
            role_str = parts[1].lower()
            reason = parts[2]

            try:
                role = WhitelistRole(role_str)
            except ValueError:
                available_roles = ", ".join([r.value for r in WhitelistRole])
                await update.message.reply_text(
                    f"❌ Неизвестная роль: {role_str}\n"
                    f"Доступные: {available_roles}"
                )
                return

            user = self.user_service.get_or_create(
                telegram_id=telegram_id,
                username=None,
                first_name=f"User_{telegram_id}",
                last_name=None
            )

            if self.whitelist_service.is_in_whitelist(user):
                existing_role = self.whitelist_service.get_user_role(user)
                await update.message.reply_text(
                    f"⚠️ Пользователь {telegram_id} уже в белом списке!\n"
                    f"Текущая роль: {existing_role.display_name if existing_role else 'Unknown'}"
                )
                return

            days = 30 if role == WhitelistRole.TEMPORARY else None
            entry = self.whitelist_service.add_to_whitelist(
                user=user,
                role=role,
                reason=reason,
                added_by=admin_db,
                days=days
            )

            self._waiting_for_add.pop(user.id, None)
            context.user_data.pop('waiting_for_whitelist_add', None)

            try:
                await update.get_bot().send_message(
                    telegram_id,
                    f"🎉 Вы добавлены в белый список PianoMaster Club!\n\n"
                    f"Роль: {role.display_name}\n"
                    f"Причина: {reason}\n"
                    f"Добавил: {admin_db.display_name}\n\n"
                    f"Теперь вам доступны все функции клуба.\n"
                    f"Нажмите /menu для начала работы."
                )
            except Exception as e:
                await update.message.reply_text(
                    f"⚠️ Пользователь добавлен, но не удалось отправить уведомление.\n"
                    f"Убедитесь, что пользователь начал диалог с ботом.\n"
                    f"Ошибка: {str(e)}"
                )

            await update.message.reply_text(
                f"✅ Пользователь успешно добавлен в белый список!\n\n"
                f"Telegram ID: {telegram_id}\n"
                f"Имя: {user.display_name}\n"
                f"Роль: {role.display_name}\n"
                f"Причина: {reason}\n"
                f"{'⏳ Действует 30 дней' if days else '♾️ Бессрочный доступ'}"
            )

        except ValueError as e:
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}\n"
                "Убедитесь, что Telegram ID - это число."
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}"
            )

    async def remove_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса удаления пользователя"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        db_user = self.user_service.get_by_telegram_id(user.id)
        if not db_user or not self.whitelist_service.can_manage_whitelist(db_user):
            await query.edit_message_text(
                "⛔ У вас нет прав для этого действия",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_menu")]
                ])
            )
            return

        users = self.whitelist_service.get_all_whitelist_users()

        if not users:
            await query.edit_message_text(
                "📭 Белый список пуст. Некого удалять.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="admin_menu")]
                ])
            )
            return

        text = "❌ Удаление из белого списка\n\n"
        text += "Введите Telegram ID пользователя для удаления:\n\n"
        text += "Текущие участники:\n"

        for user in users:
            entry = self.whitelist_service.get_by_user(user)
            if entry:
                text += f"• {user.telegram_id} - {user.display_name} ({entry.role.display_name})\n"

        text += "\nДля отмены отправьте /cancel"

        self._waiting_for_remove[update.effective_user.id] = True
        context.user_data['waiting_for_whitelist_remove'] = True

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Отмена", callback_data="admin_menu")]
            ])
        )

    async def handle_remove_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода для удаления пользователя"""
        if not update.message:
            return

        user = update.effective_user
        text = update.message.text.strip()

        if text.lower() == '/cancel':
            self._waiting_for_remove.pop(user.id, None)
            context.user_data.pop('waiting_for_whitelist_remove', None)
            await update.message.reply_text(
                "❌ Операция отменена",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )
            return

        if user.id not in config.ADMIN_IDS:
            await update.message.reply_text("⛔ У вас нет прав для этого действия")
            return

        admin_db = self.user_service.get_by_telegram_id(user.id)
        if not admin_db or not self.whitelist_service.can_manage_whitelist(admin_db):
            await update.message.reply_text("⛔ У вас нет прав для этого действия")
            return

        try:
            telegram_id = int(text.strip())
            user_to_remove = self.user_service.get_by_telegram_id(telegram_id)

            if not user_to_remove:
                await update.message.reply_text(
                    f"❌ Пользователь с ID {telegram_id} не найден в системе"
                )
                return

            if not self.whitelist_service.is_in_whitelist(user_to_remove):
                await update.message.reply_text(
                    f"❌ Пользователь {telegram_id} не найден в белом списке"
                )
                return

            role = self.whitelist_service.get_user_role(user_to_remove)

            if self.whitelist_service.remove_from_whitelist(user_to_remove):
                self._waiting_for_remove.pop(user.id, None)
                context.user_data.pop('waiting_for_whitelist_remove', None)

                try:
                    await update.get_bot().send_message(
                        telegram_id,
                        f"⏰ Ваш доступ по белому списку отозван\n\n"
                        f"Роль: {role.display_name if role else 'Unknown'}\n"
                        f"Отозвал: {admin_db.display_name}\n\n"
                        "Для продолжения использования клуба оформите подписку.\n"
                        "Нажмите /menu для просмотра доступных опций."
                    )
                except Exception:
                    pass

                await update.message.reply_text(
                    f"✅ Пользователь удален из белого списка!\n\n"
                    f"Telegram ID: {telegram_id}\n"
                    f"Имя: {user_to_remove.display_name}\n"
                    f"Бывшая роль: {role.display_name if role else 'Unknown'}"
                )
            else:
                await update.message.reply_text(
                    f"❌ Не удалось удалить пользователя {telegram_id} из белого списка"
                )

        except ValueError:
            await update.message.reply_text(
                "❌ Неверный Telegram ID. Введите число.\n"
                "Пример: 123456789"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает полную статистику с учётом пробных периодов и подписок"""
        query = update.callback_query
        await query.answer()

        # Получаем всех пользователей
        all_users = self.user_service.get_all_active()
        total_users = len(all_users)

        # Пользователи в белом списке
        whitelist_users = self.whitelist_service.get_all_whitelist_users()
        whitelist_count = len(whitelist_users)

        # Статистика по ролям
        stats = {role.value: 0 for role in WhitelistRole}
        for user in whitelist_users:
            role = self.whitelist_service.get_user_role(user)
            if role:
                stats[role.value] = stats.get(role.value, 0) + 1

        # ---- СТАТИСТИКА ПО ПОДПИСКАМ ----
        trial_users = []
        subscribed_users = []
        expired_users = []

        for user in all_users:
            subscription = self.subscription_service.get_by_user(user)
            if subscription:
                if subscription.is_trial:
                    trial_users.append(user)
                elif subscription.is_active and not subscription.is_expired:
                    subscribed_users.append(user)
                elif subscription.is_expired:
                    expired_users.append(user)

        trial_count = len(trial_users)
        subscribed_count = len(subscribed_users)
        expired_count = len(expired_users)

        # Формируем текст
        text = "📊 **Статистика клуба**\n\n"
        text += f"👥 Всего пользователей: **{total_users}**\n"
        text += f"⭐ В белом списке: **{whitelist_count}**\n"
        text += f"📊 Процент: **{round((whitelist_count / total_users * 100) if total_users > 0 else 0, 1)}%**\n\n"

        # Статистика по подпискам
        text += "📋 **Подписки:**\n"
        text += f"  🔰 Пробный период: **{trial_count}**\n"
        text += f"  💎 Активная подписка: **{subscribed_count}**\n"
        text += f"  ⏰ Истекла: **{expired_count}**\n\n"

        text += "👑 **Распределение по ролям:**\n"
        for role in WhitelistRole:
            count = stats.get(role.value, 0)
            if count > 0:
                text += f"  {role.display_name}: {count}\n"

        if whitelist_count == 0:
            text += "  ❌ Белый список пуст\n"

        # Список пользователей на пробном периоде
        if trial_count > 0:
            text += "\n🔰 **Пользователи на пробном периоде:**\n"
            for user in trial_users[:10]:
                subscription = self.subscription_service.get_by_user(user)
                if subscription:
                    text += f"  • {user.first_name} (@{user.username or 'нет'}) — до {subscription.trial_end.strftime('%d.%m.%Y')}\n"
            if trial_count > 10:
                text += f"  ... и ещё {trial_count - 10}\n"

        # Список пользователей с активной подпиской
        if subscribed_count > 0:
            text += "\n💎 **Активная подписка:**\n"
            for user in subscribed_users[:10]:
                subscription = self.subscription_service.get_by_user(user)
                if subscription:
                    text += f"  • {user.first_name} (@{user.username or 'нет'}) — до {subscription.expires_at.strftime('%d.%m.%Y')}\n"
            if subscribed_count > 10:
                text += f"  ... и ещё {subscribed_count - 10}\n"

        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_menu")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def add_self(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавляет себя в белый список (для тестирования)"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        db_user = self.user_service.get_by_telegram_id(user.id)

        if not db_user:
            await query.edit_message_text("❌ Пользователь не найден")
            return

        if self.whitelist_service.is_in_whitelist(db_user):
            role = self.whitelist_service.get_user_role(db_user)
            await query.edit_message_text(
                f"✅ Вы уже в белом списке!\n"
                f"Роль: {role.display_name if role else 'Unknown'}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                ])
            )
            return

        entry = self.whitelist_service.add_to_whitelist(
            user=db_user,
            role=WhitelistRole.FOUNDER,
            reason="Тестовый доступ",
            added_by=db_user,
            days=None
        )

        await query.edit_message_text(
            f"✅ Вы добавлены в белый список!\n\n"
            f"Роль: {entry.role.display_name}\n"
            f"Теперь вам доступны все функции клуба.\n"
            f"Нажмите /menu для начала работы.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
            ])
        )

    def get_command(self) -> str:
        return "admin"