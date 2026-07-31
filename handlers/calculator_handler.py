from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base_handler import BaseHandler
from services.calculator_service import CalculatorService
from services.access_service import AccessService
from services.user_service import UserService


class CalculatorHandler(BaseHandler):
    """Обработчик калькулятора струн"""

    def __init__(self, calculator_service: CalculatorService,
                 access_service: AccessService,
                 user_service: UserService):
        self.calculator_service = calculator_service
        self.access_service = access_service
        self.user_service = user_service

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает форму калькулятора"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        db_user = self.user_service.get_by_telegram_id(user.id)

        if not db_user or not self.access_service.has_access(db_user)[0]:
            await query.edit_message_text(
                "🔒 Доступ запрещен\n\nКалькулятор доступен только участникам клуба.\nОформите подписку или свяжитесь с администратором.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎹 Присоединиться", callback_data="subscribe")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                ])
            )
            return

        # Сохраняем состояние для ожидания ввода
        context.user_data['calculator_state'] = 'waiting_input'

        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
        ]

        await query.edit_message_text(
            "🔧 Калькулятор басовых струн\n\n"
            "Введите параметры струны в формате:\n"
            "тип, керн, длина навивки, общий диаметр струны через пробел\n\n"
            "Примеры:\n"
            "1 1.2 850 2.5 - одинарная навивка\n"
            "2 1.2 850 2.5 - двойная навивка\n\n"
            "Где:\n"
            "• тип: 1 - одинарная, 2 - двойная\n"
            "• керн: диаметр в мм\n"
            "• длина навивки: длина в мм\n"
            "• общий диаметр струны: общий диаметр в мм",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def calculate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода и расчет"""
        try:
            # Проверяем, есть ли сообщение
            if not update.message:
                return

            text = update.message.text.strip()
            parts = text.split()

            if len(parts) != 4:
                await update.message.reply_text(
                    "❌ Неверный формат. Используйте: тип(пробел) керн(пробел) длина навивки(пробел) общий диаметр\n"
                    "Пример: 1 1.2 850 2.5"
                )
                return

            type_of_string = int(parts[0])
            kern = float(parts[1])
            length = int(parts[2])
            diam_general = float(parts[3])

            if type_of_string not in [1, 2]:
                await update.message.reply_text("❌ Тип струны должен быть 1 или 2")
                return

            # Выполняем расчет
            result = self.calculator_service.calculate(
                type_of_string, kern, length, diam_general
            )

            # Форматируем результат (без Markdown для безопасности)
            if result['type'] == 'single':
                formatted_result = (
                    f"📊 Результат расчета (одинарная навивка)\n\n"
                    f"Диаметр меди: {result['diam_primary']} мм\n"
                    f"Длина меди: {result['length_primary']} мм\n"
                )
            else:
                formatted_result = (
                    f"📊 Результат расчета (двойная навивка)\n\n"
                    f"Диаметр первичной меди: {result['diam_primary']} мм\n"
                    f"Диаметр вторичной меди: {result['diam_secondary']} мм\n"
                    f"Длина первичной меди: {result['length_primary']} мм\n"
                    f"Длина вторичной меди: {result['length_secondary']} мм\n"
                )

            # Добавляем кнопки
            keyboard = [
                [InlineKeyboardButton("🔄 Новый расчет", callback_data="calculator")],
                [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
            ]

            await update.message.reply_text(
                formatted_result,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except ValueError as e:
            await update.message.reply_text(
                f"❌ Ошибка ввода: {str(e)}\n"
                "Пожалуйста, проверьте правильность данных."
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка расчета: {str(e)}"
            )

    def get_command(self) -> str:
        return "calculator"