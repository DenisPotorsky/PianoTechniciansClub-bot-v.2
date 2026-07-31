from typing import Optional, List
from datetime import datetime
from models.subscription import Subscription
from repositories.base_repository import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    """Репозиторий подписок"""

    def create(self, subscription: Subscription) -> Subscription:
        """Создание подписки"""
        result = self.db.execute(
            """
            INSERT INTO subscriptions (user_id, is_active, starts_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (subscription.user_id, subscription.is_active,
             subscription.starts_at, subscription.expires_at)
        )
        subscription.id = result.lastrowid
        return subscription

    def get_by_id(self, id: int) -> Optional[Subscription]:
        """Получение по ID"""
        data = self.db.fetch_one(
            "SELECT * FROM subscriptions WHERE id = ?",
            (id,)
        )
        return self._dict_to_subscription(data) if data else None

    def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """Получение активной подписки пользователя"""
        data = self.db.fetch_one(
            """
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND is_active = 1
            ORDER BY expires_at DESC LIMIT 1
            """,
            (user_id,)
        )
        return self._dict_to_subscription(data) if data else None

    def get_expired_active(self) -> List[Subscription]:
        """Получение всех активных истекших подписок"""
        data_list = self.db.fetch_all(
            """
            SELECT * FROM subscriptions 
            WHERE is_active = 1 AND expires_at < CURRENT_TIMESTAMP
            """
        )
        return [self._dict_to_subscription(data) for data in data_list]

    def update(self, subscription: Subscription) -> Subscription:
        """Обновление подписки"""
        self.db.execute(
            """
            UPDATE subscriptions 
            SET is_active = ?, starts_at = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (subscription.is_active, subscription.starts_at,
             subscription.expires_at, subscription.id)
        )
        return subscription

    def delete(self, id: int) -> bool:
        """Удаление подписки"""
        result = self.db.execute(
            "DELETE FROM subscriptions WHERE id = ?",
            (id,)
        )
        return result.rowcount > 0

    def get_all_active(self) -> List[Subscription]:
        """Получение всех активных подписок"""
        data_list = self.db.fetch_all(
            "SELECT * FROM subscriptions WHERE is_active = 1"
        )
        return [self._dict_to_subscription(data) for data in data_list]

    @staticmethod
    def _dict_to_subscription(data: dict) -> Subscription:
        """Преобразование словаря в объект"""
        return Subscription(
            id=data['id'],
            user_id=data['user_id'],
            is_active=bool(data['is_active']),
            starts_at=datetime.fromisoformat(data['starts_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )