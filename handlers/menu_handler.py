from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base_handler import BaseHandler
from services.access_service import AccessService
from services.user_service import UserService
from keyboards.inline_keyboards import get_main_keyboard


class MenuHandler(BaseHandler):
    """Обработчик главного меню"""

    def __init__(self, access_service: AccessService, user_service: UserService):
        self.access_service = access_service
        self.user_service = user_service

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню"""
        user = update.effective_user

        # Получаем или создаем пользователя
        db_user = self.user_service.get_or_create(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        # Проверяем доступ
        has_access, access_type = self.access_service.has_access(db_user)
        access_desc = self.access_service.get_access_description(db_user)

        # Создаем клавиатуру
        keyboard = get_main_keyboard(has_access, access_type)

        # Формируем сообщение
        status_icon = "🔒" if not has_access else "✅"
        status_text = "Закрытый клуб" if not has_access else "Доступ открыт"

        message = (
            f"🎵 **PianoMasterClub**\n\n"
            f"{status_icon} **{status_text}**\n"
            f"Добро пожаловать, {user.first_name}!\n\n"
            f"Эксклюзивный клуб для фортепианных мастеров экстра-класса.\n\n"
            f"**Ваш статус:** {access_desc}"
        )

        # Проверяем тип обновления и отправляем ответ
        if update.message:
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

    def get_command(self) -> str:
        return "start"