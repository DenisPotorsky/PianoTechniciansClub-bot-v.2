from typing import Optional, List
from datetime import datetime, timedelta
from models.user import User
from models.whitelist import WhitelistEntry, WhitelistRole
from repositories.whitelist_repository import WhitelistRepository
from repositories.user_repository import UserRepository
from services.base_service import BaseService


class WhitelistService(BaseService[WhitelistEntry]):
    """Сервис для управления белым списком"""

    def __init__(self, whitelist_repo: WhitelistRepository, user_repo: UserRepository):
        self.whitelist_repo = whitelist_repo
        self.user_repo = user_repo

    def create(self, data: dict) -> WhitelistEntry:
        """Создание записи в белом списке"""
        entry = WhitelistEntry(
            id=0,
            user_id=data['user_id'],
            role=data['role'],
            reason=data['reason'],
            added_by=data['added_by'],
            expires_at=data.get('expires_at')
        )
        return self.whitelist_repo.create(entry)

    def get(self, id: int) -> Optional[WhitelistEntry]:
        """Получение записи по ID"""
        return self.whitelist_repo.get_by_id(id)

    def get_by_user(self, user: User) -> Optional[WhitelistEntry]:
        """Получение записи пользователя"""
        return self.whitelist_repo.get_by_user_id(user.id)

    def is_in_whitelist(self, user: User) -> bool:
        """Проверка наличия в белом списке"""
        entry = self.get_by_user(user)
        if not entry:
            return False
        if entry.is_expired:
            entry.deactivate()
            self.whitelist_repo.update(entry)
            return False
        return entry.is_active

    def get_user_role(self, user: User) -> Optional[WhitelistRole]:
        """Получение роли пользователя"""
        entry = self.get_by_user(user)
        if entry and entry.is_active and not entry.is_expired:
            return entry.role
        return None

    def add_to_whitelist(self, user: User, role: WhitelistRole, reason: str,
                         added_by: User, days: Optional[int] = None) -> WhitelistEntry:
        """Добавление в белый список"""
        # Проверяем существующую запись
        existing = self.whitelist_repo.get_by_user_id(user.id)

        if existing:
            existing.role = role
            existing.reason = reason
            existing.added_by = added_by.id
            existing.expires_at = datetime.now() + timedelta(days=days) if days else None
            existing.is_active = True
            return self.whitelist_repo.update(existing)

        # Создаем новую запись
        entry = WhitelistEntry(
            id=0,
            user_id=user.id,
            role=role,
            reason=reason,
            added_by=added_by.id,
            expires_at=datetime.now() + timedelta(days=days) if days else None
        )
        return self.whitelist_repo.create(entry)

    def remove_from_whitelist(self, user: User) -> bool:
        """Удаление из белого списка"""
        return self.whitelist_repo.deactivate_by_user_id(user.id)

    def update(self, id: int, data: dict) -> Optional[WhitelistEntry]:
        """Обновление записи"""
        entry = self.whitelist_repo.get_by_id(id)
        if not entry:
            return None

        if 'role' in data:
            entry.role = data['role']
        if 'reason' in data:
            entry.reason = data['reason']
        if 'expires_at' in data:
            entry.expires_at = data['expires_at']
        if 'is_active' in data:
            entry.is_active = data['is_active']

        return self.whitelist_repo.update(entry)

    def delete(self, id: int) -> bool:
        """Удаление записи"""
        return self.whitelist_repo.delete(id)

    def get_all_whitelist_users(self) -> List[User]:
        """Получение всех пользователей в белом списке"""
        entries = self.whitelist_repo.get_all_active()
        users = []
        for entry in entries:
            user = self.user_repo.get_by_id(entry.user_id)
            if user:
                users.append(user)
        return users

    def check_expired_entries(self) -> List[WhitelistEntry]:
        """Проверка и деактивация истекших записей"""
        expired = self.whitelist_repo.get_expired_active()
        for entry in expired:
            entry.deactivate()
            self.whitelist_repo.update(entry)
        return expired

    def can_manage_whitelist(self, user: User) -> bool:
        """Проверка прав на управление белым списком"""
        role = self.get_user_role(user)
        return role in [WhitelistRole.FOUNDER, WhitelistRole.EXPERT] if role else False