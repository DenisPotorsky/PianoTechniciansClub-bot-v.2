from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes


class BaseHandler(ABC):
    """Базовый абстрактный обработчик"""

    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Основной метод обработки"""
        pass

    @abstractmethod
    def get_command(self) -> str:
        """Получение команды"""
        pass

    async def check_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверка доступа (может быть переопределен)"""
        return True