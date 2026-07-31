from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Subscription:
    """Модель подписки"""
    id: int
    user_id: int
    is_active: bool = True
    starts_at: datetime = datetime.now()
    expires_at: datetime = datetime.now() + timedelta(days=30)
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    @property
    def days_left(self) -> int:
        """Количество дней до истечения"""
        if not self.is_active:
            return 0
        delta = self.expires_at - datetime.now()
        return max(0, delta.days)

    @property
    def is_expired(self) -> bool:
        """Проверка на истечение"""
        if not self.is_active:
            return True
        return datetime.now() > self.expires_at

    def extend(self, days: int = 30):
        """Продление подписки"""
        if self.is_expired:
            self.starts_at = datetime.now()
        self.expires_at = self.expires_at + timedelta(days=days)
        self.is_active = True
        self.updated_at = datetime.now()

    def deactivate(self):
        """Деактивация подписки"""
        self.is_active = False
        self.updated_at = datetime.now()