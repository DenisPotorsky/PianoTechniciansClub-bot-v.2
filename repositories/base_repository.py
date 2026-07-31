from abc import ABC, abstractmethod
from typing import Optional, List, TypeVar, Generic
from app.database import Database

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Базовый репозиторий"""

    def __init__(self, db: Database):
        self.db = db

    @abstractmethod
    def create(self, entity: T) -> T:
        """Создание записи"""
        pass

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        """Получение по ID"""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """Обновление записи"""
        pass

    @abstractmethod
    def delete(self, id: int) -> bool:
        """Удаление записи"""
        pass