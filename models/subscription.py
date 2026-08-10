"""
Модель подписки с поддержкой пробного периода
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Subscription:
    """Модель подписки с поддержкой пробного периода"""
    id: int
    user_id: int
    is_active: bool = True
    starts_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=30))
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

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

    @property
    def is_trial(self) -> bool:
        """Проверка, активен ли пробный период"""
        if not self.trial_start or not self.trial_end:
            return False
        return self.trial_start <= datetime.now() <= self.trial_end

    @property
    def trial_days_left(self) -> int:
        """Количество дней до окончания пробного периода"""
        if not self.trial_end:
            return 0
        if datetime.now() > self.trial_end:
            return 0
        delta = self.trial_end - datetime.now()
        return max(0, delta.days)

    @property
    def has_trial_available(self) -> bool:
        """Проверка, доступен ли пробный период (был ли уже использован)"""
        return self.trial_start is None

    @property
    def status_text(self) -> str:
        """Текстовое описание статуса подписки"""
        if not self.is_active:
            return "❌ Неактивна"
        if self.is_trial:
            return f"🔰 Пробный период (осталось {self.trial_days_left} дн.)"
        if self.is_expired:
            return "❌ Истекла"
        return f"✅ Активна (осталось {self.days_left} дн.)"

    def start_trial(self, days: int = 7):
        """Начинает пробный период"""
        now = datetime.now()
        self.trial_start = now
        self.trial_end = now + timedelta(days=days)
        self.expires_at = self.trial_end
        self.is_active = True
        self.starts_at = now
        self.updated_at = now
        print(f"🔰 Trial started: {self.trial_start} -> {self.trial_end}")

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

    def to_dict(self) -> dict:
        """Преобразование в словарь для базы данных"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'is_active': 1 if self.is_active else 0,
            'starts_at': self.starts_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'trial_start': self.trial_start.isoformat() if self.trial_start else None,
            'trial_end': self.trial_end.isoformat() if self.trial_end else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Subscription':
        """Создание из словаря"""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            is_active=bool(data.get('is_active', 1)),
            starts_at=datetime.fromisoformat(data['starts_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            trial_start=datetime.fromisoformat(data['trial_start']) if data.get('trial_start') else None,
            trial_end=datetime.fromisoformat(data['trial_end']) if data.get('trial_end') else None,
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )