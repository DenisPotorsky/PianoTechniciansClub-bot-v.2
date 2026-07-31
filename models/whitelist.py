from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class WhitelistRole(Enum):
    """Роли в белом списке"""
    FOUNDER = "founder"
    EXPERT = "expert"
    VIP = "vip"
    LIFETIME = "lifetime"
    TEMPORARY = "temporary"

    @property
    def display_name(self) -> str:
        """Отображаемое имя роли"""
        names = {
            "founder": "👑 Основатель",
            "expert": "🎯 Эксперт",
            "vip": "⭐ VIP-мастер",
            "lifetime": "♾️ Пожизненный доступ",
            "temporary": "⏳ Временный доступ"
        }
        return names.get(self.value, self.value)

    @property
    def priority(self) -> int:
        """Приоритет роли (чем выше, тем больше прав)"""
        priorities = {
            "founder": 5,
            "expert": 4,
            "lifetime": 3,
            "vip": 2,
            "temporary": 1
        }
        return priorities.get(self.value, 0)


@dataclass
class WhitelistEntry:
    """Запись в белом списке"""
    id: int
    user_id: int
    role: WhitelistRole
    reason: str
    added_by: int
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    @property
    def is_expired(self) -> bool:
        """Проверка на истечение"""
        if not self.is_active:
            return True
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_permanent(self) -> bool:
        """Проверка на постоянный доступ"""
        return self.role in [WhitelistRole.FOUNDER, WhitelistRole.LIFETIME]

    def deactivate(self):
        """Деактивация записи"""
        self.is_active = False
        self.updated_at = datetime.now()