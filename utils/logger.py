import logging
import sys
from datetime import datetime


def setup_logger(name: str = "PianoMasterClub") -> logging.Logger:
    """Настройка логгера"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Добавляем обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Добавляем обработчик для записи в файл
    file_handler = logging.FileHandler(
        f"logs/piano_club_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger