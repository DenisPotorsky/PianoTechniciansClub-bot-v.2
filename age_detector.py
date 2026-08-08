"""
Модуль для определения возраста фортепиано
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgeResult:
    """Результат определения возраста"""
    brand_name: str
    brand_country: str
    serial_number: int
    year: Optional[int]
    found: bool
    message: str
    brand_info: Optional[str] = None
    brand_type: Optional[str] = None
    similar_brands: Optional[List[str]] = None


class AgeDetector:
    """Класс для определения возраста фортепиано по бренду и серийному номеру"""

    def __init__(self, database):
        """
        Инициализация детектора

        Args:
            database: Экземпляр AgeDatabase
        """
        self.db = database
        logger.info("AgeDetector initialized")

    async def detect(self, brand_name: str, serial_number: str, brand_type: str = None) -> AgeResult:
        """
        Определение возраста фортепиано (регистронезависимый поиск)

        Args:
            brand_name: Название бренда
            serial_number: Серийный номер (строка)
            brand_type: 'foreign' или 'russian' (опционально)

        Returns:
            AgeResult с результатами поиска
        """
        # Извлекаем цифры из серийного номера
        serial_int = await self.db.extract_serial_number(serial_number)
        if serial_int is None:
            return AgeResult(
                brand_name=brand_name,
                brand_country="",
                serial_number=0,
                year=None,
                found=False,
                message="❌ Не удалось распознать серийный номер. Введите только цифры."
            )

        # Ищем бренд (регистронезависимый поиск)
        brand = await self.db.get_brand_by_name(brand_name)

        # Если бренд не найден, ищем похожие (регистронезависимый поиск)
        if not brand:
            similar = await self.db.search_brands(brand_name, brand_type, limit=10)
            similar_names = [b['name'] for b in similar]

            if similar_names:
                return AgeResult(
                    brand_name=brand_name,
                    brand_country="",
                    serial_number=serial_int,
                    year=None,
                    found=False,
                    message=f"❌ Бренд '{brand_name}' не найден.\n\nВозможно, вы имели в виду:\n" + "\n".join(f"• {name}" for name in similar_names[:10]),
                    similar_brands=similar_names
                )
            else:
                # Показываем все доступные бренды
                all_brands = await self.db.get_all_brands(brand_type)
                if all_brands:
                    brands_list = "\n".join(f"• {b['name']}" for b in all_brands[:10])
                    return AgeResult(
                        brand_name=brand_name,
                        brand_country="",
                        serial_number=serial_int,
                        year=None,
                        found=False,
                        message=f"❌ Бренд '{brand_name}' не найден.\n\nДоступные бренды:\n{brands_list}\n\nВведите точное название бренда."
                    )
                else:
                    return AgeResult(
                        brand_name=brand_name,
                        brand_country="",
                        serial_number=serial_int,
                        year=None,
                        found=False,
                        message="❌ Бренд не найден. В базе данных пока нет брендов."
                    )

        # Ищем год по серийному номеру
        year = await self.db.find_age_by_serial(brand['id'], serial_int)

        if year:
            return AgeResult(
                brand_name=brand['name'],
                brand_country=brand.get('country', ''),
                serial_number=serial_int,
                year=year,
                found=True,
                message=f"✅ {brand['name']} ({brand.get('country', '')}) — год выпуска: {year}",
                brand_info=brand.get('info', ''),
                brand_type=brand.get('type', '')
            )
        else:
            # Проверяем, есть ли вообще диапазоны для этого бренда
            ranges = await self.db.get_serial_ranges(brand['id'])
            if not ranges:
                return AgeResult(
                    brand_name=brand['name'],
                    brand_country=brand.get('country', ''),
                    serial_number=serial_int,
                    year=None,
                    found=False,
                    message=f"⚠️ Для бренда '{brand['name']}' пока нет данных по серийным номерам.\n\nПожалуйста, обратитесь к администратору для добавления информации.",
                    brand_info=brand.get('info', ''),
                    brand_type=brand.get('type', '')
                )
            else:
                # Показываем доступные диапазоны
                ranges_text = "\n".join(
                    f"• {r['serial_start']} - {r['serial_end']} → {r['year']} г."
                    for r in ranges[:5]
                )
                return AgeResult(
                    brand_name=brand['name'],
                    brand_country=brand.get('country', ''),
                    serial_number=serial_int,
                    year=None,
                    found=False,
                    message=f"⚠️ Серийный номер {serial_int} не найден для бренда '{brand['name']}'.\n\nДоступные диапазоны:\n{ranges_text}\n\nПроверьте правильность серийного номера.",
                    brand_info=brand.get('info', ''),
                    brand_type=brand.get('type', '')
                )