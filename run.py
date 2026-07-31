#!/usr/bin/env python
"""
Точка входа для запуска бота
"""

import sys
import os
import asyncio

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import main

if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(main())