from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')


class BaseService(ABC, Generic[T]):
    """Базовый сервис"""

    @abstractmethod
    def create(self, data: dict) -> T:
        """Создание сущности"""
        pass

    @abstractmethod
    def get(self, id: int) -> T:
        """Получение сущности"""
        pass

    @abstractmethod
    def update(self, id: int, data: dict) -> T:
        """Обновление сущности"""
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Удаление сущности"""
        pass