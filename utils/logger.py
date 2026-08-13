"""
Модуль для красивого логирования
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


class Colors:
    """Цвета для терминала"""
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    DIM = "\033[2m"


class Emoji:
    INFO = "📘"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    CRITICAL = "🔥"
    DEBUG = "🐛"
    STARTUP = "🚀"


class ConflictFilter(logging.Filter):
    """Фильтр для игнорирования ошибок Conflict"""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "Conflict" in msg or "getUpdates" in msg:
            return False
        return True


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветами"""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.RED,
    }

    LEVEL_EMOJIS = {
        logging.DEBUG: Emoji.DEBUG,
        logging.INFO: Emoji.INFO,
        logging.WARNING: Emoji.WARNING,
        logging.ERROR: Emoji.ERROR,
        logging.CRITICAL: Emoji.CRITICAL,
    }

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_name = record.levelname[:8]
        color = self.LEVEL_COLORS.get(record.levelno, "")
        emoji = self.LEVEL_EMOJIS.get(record.levelno, "📌")
        msg = record.getMessage()

        return f"{Colors.DIM}{timestamp}{Colors.RESET} | {color}{emoji} {level_name}{Colors.RESET} | {msg}"


def setup_logger(name: str = "PianoMasterClub"):
    """Настройка логгера"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        logger.handlers.clear()

    # Консольный обработчик с фильтром
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColoredFormatter())
    handler.addFilter(ConflictFilter())
    logger.addHandler(handler)

    # Создаём папку для логов
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Файловый логгер
    log_file = logs_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    file_handler.addFilter(ConflictFilter())
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()