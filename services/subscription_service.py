"""
Сервис для управления подписками с пробным периодом
"""

from typing import Optional, List
from datetime import datetime, timedelta
from models.user import User
from models.subscription import Subscription
from repositories.subscription_repository import SubscriptionRepository
from services.base_service import BaseService
from app.config import config
import logging

logger = logging.getLogger(__name__)


class SubscriptionService(BaseService[Subscription]):
    """Сервис для управления подписками с пробным периодом"""

    TRIAL_DAYS = 7

    def __init__(self, subscription_repo: SubscriptionRepository):
        self.subscription_repo = subscription_repo
        logger.info("SubscriptionService initialized")

    def create(self, data: dict) -> Subscription:
        """Создание подписки"""
        subscription = Subscription(
            id=0,
            user_id=data['user_id'],
            expires_at=datetime.now() + timedelta(days=data.get('days', config.SUBSCRIPTION_DAYS))
        )
        return self.subscription_repo.create(subscription)

    def get(self, id: int) -> Optional[Subscription]:
        """Получение подписки по ID"""
        return self.subscription_repo.get_by_id(id)

    def get_by_user(self, user: User) -> Optional[Subscription]:
        """Получение активной подписки пользователя"""
        return self.subscription_repo.get_by_user_id(user.id)

    def has_active_subscription(self, user: User) -> bool:
        """Проверка наличия активной подписки (включая пробный период)"""
        subscription = self.get_by_user(user)
        if not subscription:
            return False

        if not subscription.is_active:
            return False

        if subscription.is_expired:
            return False

        return True

    def is_on_trial(self, user: User) -> bool:
        """Проверка, находится ли пользователь на пробном периоде"""
        subscription = self.get_by_user(user)
        if not subscription:
            return False
        return subscription.is_trial

    def has_used_trial(self, user: User) -> bool:
        """Проверка, использовал ли пользователь пробный период"""
        subscription = self.get_by_user(user)
        if not subscription:
            return False
        return subscription.trial_start is not None

    def start_trial(self, user: User) -> Subscription:
        """Начинает пробный период для пользователя и СОХРАНЯЕТ в базу"""
        logger.info(f"🔄 Starting trial for user {user.telegram_id} ({user.first_name})")

        # Проверяем, есть ли уже подписка
        subscription = self.subscription_repo.get_by_user_id(user.id)

        if subscription:
            logger.info(f"   Existing subscription found: id={subscription.id}")

            # Если уже есть подписка, проверяем, не использован ли пробный период
            if subscription.trial_start is not None:
                logger.warning(f"   Trial already used for user {user.telegram_id}")
                raise ValueError("Пробный период уже был использован")

            # Обновляем существующую подписку
            subscription.start_trial(self.TRIAL_DAYS)
            result = self.subscription_repo.update(subscription)
            logger.info(f"   ✅ Trial started (updated): {result.trial_start} -> {result.trial_end}")
            return result
        else:
            # Создаём новую подписку с пробным периодом
            logger.info(f"   No existing subscription, creating new")
            subscription = Subscription(
                id=0,
                user_id=user.id,
                expires_at=datetime.now() + timedelta(days=self.TRIAL_DAYS)
            )
            subscription.start_trial(self.TRIAL_DAYS)
            result = self.subscription_repo.create(subscription)
            logger.info(f"   ✅ Trial started (created): {result.trial_start} -> {result.trial_end}")
            return result

    def activate_subscription(self, user: User, days: int = None) -> Subscription:
        """Активация подписки (после оплаты)"""
        if days is None:
            days = config.SUBSCRIPTION_DAYS

        subscription = self.subscription_repo.get_by_user_id(user.id)

        if subscription:
            # Если подписка уже есть (возможно пробная), продлеваем её
            subscription.extend(days)
            return self.subscription_repo.update(subscription)
        else:
            # Создаём новую подписку (без пробного периода)
            subscription = Subscription(
                id=0,
                user_id=user.id,
                expires_at=datetime.now() + timedelta(days=days)
            )
            return self.subscription_repo.create(subscription)

    def deactivate_subscription(self, user: User) -> bool:
        """Деактивация подписки"""
        subscription = self.subscription_repo.get_by_user_id(user.id)
        if subscription:
            subscription.deactivate()
            self.subscription_repo.update(subscription)
            return True
        return False

    def update(self, id: int, data: dict) -> Optional[Subscription]:
        """Обновление подписки"""
        subscription = self.subscription_repo.get_by_id(id)
        if not subscription:
            return None

        if 'is_active' in data:
            subscription.is_active = data['is_active']
        if 'expires_at' in data:
            subscription.expires_at = data['expires_at']

        return self.subscription_repo.update(subscription)

    def delete(self, id: int) -> bool:
        """Удаление подписки"""
        return self.subscription_repo.delete(id)

    def check_expired_subscriptions(self) -> List[int]:
        """Проверка и деактивация истекших подписок"""
        expired = self.subscription_repo.get_expired_active()
        expired_users = []

        for subscription in expired:
            subscription.deactivate()
            self.subscription_repo.update(subscription)
            expired_users.append(subscription.user_id)
            logger.info(f"⏰ Subscription expired for user {subscription.user_id}")

        return expired_users

    def get_trials_expiring_soon(self, days: int = 1) -> List[Subscription]:
        """Получение пробных периодов, которые истекают скоро"""
        return self.subscription_repo.get_trials_expiring_soon(days)

    def get_subscription_status_text(self, user: User) -> str:
        """Получить текстовое описание статуса подписки"""
        subscription = self.get_by_user(user)
        if not subscription:
            return "❌ Нет подписки"
        return subscription.status_text