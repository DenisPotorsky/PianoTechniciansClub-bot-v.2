"""
Модель подписки с поддержкой пробного периода
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Subscription:
    """Модель подписки с поддержкой пробного периода"""
    id: int
    user_id: int
    is_active: bool = True
    starts_at: datetime = datetime.now()
    expires_at: datetime = datetime.now() + timedelta(days=30)
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    @property
    def days_left(self) -> int:
        if not self.is_active:
            return 0
        delta = self.expires_at - datetime.now()
        return max(0, delta.days)

    @property
    def is_expired(self) -> bool:
        if not self.is_active:
            return True
        return datetime.now() > self.expires_at

    @property
    def is_trial(self) -> bool:
        if not self.trial_start or not self.trial_end:
            return False
        return self.trial_start <= datetime.now() <= self.trial_end

    @property
    def trial_days_left(self) -> int:
        if not self.trial_end:
            return 0
        if datetime.now() > self.trial_end:
            return 0
        delta = self.trial_end - datetime.now()
        return max(0, delta.days)

    @property
    def has_trial_available(self) -> bool:
        if self.trial_start:
            return False
        return True

    @property
    def status_text(self) -> str:
        if not self.is_active:
            return "❌ Неактивна"
        if self.is_trial:
            return f"🔰 Пробный период (осталось {self.trial_days_left} дн.)"
        if self.is_expired:
            return "❌ Истекла"
        return f"✅ Активна (осталось {self.days_left} дн.)"

    def start_trial(self, days: int = 7):
        """Начинает пробный период"""
        self.trial_start = datetime.now()
        self.trial_end = datetime.now() + timedelta(days=days)
        self.expires_at = self.trial_end
        self.is_active = True
        self.starts_at = datetime.now()
        self.updated_at = datetime.now()
        print(f"🔰 Trial started: {self.trial_start} -> {self.trial_end}")

    def extend(self, days: int = 30):
        if self.is_expired:
            self.starts_at = datetime.now()
        self.expires_at = self.expires_at + timedelta(days=days)
        self.is_active = True
        self.updated_at = datetime.now()

    def deactivate(self):
        self.is_active = False
        self.updated_at = datetime.now()