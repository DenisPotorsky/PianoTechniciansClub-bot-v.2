from typing import Optional
from models.user import User
from repositories.user_repository import UserRepository
from services.base_service import BaseService


class UserService(BaseService[User]):
    """Сервис для работы с пользователями"""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def create(self, data: dict) -> User:
        """Создание пользователя"""
        user = User(
            id=0,
            telegram_id=data['telegram_id'],
            username=data.get('username'),
            first_name=data['first_name'],
            last_name=data.get('last_name')
        )
        return self.user_repo.create(user)

    def get(self, id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        return self.user_repo.get_by_id(id)

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        return self.user_repo.get_by_telegram_id(telegram_id)

    def get_or_create(self, telegram_id: int, username: Optional[str],
                      first_name: str, last_name: Optional[str]) -> User:
        """Получение или создание пользователя"""
        return self.user_repo.get_or_create(telegram_id, username, first_name, last_name)

    def update(self, id: int, data: dict) -> Optional[User]:
        """Обновление пользователя"""
        user = self.user_repo.get_by_id(id)
        if not user:
            return None

        if 'username' in data:
            user.username = data['username']
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'is_active' in data:
            user.is_active = data['is_active']

        return self.user_repo.update(user)

    def delete(self, id: int) -> bool:
        """Удаление пользователя"""
        return self.user_repo.delete(id)

    def get_all_active(self) -> list[User]:
        """Получение всех активных пользователей"""
        return self.user_repo.get_all_active()
