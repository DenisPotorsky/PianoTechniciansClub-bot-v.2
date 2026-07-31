from typing import Optional
from datetime import datetime, timedelta
from models.user import User
from models.subscription import Subscription
from repositories.subscription_repository import SubscriptionRepository
from services.base_service import BaseService
from app.config import config


class SubscriptionService(BaseService[Subscription]):
    """Сервис для управления подписками"""

    def __init__(self, subscription_repo: SubscriptionRepository):
        self.subscription_repo = subscription_repo

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
        """Проверка наличия активной подписки"""
        subscription = self.get_by_user(user)
        if not subscription:
            return False
        return subscription.is_active and not subscription.is_expired

    def activate_subscription(self, user: User, days: int = None) -> Subscription:
        """Активация подписки"""
        if days is None:
            days = config.SUBSCRIPTION_DAYS

        subscription = self.subscription_repo.get_by_user_id(user.id)

        if subscription:
            subscription.extend(days)
            return self.subscription_repo.update(subscription)
        else:
            new_subscription = Subscription(
                id=0,
                user_id=user.id,
                expires_at=datetime.now() + timedelta(days=days)
            )
            return self.subscription_repo.create(new_subscription)

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

    def check_expired_subscriptions(self) -> list[User]:
        """Проверка и деактивация истекших подписок"""
        expired = self.subscription_repo.get_expired_active()
        expired_users = []

        for subscription in expired:
            subscription.deactivate()
            self.subscription_repo.update(subscription)
            # Здесь можно получить пользователя через UserService
            expired_users.append(subscription.user_id)

        return expired_users