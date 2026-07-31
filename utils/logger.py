import logging
import sys
import os
from datetime import datetime
from pathlib import Path


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

    # Создаем папку для логов если её нет
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Добавляем обработчик для записи в файл
    log_file = logs_dir / f"piano_club_{datetime.now().strftime('%Y%m%d')}.log"
    try:
        file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create file handler: {e}")

    return logger