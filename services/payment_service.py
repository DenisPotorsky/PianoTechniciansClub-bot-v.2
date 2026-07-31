from typing import Optional, Tuple
from datetime import datetime
import yookassa
from yookassa import Configuration, Payment as YooPayment
from models.payment import Payment, PaymentStatus
from models.user import User
from services.subscription_service import SubscriptionService
from services.user_service import UserService


class PaymentService:
    """Сервис для работы с платежами"""

    def __init__(self, shop_id: str, secret_key: str,
                 subscription_service: SubscriptionService,
                 user_service: UserService):
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.subscription_service = subscription_service
        self.user_service = user_service

        # Настройка YooKassa
        Configuration.account_id = shop_id
        Configuration.secret_key = secret_key

    def create_payment(self, user: User, amount: int) -> Tuple[Payment, str]:
        """
        Создает платеж и возвращает объект платежа и URL для оплаты
        """
        try:
            payment = YooPayment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/piano_club_bot"
                },
                "capture": True,
                "description": f"Подписка PianoMaster Club для {user.first_name}",
                "metadata": {
                    "user_id": str(user.id),
                    "telegram_id": str(user.telegram_id)
                }
            })

            payment_obj = Payment(
                id=0,
                user_id=user.id,
                amount=amount,
                status=PaymentStatus.PENDING,
                payment_id=payment.id,
                created_at=datetime.now()
            )

            return payment_obj, payment.confirmation.confirmation_url

        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise

    def check_payment_status(self, payment_id: str) -> PaymentStatus:
        """
        Проверяет статус платежа
        """
        try:
            payment = YooPayment.find_one(payment_id)
            status = payment.status

            if status == "succeeded":
                return PaymentStatus.SUCCEEDED
            elif status == "canceled":
                return PaymentStatus.CANCELED
            else:
                return PaymentStatus.PENDING

        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return PaymentStatus.PENDING

    def complete_payment(self, payment_id: str, user_id: int):
        """
        Завершает платеж и активирует подписку
        """
        # Здесь можно сохранить информацию о завершенном платеже в БД
        pass