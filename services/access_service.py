from typing import Tuple, Optional
from models.user import User
from services.subscription_service import SubscriptionService
from services.whitelist_service import WhitelistService
from models.whitelist import WhitelistRole


class AccessService:
    """Сервис управления доступом"""

    def __init__(self, subscription_service: SubscriptionService, whitelist_service: WhitelistService):
        self.subscription_service = subscription_service
        self.whitelist_service = whitelist_service

    def has_access(self, user: User) -> Tuple[bool, str]:
        """
        Проверка доступа пользователя
        Возвращает (доступ, тип_доступа)
        """
        # Белый список имеет приоритет
        if self.whitelist_service.is_in_whitelist(user):
            role = self.whitelist_service.get_user_role(user)
            return True, f"whitelist_{role.value}"

        # Проверка подписки
        if self.subscription_service.has_active_subscription(user):
            return True, "subscription"

        return False, "none"

    def get_access_description(self, user: User) -> str:
        """Получение описания доступа"""
        has_access, access_type = self.has_access(user)

        if not has_access:
            return "❌ Нет доступа"

        if access_type.startswith("whitelist_"):
            role_str = access_type.replace("whitelist_", "")
            try:
                role = WhitelistRole(role_str)
                return f"✅ {role.display_name}"
            except ValueError:
                return f"✅ Белый список ({role_str})"

        if access_type == "subscription":
            subscription = self.subscription_service.get_by_user(user)
            if subscription:
                return f"✅ Подписка (осталось {subscription.days_left} дней)"

        return "✅ Доступ открыт"

    def get_access_level(self, user: User) -> int:
        """Получение уровня доступа (для сортировки)"""
        has_access, access_type = self.has_access(user)

        if not has_access:
            return 0

        if access_type.startswith("whitelist_"):
            role_str = access_type.replace("whitelist_", "")
            try:
                role = WhitelistRole(role_str)
                return role.priority + 10
            except ValueError:
                return 10

        if access_type == "subscription":
            return 5

        return 1