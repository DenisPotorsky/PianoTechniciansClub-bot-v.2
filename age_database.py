"""
Модуль для работы с базой данных возраста фортепиано
"""

import sqlite3
import logging
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from contextlib import contextmanager
import re

logger = logging.getLogger(__name__)


class AgeDatabase:
    """Класс для работы с БД возраста фортепиано"""

    def __init__(self, db_path: str):
        """
        Инициализация базы данных

        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self._init_database()
        logger.info(f"AgeDatabase initialized: {db_path}")

    def _init_database(self):
        """Инициализация таблиц, если их нет"""
        with self.get_connection() as conn:
            # Таблица брендов
            conn.execute("""
                CREATE TABLE IF NOT EXISTS brands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    country TEXT,
                    info TEXT,
                    type TEXT CHECK(type IN ('foreign', 'russian'))
                )
            """)

            # Таблица диапазонов серийных номеров
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

            # Индексы для ускорения поиска
            conn.execute("CREATE INDEX IF NOT EXISTS idx_brands_name ON brands(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_brands_name_lower ON brands(LOWER(name))")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_serial_ranges_brand ON serial_ranges(brand_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_serial_ranges_serial ON serial_ranges(serial_start, serial_end)")

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

    async def add_brand(self, name: str, country: str, info: str, brand_type: str) -> int:
        """
        Добавление бренда в базу данных

        Args:
            name: Название бренда
            country: Страна происхождения
            info: Дополнительная информация
            brand_type: 'foreign' или 'russian'

        Returns:
            ID добавленного бренда
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO brands (name, country, info, type) VALUES (?, ?, ?, ?)",
                    (name, country, info, brand_type)
                )
                conn.commit()
                brand_id = cursor.lastrowid
                logger.info(f"Brand added: {name} (ID: {brand_id})")
                return brand_id
        except sqlite3.IntegrityError:
            logger.warning(f"Brand already exists: {name}")
            # Возвращаем ID существующего бренда
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT id FROM brands WHERE name = ?", (name,))
                row = cursor.fetchone()
                return row['id'] if row else None

    async def get_brand_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Поиск бренда по названию (регистронезависимый)

        Args:
            name: Название бренда

        Returns:
            Словарь с данными бренда или None
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM brands WHERE LOWER(name) = LOWER(?)",
                (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    async def search_brands(self, query: str, brand_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Поиск брендов по части названия (регистронезависимый)

        Args:
            query: Строка поиска
            brand_type: 'foreign' или 'russian' (опционально)
            limit: Максимальное количество результатов

        Returns:
            Список словарей с данными брендов
        """
        with self.get_connection() as conn:
            # Приводим запрос к нижнему регистру
            query_lower = query.lower()

            sql = "SELECT * FROM brands WHERE LOWER(name) LIKE LOWER(?)"
            params = [f"%{query_lower}%"]

            if brand_type:
                sql += " AND type = ?"
                params.append(brand_type)

            sql += " ORDER BY name LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    async def add_serial_range(self, brand_id: int, serial_start: int, serial_end: int, year: int) -> int:
        """
        Добавление диапазона серийных номеров

        Args:
            brand_id: ID бренда
            serial_start: Начало диапазона
            serial_end: Конец диапазона
            year: Год выпуска

        Returns:
            ID добавленной записи
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO serial_ranges (brand_id, serial_start, serial_end, year) VALUES (?, ?, ?, ?)",
                (brand_id, serial_start, serial_end, year)
            )
            conn.commit()
            range_id = cursor.lastrowid
            logger.info(f"Serial range added: brand_id={brand_id}, range={serial_start}-{serial_end}, year={year}")
            return range_id

    async def find_age_by_serial(self, brand_id: int, serial_number: int) -> Optional[int]:
        """
        Поиск года по серийному номеру

        Args:
            brand_id: ID бренда
            serial_number: Серийный номер

        Returns:
            Год выпуска или None
        """
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
        """
        Получение всех брендов

        Args:
            brand_type: 'foreign' или 'russian' (опционально)

        Returns:
            Список словарей с данными брендов
        """
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
        """
        Получение количества брендов

        Args:
            brand_type: 'foreign' или 'russian' (опционально)

        Returns:
            Количество брендов
        """
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
        """
        Получение всех диапазонов для бренда

        Args:
            brand_id: ID бренда

        Returns:
            Список диапазонов
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM serial_ranges WHERE brand_id = ? ORDER BY serial_start",
                (brand_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    async def extract_serial_number(self, text: str) -> Optional[int]:
        """
        Извлечение цифр из строки для получения серийного номера

        Args:
            text: Строка с серийным номером

        Returns:
            Числовой серийный номер или None
        """
        digits = re.sub(r'\D', '', text)
        if digits:
            return int(digits)
        return None