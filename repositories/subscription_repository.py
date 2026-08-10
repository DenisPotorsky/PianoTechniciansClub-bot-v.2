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

    def __init__(self, db):
        self.db = db
        self._init_table()

    def _init_table(self):
        """Проверяет и создаёт таблицу subscriptions с нужными колонками"""
        with self.db.get_connection() as conn:
            # Проверяем наличие колонок
            cursor = conn.execute("PRAGMA table_info(subscriptions)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'trial_start' not in columns:
                conn.execute("ALTER TABLE subscriptions ADD COLUMN trial_start TIMESTAMP")
                logger.info("✅ Добавлена колонка trial_start")

            if 'trial_end' not in columns:
                conn.execute("ALTER TABLE subscriptions ADD COLUMN trial_end TIMESTAMP")
                logger.info("✅ Добавлена колонка trial_end")

            conn.commit()

    def create(self, subscription: Subscription) -> Subscription:
        """Создание подписки с пробным периодом"""
        logger.info(f"📝 СОЗДАНИЕ ПОДПИСКИ для user_id={subscription.user_id}")
        logger.info(f"   trial_start: {subscription.trial_start}")
        logger.info(f"   trial_end: {subscription.trial_end}")
        logger.info(f"   expires_at: {subscription.expires_at}")

        result = self.db.execute(
            """
            INSERT INTO subscriptions (
                user_id, is_active, starts_at, expires_at, 
                trial_start, trial_end
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                subscription.user_id,
                1 if subscription.is_active else 0,
                subscription.starts_at,
                subscription.expires_at,
                subscription.trial_start,
                subscription.trial_end
            )
        )
        subscription.id = result.lastrowid
        logger.info(f"   ✅ ПОДПИСКА СОЗДАНА id={subscription.id}")
        return subscription

    def get_by_id(self, id: int) -> Optional[Subscription]:
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

    def get_all_by_user_id(self, user_id: int) -> List[Subscription]:
        """Получение всех подписок пользователя (включая неактивные)"""
        data_list = self.db.fetch_all(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return [self._dict_to_subscription(data) for data in data_list]

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

    def get_all_active_trials(self) -> List[Subscription]:
        """Получение всех активных пробных периодов"""
        data_list = self.db.fetch_all(
            """
            SELECT * FROM subscriptions 
            WHERE is_active = 1 
            AND trial_start IS NOT NULL 
            AND trial_end > CURRENT_TIMESTAMP
            """
        )
        return [self._dict_to_subscription(data) for data in data_list]

    def update(self, subscription: Subscription) -> Subscription:
        """Обновление подписки"""
        logger.info(f"📝 ОБНОВЛЕНИЕ ПОДПИСКИ id={subscription.id}")
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
                1 if subscription.is_active else 0,
                subscription.starts_at,
                subscription.expires_at,
                subscription.trial_start,
                subscription.trial_end,
                subscription.id
            )
        )
        logger.info(f"   ✅ ПОДПИСКА ОБНОВЛЕНА id={subscription.id}")
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

    def count_active_trials(self) -> int:
        """Количество активных пробных периодов"""
        result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count FROM subscriptions 
            WHERE is_active = 1 
            AND trial_start IS NOT NULL 
            AND trial_end > CURRENT_TIMESTAMP
            """
        )
        return result['count'] if result else 0

    def count_active_subscriptions(self) -> int:
        """Количество активных платных подписок (без пробных)"""
        result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count FROM subscriptions 
            WHERE is_active = 1 
            AND expires_at > CURRENT_TIMESTAMP
            AND (trial_start IS NULL OR trial_end <= CURRENT_TIMESTAMP)
            """
        )
        return result['count'] if result else 0

    def count_expired_subscriptions(self) -> int:
        """Количество истекших подписок"""
        result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count FROM subscriptions 
            WHERE is_active = 0 OR expires_at <= CURRENT_TIMESTAMP
            """
        )
        return result['count'] if result else 0

    @staticmethod
    def _dict_to_subscription(data: dict) -> Subscription:
        return Subscription(
            id=data['id'],
            user_id=data['user_id'],
            is_active=bool(data.get('is_active', 0)),
            starts_at=datetime.fromisoformat(data['starts_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            trial_start=datetime.fromisoformat(data['trial_start']) if data.get('trial_start') else None,
            trial_end=datetime.fromisoformat(data['trial_end']) if data.get('trial_end') else None,
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )