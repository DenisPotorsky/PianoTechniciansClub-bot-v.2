"""
Модель пользователя
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Модель пользователя"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    is_active: bool = True
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def display_name(self) -> str:
        """
        Имя для отображения.
        Если есть username — показывает его, иначе показывает ID.
        """
        if self.username:
            return f"@{self.username}"
        return f"ID: {self.telegram_id}"

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Создание из словаря"""
        return cls(
            id=data['id'],
            telegram_id=data['telegram_id'],
            username=data.get('username'),
            first_name=data['first_name'],
            last_name=data.get('last_name'),
            is_active=bool(data.get('is_active', True)),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else datetime.now()
        )