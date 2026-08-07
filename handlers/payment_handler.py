"""
Обработчик платежей и пробного периода
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.base_handler import BaseHandler
from services.payment_service import PaymentService
from services.subscription_service import SubscriptionService
from services.user_service import UserService
from app.config import config
from keyboards.inline_keyboards import get_subscription_keyboard, get_subscription_success_keyboard


class PaymentHandler(BaseHandler):
    """Обработчик платежей с поддержкой пробного периода"""

    def __init__(self, payment_service: PaymentService,
                 subscription_service: SubscriptionService,
                 user_service: UserService):
        self.payment_service = payment_service
        self.subscription_service = subscription_service
        self.user_service = user_service

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса оплаты или активация пробного периода"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        db_user = self.user_service.get_or_create(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        # Проверяем, есть ли уже подписка
        subscription = self.subscription_service.get_by_user(db_user)

        # Проверяем, доступен ли пробный период
        can_start_trial = not subscription or subscription.has_trial_available

        keyboard = get_subscription_keyboard() if can_start_trial else InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Оформить подписку", callback_data="pay_subscription")],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
        ])

        text = (
            "🎹 **PianoMaster Club — Получение доступа**\n\n"
            "Выберите способ получения доступа:\n\n"
        )

        if can_start_trial:
            text += (
                "🔰 **Пробный период 7 дней** — бесплатно!\n"
                "• Все функции клуба\n"
                "• Доступ к каналу и чату\n"
                "• Калькулятор струн\n"
                "• Определение возраста фортепиано\n\n"
            )

        text += (
            f"💎 **Полная подписка** — {config.SUBSCRIPTION_PRICE} ₽ / {config.SUBSCRIPTION_DAYS} дней\n"
            "• Все функции пробного периода\n"
            "• Продолжение доступа после пробного периода\n\n"
            "📢 После получения доступа вам станут доступны канал и чат мастеров!"
        )

        if subscription and subscription.is_trial:
            text += f"\n\n🔰 Ваш пробный период активен! Осталось {subscription.trial_days_left} дней."
        elif subscription and subscription.is_active:
            text += f"\n\n✅ Ваша подписка активна! Осталось {subscription.days_left} дней."

        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    async def start_trial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало пробного периода"""
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

        try:
            # Запускаем пробный период
            subscription = self.subscription_service.start_trial(db_user)

            # Логируем действие
            logger.info(f"User {user.id} started trial period")

            await query.edit_message_text(
                f"✅ **Пробный период активирован!**\n\n"
                f"🔰 Вам доступны все функции клуба на 7 дней.\n"
                f"📅 Действует до: {subscription.trial_end.strftime('%d.%m.%Y')}\n\n"
                f"📢 **Теперь вам доступны канал и чат мастеров!**\n\n"
                f"После окончания пробного периода вы можете оформить полную подписку.",
                reply_markup=get_subscription_success_keyboard(),
                parse_mode="Markdown"
            )

        except ValueError as e:
            await query.edit_message_text(
                f"❌ {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                ])
            )
        except Exception as e:
            logger.error(f"Error starting trial: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при активации пробного периода: {str(e)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
                ])
            )

    async def pay_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Оформление платной подписки"""
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
            f"• 📢 Закрытый канал мастеров\n"
            f"• 💬 Чат для общения\n"
            f"• 🧮 Калькулятор струн\n"
            f"• 📅 Определение возраста фортепиано\n"
            f"• 📚 Эксклюзивные материалы",
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

            logger.info(f"User {user.id} activated subscription")

            await query.edit_message_text(
                "✅ **Подписка активирована!**\n\n"
                "Добро пожаловать в PianoMaster Club!\n\n"
                "📢 **Теперь вам доступны канал и чат мастеров!**\n\n"
                f"📅 Действует до: {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
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