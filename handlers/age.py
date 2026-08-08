"""
Обработчик определения возраста фортепиано
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from handlers.base_handler import BaseHandler
from age_detector import AgeDetector
from services.access_service import AccessService
from services.user_service import UserService

logger = logging.getLogger(__name__)

# Состояния диалога
SELECT_TYPE, INPUT_BRAND, INPUT_SERIAL = range(3)


class AgeHandler(BaseHandler):
    """Обработчик определения возраста фортепиано"""

    def __init__(self, age_detector: AgeDetector, access_service: AccessService, user_service: UserService):
        self.age_detector = age_detector
        self.access_service = access_service
        self.user_service = user_service

    def get_conversation_handler(self):
        """Возвращает ConversationHandler для определения возраста"""
        return ConversationHandler(
            entry_points=[
                CommandHandler("age", self.start_age),
                CallbackQueryHandler(self.start_age, pattern="^age$")
            ],
            states={
                SELECT_TYPE: [
                    CallbackQueryHandler(self.select_type, pattern="^age_type_"),
                    CallbackQueryHandler(self.cancel, pattern="^cancel$"),
                    CommandHandler("cancel", self.cancel)
                ],
                INPUT_BRAND: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_brand),
                    CallbackQueryHandler(self.cancel, pattern="^cancel$"),
                    CommandHandler("cancel", self.cancel)
                ],
                INPUT_SERIAL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_serial),
                    CallbackQueryHandler(self.cancel, pattern="^cancel$"),
                    CommandHandler("cancel", self.cancel)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^cancel$")
            ],
            name="age_conversation",
            persistent=False,
            allow_reentry=True
        )

    async def start_age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало определения возраста"""
        user = update.effective_user
        db_user = self.user_service.get_by_telegram_id(user.id)

        # Проверяем доступ
        if not db_user or not self.access_service.has_access(db_user)[0]:
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    "🔒 Доступ к определению возраста открыт только для участников клуба!\n\n"
                    "Оформите подписку или обратитесь к администратору.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎹 Получить доступ", callback_data="subscribe")],
                        [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                    ])
                )
            else:
                await update.message.reply_text(
                    "🔒 Доступ к определению возраста открыт только для участников клуба!\n\n"
                    "Оформите подписку или обратитесь к администратору.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎹 Получить доступ", callback_data="subscribe")],
                        [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                    ])
                )
            return ConversationHandler.END

        # Считаем количество брендов
        foreign_count = await self.age_detector.db.get_brand_count('foreign')
        russian_count = await self.age_detector.db.get_brand_count('russian')

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🇪🇺 Иностранные ({foreign_count})", callback_data="age_type_foreign"),
                InlineKeyboardButton(f"🇷🇺 Отечественные ({russian_count})", callback_data="age_type_russian")
            ],
            [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
        ])

        text = (
            "📅 **Определение возраста фортепиано**\n\n"
            "Выберите тип бренда:\n\n"
            "🇪🇺 **Иностранные** — Steinway, Yamaha, Kawai, Bechstein и др.\n"
            "🇷🇺 **Отечественные** — Красный Октябрь, Аккорд, Микро и др.\n\n"
            "📊 В базе данных:\n"
            f"• Иностранных: {foreign_count}\n"
            f"• Отечественных: {russian_count}"
        )

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text,
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=keyboard
            )

        return SELECT_TYPE

    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора типа бренда"""
        query = update.callback_query
        await query.answer()

        brand_type = query.data.replace("age_type_", "")
        context.user_data['brand_type'] = brand_type

        type_name = "иностранных" if brand_type == "foreign" else "отечественных"

        await query.edit_message_text(
            f"🔍 **Шаг 1/2: Введите название бренда**\n\n"
            f"Вы выбрали: **{type_name}** бренды.\n\n"
            f"Введите название бренда фортепиано.\n"
            f"📝 Пример: `Steinway`, `Yamaha`, `Красный Октябрь`\n\n"
            f"Поиск работает по частичному совпадению (регистр не важен).\n"
            f"Для отмены отправьте /cancel",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
            ])
        )

        return INPUT_BRAND

    async def input_brand(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод названия бренда (регистронезависимый поиск)"""
        brand_name = update.message.text.strip()

        if not brand_name:
            await update.message.reply_text(
                "❌ Пожалуйста, введите название бренда.\n"
                "Для отмены отправьте /cancel"
            )
            return INPUT_BRAND

        context.user_data['brand_name'] = brand_name

        # Проверяем, есть ли такой бренд (регистронезависимый поиск)
        brand_type = context.user_data.get('brand_type')
        brand = await self.age_detector.db.get_brand_by_name(brand_name)

        if brand:
            # Бренд найден, переходим к вводу серийного номера
            await update.message.reply_text(
                f"🔍 **Шаг 2/2: Введите серийный номер**\n\n"
                f"Бренд: **{brand['name']}**\n"
                f"{brand.get('country', '')}\n\n"
                f"Введите серийный номер фортепиано.\n"
                f"📝 Пример: `123456`, `A12345`, `SN-123456`\n\n"
                f"Я автоматически извлеку цифры из номера.\n"
                f"Для отмены отправьте /cancel",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                ])
            )
            return INPUT_SERIAL

        # Бренд не найден, ищем похожие (регистронезависимый поиск)
        similar = await self.age_detector.db.search_brands(brand_name, brand_type, limit=10)

        if similar:
            similar_text = "\n".join(f"• {b['name']}" for b in similar[:10])
            await update.message.reply_text(
                f"❌ Бренд **{brand_name}** не найден.\n\n"
                f"Возможно, вы имели в виду:\n{similar_text}\n\n"
                f"Введите точное название бренда.\n"
                f"Для отмены отправьте /cancel"
            )
            return INPUT_BRAND
        else:
            # Показываем все доступные бренды
            all_brands = await self.age_detector.db.get_all_brands(brand_type)
            if all_brands:
                brands_list = "\n".join(f"• {b['name']}" for b in all_brands[:10])
                await update.message.reply_text(
                    f"❌ Бренд **{brand_name}** не найден.\n\n"
                    f"Доступные бренды:\n{brands_list}\n\n"
                    f"Введите точное название бренда.\n"
                    f"Для отмены отправьте /cancel"
                )
            else:
                await update.message.reply_text(
                    f"❌ Бренд **{brand_name}** не найден.\n\n"
                    f"В базе данных пока нет брендов.\n"
                    f"Обратитесь к администратору.\n\n"
                    f"Введите другое название или отправьте /cancel"
                )
            return INPUT_BRAND

    async def input_serial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод серийного номера и вывод результата"""
        serial_input = update.message.text.strip()

        if not serial_input:
            await update.message.reply_text(
                "❌ Пожалуйста, введите серийный номер.\n"
                "Для отмены отправьте /cancel"
            )
            return INPUT_SERIAL

        brand_name = context.user_data.get('brand_name')
        brand_type = context.user_data.get('brand_type')

        # Определяем возраст
        result = await self.age_detector.detect(brand_name, serial_input, brand_type)

        # Формируем ответ
        if result.found:
            response = (
                f"{result.message}\n\n"
                f"📋 Серийный номер: {result.serial_number}\n"
            )
            if result.brand_info:
                response += f"\nℹ️ {result.brand_info}"
            response += "\n\n🔄 Для нового поиска используйте /age"
        else:
            response = result.message
            if result.similar_brands:
                response += "\n\n🔄 Для нового поиска используйте /age"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Новый поиск", callback_data="age")],
            [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
        ])

        await update.message.reply_text(
            response,
            reply_markup=keyboard
        )

        # Очищаем данные
        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена операции"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                "❌ Определение возраста отменено.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )
        elif update.message:
            await update.message.reply_text(
                "❌ Определение возраста отменено.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )

        context.user_data.clear()
        return ConversationHandler.END

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /age"""
        return await self.start_age(update, context)

    def get_command(self) -> str:
        return "age"