"""
Скрипт для удаления всех отечественных брендов из базы данных
"""

import sqlite3


def delete_russian_brands():
    """Удаляет все отечественные бренды и их диапазоны"""

    print("=" * 50)
    print("🗑️ УДАЛЕНИЕ ОТЕЧЕСТВЕННЫХ БРЕНДОВ")
    print("=" * 50)

    # Подключаемся к базе
    conn = sqlite3.connect("piano_age.db")
    cursor = conn.cursor()

    # Считаем, сколько есть отечественных брендов
    cursor.execute("SELECT COUNT(*) FROM brands WHERE type = 'russian'")
    count = cursor.fetchone()[0]

    print(f"\n📊 Найдено отечественных брендов: {count}")

    if count == 0:
        print("ℹ️ В базе нет отечественных брендов. Ничего не нужно удалять.")
        conn.close()
        return

    # Показываем список того, что будет удалено
    print("\n📋 Список отечественных брендов:")
    cursor.execute("SELECT id, name, country FROM brands WHERE type = 'russian' ORDER BY name")
    for row in cursor.fetchall():
        print(f"  • {row[1]} ({row[2]}) — ID: {row[0]}")

    # Запрашиваем подтверждение
    print("\n⚠️ ВНИМАНИЕ: Будут удалены ВСЕ отечественные бренды и их диапазоны!")
    response = input("Продолжить? (y/n): ")

    if response.lower() != 'y':
        print("❌ Операция отменена")
        conn.close()
        return

    # Удаляем диапазоны отечественных брендов
    cursor.execute("""
        DELETE FROM serial_ranges 
        WHERE brand_id IN (SELECT id FROM brands WHERE type = 'russian')
    """)
    deleted_ranges = cursor.rowcount
    print(f"\n🗑️ Удалено диапазонов: {deleted_ranges}")

    # Удаляем отечественные бренды
    cursor.execute("DELETE FROM brands WHERE type = 'russian'")
    deleted_brands = cursor.rowcount
    print(f"🗑️ Удалено брендов: {deleted_brands}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 50)
    print(f"✅ Удалено {deleted_brands} брендов и {deleted_ranges} диапазонов")
    print("=" * 50)


if __name__ == "__main__":
    delete_russian_brands()