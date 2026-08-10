from typing import Optional, List
from datetime import datetime
from models.user import User
from repositories.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Репозиторий пользователей"""

    def create(self, user: User) -> User:
        logger.info(f"📝 Создание пользователя {user.telegram_id}")
        result = self.db.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user.telegram_id, user.username, user.first_name, user.last_name, user.is_active)
        )
        user.id = result.lastrowid
        logger.info(f"   ✅ Создан пользователь ID={user.id}")
        return user

    def get_by_id(self, id: int) -> Optional[User]:
        data = self.db.fetch_one(
            "SELECT * FROM users WHERE id = ?",
            (id,)
        )
        return User.from_dict(data) if data else None

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        data = self.db.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        return User.from_dict(data) if data else None

    def get_or_create(self, telegram_id: int, username: Optional[str],
                      first_name: str, last_name: Optional[str]) -> User:
        user = self.get_by_telegram_id(telegram_id)
        if user:
            if (user.username != username or
                    user.first_name != first_name or
                    user.last_name != last_name):
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user = self.update(user)
            return user

        user = User(
            id=0,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        return self.create(user)

    def update(self, user: User) -> User:
        self.db.execute(
            """
            UPDATE users
            SET username   = ?,
                first_name = ?,
                last_name  = ?,
                is_active  = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user.username, user.first_name, user.last_name, user.is_active, user.id)
        )
        return user

    def delete(self, id: int) -> bool:
        result = self.db.execute(
            "DELETE FROM users WHERE id = ?",
            (id,)
        )
        return result.rowcount > 0

    def get_all_active(self) -> List[User]:
        data_list = self.db.fetch_all(
            "SELECT * FROM users WHERE is_active = 1"
        )
        return [User.from_dict(data) for data in data_list]