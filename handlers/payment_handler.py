from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base_handler import BaseHandler
from services.payment_service import PaymentService
from services.subscription_service import SubscriptionService
from services.user_service import UserService
from app.config import config
from keyboards.inline_keyboards import get_subscription_success_keyboard


class PaymentHandler(BaseHandler):
    """Обработчик платежей"""

    def __init__(self, payment_service: PaymentService,
                 subscription_service: SubscriptionService,
                 user_service: UserService):
        self.payment_service = payment_service
        self.subscription_service = subscription_service
        self.user_service = user_service

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса оплаты"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        db_user = self.user_service.get_or_create(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        # Создаем платеж
        payment_obj, payment_url = self.payment_service.create_payment(
            db_user, config.SUBSCRIPTION_PRICE
        )

        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", url=payment_url)],
            [InlineKeyboardButton("✅ Проверить оплату",
                                  callback_data=f"check_payment_{payment_obj.payment_id}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
        ]

        await query.edit_message_text(
            f"💎 **Оформление подписки**\n\n"
            f"Стоимость: {config.SUBSCRIPTION_PRICE} ₽\n"
            f"Срок: {config.SUBSCRIPTION_DAYS} дней\n\n"
            f"После оплаты нажмите «Проверить оплату»\n\n"
            f"📢 **После активации подписки вам станут доступны:**\n"
            f"• Закрытый канал мастеров\n"
            f"• Чат для общения\n"
            f"• Калькулятор струн\n"
            f"• Эксклюзивные материалы",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    async def check_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка статуса платежа"""
        query = update.callback_query
        await query.answer()

        payment_id = query.data.replace("check_payment_", "")
        status = self.payment_service.check_payment_status(payment_id)

        if status.value == "succeeded":
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

            # Активируем подписку
            subscription = self.subscription_service.activate_subscription(db_user)

            # Отмечаем платеж как завершенный
            self.payment_service.complete_payment(payment_id, db_user.id)

            await query.edit_message_text(
                "✅ **Подписка активирована!**\n\n"
                "Добро пожаловать в PianoMasterClub!\n\n"
                "**Теперь вам доступны:**\n"
                "• 📢 Закрытый канал\n"
                "• 💬 Чат мастеров\n"
                "• 🔧 Калькулятор струн\n"
                "• 📚 Эксклюзивные материалы\n\n"
                "Присоединяйтесь к сообществу!",
                reply_markup=get_subscription_success_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                "⏳ **Платеж еще не подтвержден**\n\n"
                "Пожалуйста, оплатите подписку и нажмите «Проверить оплату» снова.\n"
                "Если вы уже оплатили, подождите 1-2 минуты.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Проверить снова",
                                          callback_data=f"check_payment_{payment_id}")],
                    [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                ]),
                parse_mode="Markdown"
            )

    def get_command(self) -> str:
        return "subscribe"