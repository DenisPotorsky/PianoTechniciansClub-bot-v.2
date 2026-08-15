"""
Модуль для работы с базой данных возраста фортепиано
(с поддержкой умляутов через Unidecode)
"""

import sqlite3
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import re
from unidecode import unidecode

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
    def normalize_text(text: str) -> str:
        """Нормализует текст: убирает умляуты и приводит к нижнему регистру"""
        if not text:
            return text
        # unidecode превращает Förster → Forster, Bösendorfer → Bosendorfer
        return unidecode(text).lower()

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
        """
        Поиск бренда по названию (с поддержкой умляутов через unidecode)
        """
        with self.get_connection() as conn:
            clean_name = name.strip()
            normalized_input = self.normalize_text(clean_name)

            # Получаем все бренды
            cursor = conn.execute("SELECT * FROM brands")
            all_brands = cursor.fetchall()

            for row in all_brands:
                brand_dict = dict(row)
                brand_name = brand_dict['name']
                normalized_brand = self.normalize_text(brand_name)

                # Сравниваем нормализованные строки
                if normalized_brand == normalized_input:
                    logger.info(f"✅ Найден бренд: {brand_name}")
                    return brand_dict

            # Если не нашли — пробуем частичное совпадение
            for row in all_brands:
                brand_dict = dict(row)
                brand_name = brand_dict['name']
                normalized_brand = self.normalize_text(brand_name)

                if normalized_input in normalized_brand:
                    logger.info(f"✅ Найден бренд по частичному совпадению: {brand_name}")
                    return brand_dict

            logger.info(f"❌ Бренд не найден: {clean_name}")
            return None

    async def search_brands(self, query: str, brand_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Поиск брендов по части названия (с поддержкой умляутов через unidecode)
        """
        with self.get_connection() as conn:
            clean_query = query.strip().lower()
            normalized_query = self.normalize_text(clean_query)

            # Получаем все бренды
            if brand_type:
                cursor = conn.execute("SELECT * FROM brands WHERE type = ?", (brand_type,))
            else:
                cursor = conn.execute("SELECT * FROM brands")

            all_brands = cursor.fetchall()
            results = []
            seen_names = set()

            for row in all_brands:
                brand_dict = dict(row)
                brand_name = brand_dict['name']
                normalized_brand = self.normalize_text(brand_name)

                # Проверяем совпадение
                if normalized_query in normalized_brand:
                    if brand_name not in seen_names:
                        results.append(brand_dict)
                        seen_names.add(brand_name)

            # Сортируем по названию и ограничиваем
            results.sort(key=lambda x: x['name'])

            if not results:
                # Если ничего не нашли — показываем все бренды
                if brand_type:
                    cursor = conn.execute("SELECT * FROM brands WHERE type = ? ORDER BY name LIMIT ?", (brand_type, limit))
                else:
                    cursor = conn.execute("SELECT * FROM brands ORDER BY name LIMIT ?", (limit,))
                results = [dict(row) for row in cursor.fetchall()]

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
            if brand_type:
                cursor = conn.execute("SELECT * FROM brands WHERE type = ? ORDER BY name", (brand_type,))
            else:
                cursor = conn.execute("SELECT * FROM brands ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    async def get_brand_count(self, brand_type: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            if brand_type:
                cursor = conn.execute("SELECT COUNT(*) as count FROM brands WHERE type = ?", (brand_type,))
            else:
                cursor = conn.execute("SELECT COUNT(*) as count FROM brands")
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