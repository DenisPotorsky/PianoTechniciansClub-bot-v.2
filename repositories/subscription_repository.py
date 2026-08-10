"""
Репозиторий для работы с подписками
"""

from typing import Optional, List
from datetime import datetime
from models.subscription import Subscription
from repositories.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class SubscriptionRepository(BaseRepository[Subscription]):
    """Репозиторий подписок с поддержкой пробного периода"""

    def create(self, subscription: Subscription) -> Subscription:
        """Создание подписки с пробным периодом"""
        logger.info(f"📝 Creating subscription for user {subscription.user_id}")
        logger.info(f"   trial_start: {subscription.trial_start}")
        logger.info(f"   trial_end: {subscription.trial_end}")

        result = self.db.execute(
            """
            INSERT INTO subscriptions (
                user_id, is_active, starts_at, expires_at, 
                trial_start, trial_end
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                subscription.user_id,
                subscription.is_active,
                subscription.starts_at,
                subscription.expires_at,
                subscription.trial_start,
                subscription.trial_end
            )
        )
        subscription.id = result.lastrowid
        logger.info(f"   ✅ Created subscription id={subscription.id}")
        return subscription

    def get_by_id(self, id: int) -> Optional[Subscription]:
        data = self.db.fetch_one(
            "SELECT * FROM subscriptions WHERE id = ?",
            (id,)
        )
        return self._dict_to_subscription(data) if data else None

    def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
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
        data_list = self.db.fetch_all(
            """
            SELECT * FROM subscriptions 
            WHERE is_active = 1 AND expires_at < CURRENT_TIMESTAMP
            """
        )
        return [self._dict_to_subscription(data) for data in data_list]

    def get_trials_expiring_soon(self, days: int = 1) -> List[Subscription]:
        data_list = self.db.fetch_all(
            """
            SELECT * FROM subscriptions 
            WHERE is_active = 1 
            AND trial_end IS NOT NULL 
            AND trial_end <= datetime('now', '+' || ? || ' days')
            AND trial_end > datetime('now')
            """,
            (days,)
        )
        return [self._dict_to_subscription(data) for data in data_list]

    def update(self, subscription: Subscription) -> Subscription:
        """Обновление подписки с пробным периодом"""
        logger.info(f"📝 Updating subscription id={subscription.id}")
        logger.info(f"   trial_start: {subscription.trial_start}")
        logger.info(f"   trial_end: {subscription.trial_end}")

        self.db.execute(
            """
            UPDATE subscriptions 
            SET is_active = ?, starts_at = ?, expires_at = ?, 
                trial_start = ?, trial_end = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                subscription.is_active,
                subscription.starts_at,
                subscription.expires_at,
                subscription.trial_start,
                subscription.trial_end,
                subscription.id
            )
        )
        logger.info(f"   ✅ Updated subscription id={subscription.id}")
        return subscription

    def delete(self, id: int) -> bool:
        result = self.db.execute(
            "DELETE FROM subscriptions WHERE id = ?",
            (id,)
        )
        return result.rowcount > 0

    def get_all_active(self) -> List[Subscription]:
        data_list = self.db.fetch_all(
            "SELECT * FROM subscriptions WHERE is_active = 1"
        )
        return [self._dict_to_subscription(data) for data in data_list]

    @staticmethod
    def _dict_to_subscription(data: dict) -> Subscription:
        return Subscription(
            id=data['id'],
            user_id=data['user_id'],
            is_active=bool(data['is_active']),
            starts_at=datetime.fromisoformat(data['starts_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            trial_start=datetime.fromisoformat(data['trial_start']) if data.get('trial_start') else None,
            trial_end=datetime.fromisoformat(data['trial_end']) if data.get('trial_end') else None,
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )