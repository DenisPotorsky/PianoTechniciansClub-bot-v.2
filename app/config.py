import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Конфигурация приложения с валидацией"""

    # Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Payment
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/piano_club.db")

    # Telegram Channels - ссылки на канал и чат
    CHANNEL_URL: str = os.getenv("CHANNEL_URL", "https://t.me/piano_club_channel")
    CHAT_URL: str = os.getenv("CHAT_URL", "https://t.me/piano_club_chat")

    # Subscription
    SUBSCRIPTION_PRICE: int = int(os.getenv("SUBSCRIPTION_PRICE", "999"))
    SUBSCRIPTION_DAYS: int = int(os.getenv("SUBSCRIPTION_DAYS", "30"))

    # Admin
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x
    ])

    # Whitelist
    DEFAULT_WHITELIST_ROLE: str = os.getenv("DEFAULT_WHITELIST_ROLE", "vip")

    @property
    def db_path(self) -> str:
        """Получает путь к базе данных"""
        if self.DATABASE_URL.startswith("sqlite:///"):
            path = self.DATABASE_URL.replace("sqlite:///", "")
            db_dir = os.path.dirname(path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            return path
        return self.DATABASE_URL

    def validate(self) -> bool:
        """Проверяет наличие обязательных переменных"""
        required = [self.BOT_TOKEN, self.YOOKASSA_SHOP_ID, self.YOOKASSA_SECRET_KEY]
        return all(required)


config = Config()