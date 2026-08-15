"""
Модуль для работы с базой данных возраста фортепиано
"""

import sqlite3
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import re

logger = logging.getLogger(__name__)


class AgeDatabase:
    """Класс для работы с БД возраста фортепиано"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
        logger.info(f"AgeDatabase initialized: {db_path}")

    def _init_database(self):
        """Инициализация таблиц"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS brands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    country TEXT,
                    info TEXT,
                    type TEXT CHECK(type IN ('foreign', 'russian'))
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS serial_ranges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id INTEGER NOT NULL,
                    serial_start INTEGER NOT NULL,
                    serial_end INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_brands_name ON brands(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_serial_ranges_brand ON serial_ranges(brand_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_serial_ranges_serial ON serial_ranges(serial_start, serial_end)")
            conn.commit()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _replace_umlauts(text: str) -> str:
        """Заменяет немецкие умляуты на обычные буквы"""
        replacements = {
            'ä': 'a', 'ö': 'o', 'ü': 'u',
            'Ä': 'A', 'Ö': 'O', 'Ü': 'U',
            'ß': 'ss'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    async def add_brand(self, name: str, country: str, info: str, brand_type: str) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO brands (name, country, info, type) VALUES (?, ?, ?, ?)",
                    (name, country, info, brand_type)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT id FROM brands WHERE name = ?", (name,))
                row = cursor.fetchone()
                return row['id'] if row else None

    async def get_brand_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            clean_name = name.strip()

            # 1. Прямой поиск
            cursor = conn.execute(
                "SELECT * FROM brands WHERE LOWER(name) = LOWER(?)",
                (clean_name,)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"✅ Найден бренд: {row['name']}")
                return dict(row)

            # 2. Поиск без умляутов
            name_no_umlaut = self._replace_umlauts(clean_name)
            cursor = conn.execute(
                "SELECT * FROM brands WHERE LOWER(name) = LOWER(?)",
                (name_no_umlaut,)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"✅ Найден бренд (без умляутов): {row['name']}")
                return dict(row)

            # 3. Поиск по части названия
            cursor = conn.execute(
                "SELECT * FROM brands WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{clean_name}%",)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"✅ Найден бренд по частичному совпадению: {row['name']}")
                return dict(row)

            logger.info(f"❌ Бренд не найден: {clean_name}")
            return None

    async def search_brands(self, query: str, brand_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            clean_query = query.strip().lower()

            sql = "SELECT * FROM brands WHERE LOWER(name) LIKE LOWER(?)"
            params = [f"%{clean_query}%"]

            if brand_type:
                sql += " AND type = ?"
                params.append(brand_type)

            sql += " ORDER BY name LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]

            if not results:
                sql = "SELECT * FROM brands"
                params = []

                if brand_type:
                    sql += " WHERE type = ?"
                    params.append(brand_type)

                sql += " ORDER BY name LIMIT ?"
                params.append(limit)

                cursor = conn.execute(sql, params)
                results = [dict(row) for row in cursor.fetchall()]

            return results

    async def add_serial_range(self, brand_id: int, serial_start: int, serial_end: int, year: int) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO serial_ranges (brand_id, serial_start, serial_end, year) VALUES (?, ?, ?, ?)",
                (brand_id, serial_start, serial_end, year)
            )
            conn.commit()
            return cursor.lastrowid

    async def find_age_by_serial(self, brand_id: int, serial_number: int) -> Optional[int]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT year FROM serial_ranges 
                WHERE brand_id = ? AND serial_start <= ? AND serial_end >= ?
                ORDER BY year DESC LIMIT 1
                """,
                (brand_id, serial_number, serial_number)
            )
            row = cursor.fetchone()
            return row['year'] if row else None

    async def get_all_brands(self, brand_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            sql = "SELECT * FROM brands"
            params = []

            if brand_type:
                sql += " WHERE type = ?"
                params.append(brand_type)

            sql += " ORDER BY name"

            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    async def get_brand_count(self, brand_type: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            sql = "SELECT COUNT(*) as count FROM brands"
            params = []

            if brand_type:
                sql += " WHERE type = ?"
                params.append(brand_type)

            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            return row['count'] if row else 0

    async def get_serial_ranges(self, brand_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM serial_ranges WHERE brand_id = ? ORDER BY serial_start",
                (brand_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    async def extract_serial_number(self, text: str) -> Optional[int]:
        digits = re.sub(r'\D', '', text)
        if digits:
            return int(digits)
        return None