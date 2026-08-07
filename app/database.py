import sqlite3
from typing import Optional, Any, List, Dict
from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, db_path: str):
        # Убеждаемся, что папка существует
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Инициализация всех таблиц"""
        with self.get_connection() as conn:
            # Таблица пользователей (без изменений)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица подписок — ДОБАВЛЯЕМ ПОЛЯ ДЛЯ ПРОБНОГО ПЕРИОДА
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    trial_start TIMESTAMP,
                    trial_end TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)


    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Выполнение запроса"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor

    def execute_many(self, query: str, params: List[tuple]) -> int:
        """Выполнение множества запросов"""
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params)
            conn.commit()
            return cursor.rowcount

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Получение одной записи"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Получение всех записей"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]