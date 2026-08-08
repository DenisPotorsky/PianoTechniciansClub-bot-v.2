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
        """Поиск бренда (регистронезависимый, с частичным совпадением)"""
        with self.get_connection() as conn:
            clean_name = name.strip()

            # 1. Точное совпадение
            cursor = conn.execute(
                "SELECT * FROM brands WHERE LOWER(name) = LOWER(?)",
                (clean_name,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

            # 2. Частичное совпадение (для названий с доп. данными в скобках)
            cursor = conn.execute(
                "SELECT * FROM brands WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{clean_name}%",)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

            # 3. Поиск по первому слову
            words = clean_name.split()
            if words:
                first_word = words[0]
                if len(first_word) > 2:
                    cursor = conn.execute(
                        "SELECT * FROM brands WHERE LOWER(name) LIKE LOWER(?)",
                        (f"{first_word}%",)
                    )
                    row = cursor.fetchone()
                    if row:
                        return dict(row)

            # 4. Поиск по любому слову из запроса
            for word in words:
                if len(word) > 3:
                    cursor = conn.execute(
                        "SELECT * FROM brands WHERE LOWER(name) LIKE LOWER(?)",
                        (f"%{word}%",)
                    )
                    row = cursor.fetchone()
                    if row:
                        return dict(row)

            return None

    async def search_brands(self, query: str, brand_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Поиск брендов по части названия (регистронезависимый)"""
        with self.get_connection() as conn:
            clean_query = query.strip().lower()
            results = []
            seen_names = set()

            # 1. Основной поиск
            sql = "SELECT * FROM brands WHERE LOWER(name) LIKE LOWER(?)"
            params = [f"%{clean_query}%"]

            if brand_type:
                sql += " AND type = ?"
                params.append(brand_type)

            sql += " ORDER BY name LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            for row in cursor.fetchall():
                r = dict(row)
                if r['name'] not in seen_names:
                    results.append(r)
                    seen_names.add(r['name'])

            # 2. Если мало результатов, ищем по первому слову
            if len(results) < 3 and len(clean_query.split()) > 1:
                first_word = clean_query.split()[0]
                if len(first_word) > 2:
                    sql2 = "SELECT * FROM brands WHERE LOWER(name) LIKE LOWER(?)"
                    params2 = [f"{first_word}%"]

                    if brand_type:
                        sql2 += " AND type = ?"
                        params2.append(brand_type)

                    sql2 += " ORDER BY name LIMIT ?"
                    params2.append(limit)

                    cursor2 = conn.execute(sql2, params2)
                    for row in cursor2.fetchall():
                        r = dict(row)
                        if r['name'] not in seen_names:
                            results.append(r)
                            seen_names.add(r['name'])

            return results[:limit]

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