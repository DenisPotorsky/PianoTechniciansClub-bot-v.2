"""
Сервис для работы с пользователями
"""

from typing import Optional
from models.user import User
from repositories.user_repository import UserRepository
from services.base_service import BaseService
import logging

logger = logging.getLogger(__name__)


class UserService(BaseService[User]):
    """Сервис для работы с пользователями"""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def create(self, data: dict) -> User:
        user = User(
            id=0,
            telegram_id=data['telegram_id'],
            username=data.get('username'),
            first_name=data['first_name'],
            last_name=data.get('last_name')
        )
        return self.user_repo.create(user)

    def get(self, id: int) -> Optional[User]:
        return self.user_repo.get_by_id(id)

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return self.user_repo.get_by_telegram_id(telegram_id)

    def get_or_create(self, telegram_id: int, username: Optional[str],
                      first_name: str, last_name: Optional[str]) -> User:
        """Получение или создание пользователя"""
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if user:
            logger.debug(f"Пользователь {telegram_id} уже существует")
            # Обновляем данные
            if user.username != username or user.first_name != first_name or user.last_name != last_name:
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user = self.user_repo.update(user)
                logger.info(f"Обновлён пользователь {telegram_id}")
            return user

        # СОЗДАЁМ НОВОГО
        logger.info(f"Создаём нового пользователя {telegram_id} ({first_name})")
        user = User(
            id=0,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        result = self.user_repo.create(user)
        logger.info(f"✅ Создан пользователь {telegram_id} с ID {result.id}")
        return result

    def update(self, id: int, data: dict) -> Optional[User]:
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
        return self.user_repo.delete(id)

    def get_all_active(self) -> list[User]:
        return self.user_repo.get_all_active()