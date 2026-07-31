from typing import Union, Tuple


class Validators:
    """Класс для валидации данных"""

    @staticmethod
    def validate_positive_number(value: Union[int, float], name: str) -> Tuple[bool, str]:
        """Проверка, что число положительное"""
        if value <= 0:
            return False, f"{name} должен быть положительным числом"
        return True, ""

    @staticmethod
    def validate_string_length(value: str, min_len: int = 1, max_len: int = 100) -> Tuple[bool, str]:
        """Проверка длины строки"""
        if len(value) < min_len:
            return False, f"Длина должна быть не менее {min_len} символов"
        if len(value) > max_len:
            return False, f"Длина должна быть не более {max_len} символов"
        return True, ""

    @staticmethod
    def validate_telegram_id(telegram_id: int) -> Tuple[bool, str]:
        """Проверка Telegram ID"""
        if telegram_id <= 0:
            return False, "Telegram ID должен быть положительным числом"
        return True, ""

    @staticmethod
    def validate_role(role: str, available_roles: list) -> Tuple[bool, str]:
        """Проверка роли"""
        if role not in available_roles:
            return False, f"Недоступная роль. Доступные: {', '.join(available_roles)}"
        return True, ""