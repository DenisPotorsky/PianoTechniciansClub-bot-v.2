from typing import Optional, List
from datetime import datetime
from models.whitelist import WhitelistEntry, WhitelistRole
from repositories.base_repository import BaseRepository


class WhitelistRepository(BaseRepository[WhitelistEntry]):
    """Репозиторий белого списка"""

    def create(self, entry: WhitelistEntry) -> WhitelistEntry:
        """Создание записи"""
        result = self.db.execute(
            """
            INSERT INTO whitelist (user_id, role, reason, added_by, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entry.user_id, entry.role.value, entry.reason,
             entry.added_by, entry.expires_at, entry.is_active)
        )
        entry.id = result.lastrowid
        return entry

    def get_by_id(self, id: int) -> Optional[WhitelistEntry]:
        """Получение по ID"""
        data = self.db.fetch_one(
            "SELECT * FROM whitelist WHERE id = ?",
            (id,)
        )
        return self._dict_to_entry(data) if data else None

    def get_by_user_id(self, user_id: int) -> Optional[WhitelistEntry]:
        """Получение активной записи пользователя"""
        data = self.db.fetch_one(
            """
            SELECT * FROM whitelist 
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id,)
        )
        return self._dict_to_entry(data) if data else None

    def get_expired_active(self) -> List[WhitelistEntry]:
        """Получение активных истекших записей"""
        data_list = self.db.fetch_all(
            """
            SELECT * FROM whitelist 
            WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """
        )
        return [self._dict_to_entry(data) for data in data_list]

    def update(self, entry: WhitelistEntry) -> WhitelistEntry:
        """Обновление записи"""
        self.db.execute(
            """
            UPDATE whitelist 
            SET role = ?, reason = ?, expires_at = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (entry.role.value, entry.reason, entry.expires_at, entry.is_active, entry.id)
        )
        return entry

    def delete(self, id: int) -> bool:
        """Удаление записи"""
        result = self.db.execute(
            "DELETE FROM whitelist WHERE id = ?",
            (id,)
        )
        return result.rowcount > 0

    def deactivate_by_user_id(self, user_id: int) -> bool:
        """Деактивация записи по ID пользователя"""
        result = self.db.execute(
            """
            UPDATE whitelist 
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND is_active = 1
            """,
            (user_id,)
        )
        return result.rowcount > 0

    def get_all_active(self) -> List[WhitelistEntry]:
        """Получение всех активных записей"""
        data_list = self.db.fetch_all(
            "SELECT * FROM whitelist WHERE is_active = 1 ORDER BY created_at DESC"
        )
        return [self._dict_to_entry(data) for data in data_list]

    @staticmethod
    def _dict_to_entry(data: dict) -> WhitelistEntry:
        """Преобразование словаря в объект"""
        return WhitelistEntry(
            id=data['id'],
            user_id=data['user_id'],
            role=WhitelistRole(data['role']),
            reason=data['reason'] or "",
            added_by=data['added_by'],
            expires_at=datetime.fromisoformat(data['expires_at']) if data['expires_at'] else None,
            is_active=bool(data['is_active']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )