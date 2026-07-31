import math
from typing import Dict, Any


class CalculatorService:
    """Сервис для расчета басовых струн"""

    @staticmethod
    def cooper_diam(general: float, kern: float) -> float:
        """Вычисление диаметра меди для одиночной струны"""
        return round((general - kern) / 2, 3)

    @staticmethod
    def length_cooper(kern: float, cooper: float, length: int) -> int:
        """Вычисление длины меди для одиночной струны"""
        return int((kern + cooper * 2) * math.pi * length)

    @staticmethod
    def cooper_first(general: float, kern: float) -> float:
        """Вычисление диаметра меди для первичной навивки"""
        return round(((general - kern) * 0.3334) / 2, 3)

    @staticmethod
    def cooper_second(general: float, kern: float) -> float:
        """Вычисление диаметра меди для вторичной навивки"""
        return round(((general - kern) * 0.6667) / 2, 3)

    @staticmethod
    def length_cooper_primary(kern: float, length: int, cooper_first: float) -> int:
        """Вычисление длины меди для первичной навивки"""
        return int((kern + cooper_first * 2) * math.pi * length - 50)

    @staticmethod
    def length_cooper_secondary(kern: float, length: int, cooper_first: float,
                                cooper_second: float) -> int:
        """Вычисление длины меди для вторичной навивки"""
        return int(((kern + (cooper_first * 2)) + (cooper_second * 2)) * math.pi * length)

    def calculate(self, type_of_string: int, kern: float, length: int,
                  diam_general: float) -> Dict[str, Any]:
        """
        Основной метод расчета струн

        Args:
            type_of_string: 1 - одиночная, 2 - двойная
            kern: диаметр керна
            length: длина струны
            diam_general: общий диаметр

        Returns:
            Dict с результатами расчета
        """
        if type_of_string == 1:
            cooper = self.cooper_diam(diam_general, kern)
            length_cooper = self.length_cooper(kern, cooper, length)
            return {
                'type': 'single',
                'diam_primary': cooper,
                'diam_secondary': None,
                'length_primary': length_cooper,
                'length_secondary': None,
                'total_length': length_cooper
            }
        else:
            cooper_first = self.cooper_first(diam_general, kern)
            cooper_second = self.cooper_second(diam_general, kern)
            length_primary = self.length_cooper_primary(kern, length, cooper_first)
            length_secondary = self.length_cooper_secondary(
                kern, length, cooper_first, cooper_second
            )
            return {
                'type': 'double',
                'diam_primary': cooper_first,
                'diam_secondary': cooper_second,
                'length_primary': length_primary,
                'length_secondary': length_secondary,
                'total_length': length_primary + length_secondary
            }

    def format_result(self, result: Dict[str, Any]) -> str:
        """Форматирование результата для вывода"""
        if result['type'] == 'single':
            return (
                f"📊 **Результат расчета (одинарная навивка)**\n\n"
                f"Диаметр меди: {result['diam_primary']} мм\n"
                f"Длина меди: {result['length_primary']} мм\n"
                f"Общая длина: {result['total_length']} мм"
            )
        else:
            return (
                f"📊 **Результат расчета (двойная навивка)**\n\n"
                f"Диаметр первичной меди: {result['diam_primary']} мм\n"
                f"Диаметр вторичной меди: {result['diam_secondary']} мм\n"
                f"Длина первичной меди: {result['length_primary']} мм\n"
                f"Длина вторичной меди: {result['length_secondary']} мм\n"
                f"Общая длина: {result['total_length']} мм"
            )