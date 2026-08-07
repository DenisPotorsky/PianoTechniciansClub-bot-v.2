"""
Модуль для красивого логирования с цветами и эмодзи
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# ANSI-коды для цветов
class Colors:
    """Цвета для терминала"""
    RESET = "\033[0m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Фоновые цвета
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"


# Эмодзи для разных событий
class Emoji:
    """Эмодзи для логирования"""
    INFO = "📘"
    SUCCESS = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    CRITICAL = "🔥"
    DEBUG = "🐛"
    STARTUP = "🚀"
    SHUTDOWN = "🛑"
    DATABASE = "🗄️"
    USER = "👤"
    PAYMENT = "💳"
    SUBSCRIPTION = "📋"
    WHITELIST = "⭐"
    CALCULATOR = "🧮"
    AGE = "📅"
    CHANNEL = "📢"
    CHAT = "💬"
    BOT = "🤖"
    TIME = "⏰"
    MESSAGE = "✉️"
    COMMAND = "⚡"
    WEBHOOK = "🌐"
    CONFLICT = "⚔️"
    TEST = "🧪"


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветами для консоли"""

    # Цвета для разных уровней логирования
    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BG_RED + Colors.WHITE,
    }

    # Эмодзи для разных уровней
    LEVEL_EMOJIS = {
        logging.DEBUG: Emoji.DEBUG,
        logging.INFO: Emoji.INFO,
        logging.WARNING: Emoji.WARNING,
        logging.ERROR: Emoji.ERROR,
        logging.CRITICAL: Emoji.CRITICAL,
    }

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Форматирование записи лога с цветами и эмодзи"""
        # Получаем время
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Получаем имя логгера (сокращаем до 20 символов)
        logger_name = record.name[:20].ljust(20)

        # Получаем уровень
        level_name = record.levelname[:8].ljust(8)
        level_emoji = self.LEVEL_EMOJIS.get(record.levelno, "📌")

        # Цвет для уровня
        color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE) if self.use_colors else ""
        reset = Colors.RESET if self.use_colors else ""

        # Формируем сообщение
        msg = record.getMessage()

        # Добавляем эмодзи в сообщение, если их нет
        if not any(emoji in msg for emoji in [Emoji.INFO, Emoji.SUCCESS, Emoji.WARNING,
                                               Emoji.ERROR, Emoji.CRITICAL, Emoji.DEBUG]):
            msg = f"{level_emoji} {msg}"

        # Формируем строку лога
        log_line = (
            f"{Colors.DIM}{timestamp}{Colors.RESET} | "
            f"{color}{level_emoji} {level_name}{reset} | "
            f"{Colors.BLUE}{logger_name}{Colors.RESET} | "
            f"{msg}"
        )

        # Добавляем место вызова если есть
        if record.filename and record.lineno:
            log_line += f" {Colors.DIM}({record.filename}:{record.lineno}){Colors.RESET}"

        return log_line


class FileFormatter(logging.Formatter):
    """Форматтер для файла (без цветов, но с эмодзи)"""

    def format(self, record: logging.LogRecord) -> str:
        """Форматирование для файла"""
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level_name = record.levelname[:8].ljust(8)
        msg = record.getMessage()

        return f"{timestamp} | {level_name} | {record.name} | {msg}"


class LoggerFilter(logging.Filter):
    """Фильтр для исключения шумных сообщений"""

    def filter(self, record: logging.LogRecord) -> bool:
        # Игнорируем слишком частые/шумные сообщения
        ignored_messages = [
            "Conflict",
            "getUpdates",
            "polling",
        ]
        msg = record.getMessage()
        for ignored in ignored_messages:
            if ignored in msg and record.levelno < logging.WARNING:
                return False
        return True


def setup_logger(
    name: str = "PianoMasterClub",
    log_dir: str = "logs",
    use_colors: bool = True,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Настройка красивого логгера.

    Args:
        name: Имя логгера
        log_dir: Директория для логов
        use_colors: Использовать цвета в консоли
        level: Уровень логирования
        log_to_file: Писать в файл
        log_to_console: Писать в консоль

    Returns:
        logging.Logger: Настроенный логгер
    """
    # Создаём логгер
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Очищаем существующие обработчики (чтобы не дублировать)
    if logger.handlers:
        logger.handlers.clear()

    # Консольный обработчик
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ColoredFormatter(use_colors))
        console_handler.addFilter(LoggerFilter())
        logger.addHandler(console_handler)

    # Файловый обработчик
    if log_to_file:
        try:
            logs_dir = Path(log_dir)
            logs_dir.mkdir(exist_ok=True)

            log_file = logs_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(FileFormatter())
            logger.addHandler(file_handler)

            print(f"✅ Логи сохраняются в: {log_file}")
        except Exception as e:
            print(f"⚠️ Не удалось создать файловый логгер: {e}")

    return logger


def get_logger(name: str = "PianoMasterClub") -> logging.Logger:
    """
    Получить настроенный логгер.

    Args:
        name: Имя логгера

    Returns:
        logging.Logger: Логгер
    """
    return logging.getLogger(name)


# Создаём и настраиваем логгер по умолчанию
logger = setup_logger()

# Декоратор для логирования функций
def log_function(logger: Optional[logging.Logger] = None):
    """
    Декоратор для логирования вызовов функций.

    Args:
        logger: Логгер для логирования

    Returns:
        Декоратор
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            _logger = logger or get_logger()
            _logger.debug(f"🚀 Вызов {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                _logger.debug(f"✅ {func.__name__} завершён успешно")
                return result
            except Exception as e:
                _logger.error(f"❌ Ошибка в {func.__name__}: {e}")
                raise

        def sync_wrapper(*args, **kwargs):
            _logger = logger or get_logger()
            _logger.debug(f"🚀 Вызов {func.__name__}")
            try:
                result = func(*args, **kwargs)
                _logger.debug(f"✅ {func.__name__} завершён успешно")
                return result
            except Exception as e:
                _logger.error(f"❌ Ошибка в {func.__name__}: {e}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Импорт asyncio для декоратора
import asyncio