"""
Модуль для работы с базой данных
"""

import sqlite3
from typing import Optional, List, Dict
from contextlib import contextmanager
from datetime import datetime
from utils.logger import logger


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
        logger.info(f"Database initialized at: {db_path}")

    def _init_database(self):
        """Инициализация всех таблиц"""
        with self.get_connection() as conn:
            # Таблица пользователей
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

            # Таблица подписок
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

            # Таблица платежей
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    payment_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Таблица белого списка
            conn.execute("""
                CREATE TABLE IF NOT EXISTS whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    reason TEXT,
                    added_by INTEGER NOT NULL,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Индексы
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_whitelist_user ON whitelist(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_whitelist_active ON whitelist(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)")

            # Проверяем наличие колонок для пробного периода
            cursor = conn.execute("PRAGMA table_info(subscriptions)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'trial_start' not in columns:
                conn.execute("ALTER TABLE subscriptions ADD COLUMN trial_start TIMESTAMP")
                logger.info("✅ Добавлена колонка trial_start")

            if 'trial_end' not in columns:
                conn.execute("ALTER TABLE subscriptions ADD COLUMN trial_end TIMESTAMP")
                logger.info("✅ Добавлена колонка trial_end")

            conn.commit()

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
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor

    def execute_many(self, query: str, params: List[tuple]) -> int:
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params)
            conn.commit()
            return cursor.rowcount

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]