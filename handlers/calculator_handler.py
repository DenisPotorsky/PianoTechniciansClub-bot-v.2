"""
Обработчик калькулятора струн (пошаговый режим с иконками)
"""

import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from handlers.base_handler import BaseHandler
from services.access_service import AccessService
from services.user_service import UserService

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECT_WINDING, INPUT_CORE, INPUT_TOTAL, INPUT_LENGTH = range(4)


class CalculatorHandler(BaseHandler):
    """Обработчик калькулятора с пошаговым режимом"""

    def __init__(self, access_service: AccessService, user_service: UserService):
        self.access_service = access_service
        self.user_service = user_service

    def get_conversation_handler(self):
        """Возвращает ConversationHandler для калькулятора"""
        from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.start_calculator, pattern="^calculator$"),
                CallbackQueryHandler(self.new_calculation, pattern="^new_calculation$"),
                CommandHandler("calc", self.start_calculator)
            ],
            states={
                SELECT_WINDING: [
                    CallbackQueryHandler(self.select_winding, pattern="^winding_"),
                    CallbackQueryHandler(self.cancel, pattern="^cancel$")
                ],
                INPUT_CORE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_core),
                    CallbackQueryHandler(self.cancel, pattern="^cancel$")
                ],
                INPUT_TOTAL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_total),
                    CallbackQueryHandler(self.cancel, pattern="^cancel$")
                ],
                INPUT_LENGTH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.input_length),
                    CallbackQueryHandler(self.cancel, pattern="^cancel$")
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^cancel$")
            ],
            name="calculator_conversation",
            persistent=False,
            allow_reentry=True
        )

    async def new_calculation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Новый расчет - полный сброс"""
        query = update.callback_query
        await query.answer()

        # Очищаем все данные пользователя
        context.user_data.clear()

        # Запускаем калькулятор заново
        return await self.start_calculator(update, context)

    async def start_calculator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск калькулятора"""
        user = update.effective_user
        db_user = self.user_service.get_by_telegram_id(user.id)

        if not db_user or not self.access_service.has_access(db_user)[0]:
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    "🔒 Доступ к калькулятору открыт только для участников клуба!\n\n"
                    "Оформите подписку или обратитесь к администратору.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎹 Присоединиться", callback_data="subscribe")],
                        [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                    ])
                )
            else:
                await update.message.reply_text(
                    "🔒 Доступ к калькулятору открыт только для участников клуба!\n\n"
                    "Оформите подписку или обратитесь к администратору.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎹 Присоединиться", callback_data="subscribe")],
                        [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                    ])
                )
            return ConversationHandler.END

        # Очищаем старые данные перед новым расчетом
        context.user_data.clear()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔵 Одиночная навивка", callback_data="winding_1"),
                InlineKeyboardButton("🔴 Двойная навивка", callback_data="winding_2")
            ],
            [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
        ])

        text = (
            "🧮 **Калькулятор басовых струн**\n\n"
            "Выберите тип навивки струны:\n\n"
            "🔵 **Одиночная** — один слой медной обмотки\n"
            "🔴 **Двойная** — два слоя медной обмотки"
        )

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        return SELECT_WINDING

    async def select_winding(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора типа навивки"""
        query = update.callback_query
        await query.answer()

        if query.data == "winding_1":
            winding_type = 1
            winding_name = "одинарную"
        elif query.data == "winding_2":
            winding_type = 2
            winding_name = "двойную"
        else:
            await query.edit_message_text(
                "❌ Неизвестный тип навивки.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                ])
            )
            return SELECT_WINDING

        context.user_data['winding_type'] = winding_type
        context.user_data['winding_name'] = winding_name

        await query.edit_message_text(
            f"🔧 **Шаг 1/3: Диаметр керна**\n\n"
            f"Вы выбрали **{winding_name}** навивку.\n\n"
            f"Введите **диаметр керна** (стальной сердечник) в миллиметрах.\n"
            f"📝 Пример: `0.8` или `1.2`\n\n"
            f"Для отмены отправьте /cancel",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
            ])
        )

        return INPUT_CORE

    async def input_core(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод диаметра керна"""
        try:
            core = float(update.message.text.replace(",", "."))
            if core <= 0:
                raise ValueError("Диаметр должен быть положительным")
            if core > 5:
                await update.message.reply_text(
                    "⚠️ Слишком большой диаметр керна. Обычно он не превышает 3-4 мм.\n"
                    "Введите корректное значение:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                    ])
                )
                return INPUT_CORE

            context.user_data['core_diameter'] = core

            await update.message.reply_text(
                f"🔧 **Шаг 2/3: Общий диаметр струны**\n\n"
                f"Диаметр керна: **{core} мм**\n\n"
                f"Введите **общий диаметр струны** (с обмоткой) в миллиметрах.\n"
                f"📝 Пример: `1.5` или `2.8`\n\n"
                f"Для отмены отправьте /cancel",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                ])
            )

            return INPUT_TOTAL

        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректное **положительное число**.\n"
                "📝 Пример: `0.8`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                ])
            )
            return INPUT_CORE

    async def input_total(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод общего диаметра"""
        try:
            total = float(update.message.text.replace(",", "."))
            core = context.user_data.get('core_diameter', 0)

            if total <= 0:
                raise ValueError("Диаметр должен быть положительным")
            if total <= core:
                await update.message.reply_text(
                    f"⚠️ Общий диаметр **{total} мм** должен быть больше диаметра керна **{core} мм**.\n"
                    "Введите корректное значение:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                    ])
                )
                return INPUT_TOTAL

            context.user_data['total_diameter'] = total

            await update.message.reply_text(
                f"📏 **Шаг 3/3: Длина навивки**\n\n"
                f"Диаметр керна: **{core} мм**\n"
                f"Общий диаметр: **{total} мм**\n\n"
                f"Введите **длину навивки** (рабочую длину струны) в миллиметрах.\n"
                f"📝 Пример: `850` или `1000`\n\n"
                f"Для отмены отправьте /cancel",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                ])
            )

            return INPUT_LENGTH

        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректное **положительное число**.\n"
                "📝 Пример: `1.5`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                ])
            )
            return INPUT_TOTAL

    async def input_length(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод длины и расчет"""
        try:
            length = float(update.message.text.replace(",", "."))
            if length <= 0:
                raise ValueError("Длина должна быть положительной")
            if length < 50:
                await update.message.reply_text(
                    "⚠️ Слишком короткая струна. Обычная длина не менее 100-200 мм.\n"
                    "Введите корректное значение:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                    ])
                )
                return INPUT_LENGTH

            winding_type = context.user_data.get('winding_type')
            core = context.user_data.get('core_diameter')
            total = context.user_data.get('total_diameter')
            winding_name = context.user_data.get('winding_name', '')

            # Проверяем, что все данные есть
            if winding_type is None or core is None or total is None:
                await update.message.reply_text(
                    "❌ Ошибка: данные не найдены.\n"
                    "Начните расчет заново.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Новый расчет", callback_data="new_calculation")],
                        [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                    ])
                )
                return ConversationHandler.END

            result = self.calculate_string(winding_type, core, total, length)

            result_text = self.format_result(
                winding_type, core, total, length, winding_name, result
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Новый расчет", callback_data="new_calculation")],
                [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
            ])

            await update.message.reply_text(
                result_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

            # Очищаем данные после завершения расчета
            context.user_data.clear()
            return ConversationHandler.END

        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректное **положительное число**.\n"
                "📝 Пример: `850`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
                ])
            )
            return INPUT_LENGTH

    def calculate_string(self, winding_type, core, total, length):
        """Расчет параметров струны"""
        pi = math.pi

        if winding_type == 1:
            copper_diam = round((total - core) / 2, 3)
            copper_length = int((core + copper_diam * 2) * pi * length)

            return {
                'type': 'single',
                'copper_diam': copper_diam,
                'copper_length': copper_length,
                'total_length': copper_length
            }
        else:
            copper_first = round(((total - core) * 0.3334) / 2, 3)
            copper_second = round(((total - core) * 0.6667) / 2, 3)
            length_primary = int((core + copper_first * 2) * pi * length - 50)
            length_secondary = int((core + copper_first * 2 + copper_second * 2) * pi * length)

            return {
                'type': 'double',
                'copper_first': copper_first,
                'copper_second': copper_second,
                'length_primary': length_primary,
                'length_secondary': length_secondary,
                'total_length': length_primary + length_secondary
            }

    def format_result(self, winding_type, core, total, length, winding_name, result):
        """Форматирование результата с иконками"""
        text = "✅ **Результат расчета**\n\n"
        text += f"📋 **Исходные данные:**\n"
        text += f"• Тип навивки: {winding_name}\n"
        text += f"• Диаметр керна: **{core} мм**\n"
        text += f"• Общий диаметр: **{total} мм**\n"
        text += f"• Длина навивки: **{length} мм**\n\n"

        text += "📊 **Результаты:**\n"

        if result['type'] == 'single':
            text += f"• 🟡 Диаметр меди: **{result['copper_diam']} мм**\n"
            text += f"• 📏 Длина меди: **{result['copper_length']} мм**\n"
            text += f"• 📐 Общая длина: **{result['total_length']} мм**\n"
        else:
            text += f"• 🟡 Диаметр меди (первичный): **{result['copper_first']} мм**\n"
            text += f"• 🟠 Диаметр меди (вторичный): **{result['copper_second']} мм**\n"
            text += f"• 📏 Длина меди (первичная): **{result['length_primary']} мм**\n"
            text += f"• 📐 Длина меди (вторичная): **{result['length_secondary']} мм**\n"
            text += f"• 📊 Общая длина: **{result['total_length']} мм**\n"

        return text

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена расчета"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()

            await query.edit_message_text(
                "❌ Расчет отменен.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )
        elif update.message:
            await update.message.reply_text(
                "❌ Расчет отменен.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
                ])
            )

        context.user_data.clear()
        return ConversationHandler.END

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /calc или кнопки Калькулятор"""
        return await self.start_calculator(update, context)

    def get_command(self) -> str:
        return "calc"