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
        logger.info("✅ SubscriptionService инициализирован")

    def create(self, data: dict) -> Subscription:
        subscription = Subscription(
            id=0,
            user_id=data['user_id'],
            expires_at=datetime.now() + timedelta(days=data.get('days', config.SUBSCRIPTION_DAYS))
        )
        return self.subscription_repo.create(subscription)

    def get(self, id: int) -> Optional[Subscription]:
        return self.subscription_repo.get_by_id(id)

    def get_by_user(self, user: User) -> Optional[Subscription]:
        return self.subscription_repo.get_by_user_id(user.id)

    def get_all_subscriptions(self, user: User) -> List[Subscription]:
        return self.subscription_repo.get_all_by_user_id(user.id)

    def has_active_subscription(self, user: User) -> bool:
        subscription = self.get_by_user(user)
        if not subscription:
            logger.debug(f"Нет подписки для user {user.id}")
            return False
        if not subscription.is_active:
            logger.debug(f"Подписка неактивна для user {user.id}")
            return False
        if subscription.is_expired:
            logger.debug(f"Подписка истекла для user {user.id}")
            return False
        logger.debug(f"Подписка активна для user {user.id}")
        return True

    def is_on_trial(self, user: User) -> bool:
        subscription = self.get_by_user(user)
        if not subscription:
            return False
        return subscription.is_trial

    def has_used_trial(self, user: User) -> bool:
        subscription = self.get_by_user(user)
        if not subscription:
            return False
        return subscription.trial_start is not None

    def start_trial(self, user: User) -> Subscription:
        """
        Начинает пробный период для пользователя и СОХРАНЯЕТ в базу
        """
        logger.info(f"🔄 НАЧАЛО ПРОБНОГО ПЕРИОДА для user {user.id} ({user.first_name})")

        # Проверяем, есть ли уже подписка
        existing = self.subscription_repo.get_by_user_id(user.id)

        if existing:
            logger.info(f"   Найдена существующая подписка id={existing.id}")

            if existing.trial_start is not None:
                logger.warning(f"   Пробный период уже использован для user {user.id}")
                raise ValueError("Пробный период уже был использован")

            # Обновляем существующую подписку
            existing.start_trial(self.TRIAL_DAYS)
            result = self.subscription_repo.update(existing)
            logger.info(f"   ✅ ПРОБНЫЙ ПЕРИОД ОБНОВЛЁН: {result.trial_start} -> {result.trial_end}")
            return result

        # Создаём НОВУЮ подписку
        logger.info(f"   Создаём новую подписку для user {user.id}")

        now = datetime.now()
        trial_end = now + timedelta(days=self.TRIAL_DAYS)

        subscription = Subscription(
            id=0,
            user_id=user.id,
            is_active=True,
            starts_at=now,
            expires_at=trial_end,
            trial_start=now,
            trial_end=trial_end,
            created_at=now,
            updated_at=now
        )

        # СОХРАНЯЕМ В БАЗУ
        result = self.subscription_repo.create(subscription)
        logger.info(f"   ✅ ПРОБНЫЙ ПЕРИОД СОЗДАН: {result.trial_start} -> {result.trial_end}")
        logger.info(f"   ✅ ID подписки: {result.id}")

        return result

    def activate_subscription(self, user: User, days: int = None) -> Subscription:
        if days is None:
            days = config.SUBSCRIPTION_DAYS

        subscription = self.subscription_repo.get_by_user_id(user.id)

        if subscription:
            subscription.extend(days)
            return self.subscription_repo.update(subscription)
        else:
            subscription = Subscription(
                id=0,
                user_id=user.id,
                expires_at=datetime.now() + timedelta(days=days)
            )
            return self.subscription_repo.create(subscription)

    def deactivate_subscription(self, user: User) -> bool:
        subscription = self.subscription_repo.get_by_user_id(user.id)
        if subscription:
            subscription.deactivate()
            self.subscription_repo.update(subscription)
            return True
        return False

    def update(self, id: int, data: dict) -> Optional[Subscription]:
        subscription = self.subscription_repo.get_by_id(id)
        if not subscription:
            return None

        if 'is_active' in data:
            subscription.is_active = data['is_active']
        if 'expires_at' in data:
            subscription.expires_at = data['expires_at']

        return self.subscription_repo.update(subscription)

    def delete(self, id: int) -> bool:
        return self.subscription_repo.delete(id)

    def check_expired_subscriptions(self) -> List[int]:
        expired = self.subscription_repo.get_expired_active()
        expired_users = []

        for subscription in expired:
            subscription.deactivate()
            self.subscription_repo.update(subscription)
            expired_users.append(subscription.user_id)
            logger.info(f"⏰ Подписка истекла для user {subscription.user_id}")

        return expired_users

    def get_trials_expiring_soon(self, days: int = 1) -> List[Subscription]:
        return self.subscription_repo.get_trials_expiring_soon(days)

    def get_subscription_status_text(self, user: User) -> str:
        subscription = self.get_by_user(user)
        if not subscription:
            return "❌ Нет подписки"
        return subscription.status_text

    def get_statistics(self) -> dict:
        """Получение статистики по подпискам"""
        return {
            'active_trials': self.subscription_repo.count_active_trials(),
            'active_subscriptions': self.subscription_repo.count_active_subscriptions(),
            'expired_subscriptions': self.subscription_repo.count_expired_subscriptions()
        }