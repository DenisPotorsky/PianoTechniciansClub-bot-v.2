#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import asyncio
import time
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def force_cleanup():
    """Максимально агрессивная очистка"""
    try:
        from app.config import config
        from telegram import Bot

        print("🔥 ПРИНУДИТЕЛЬНАЯ ОЧИСТКА...")

        if config.BOT_TOKEN:
            bot = Bot(token=config.BOT_TOKEN)

            # 1. Удаляем вебхук (несколько раз)
            for i in range(3):
                try:
                    await bot.delete_webhook()
                    print(f"✅ Вебхук удалён (попытка {i + 1})")
                except Exception as e:
                    print(f"⚠️ Попытка {i + 1}: {e}")
                await asyncio.sleep(1)

            # 2. Проверяем статус
            info = await bot.get_webhook_info()
            print(f"✅ Статус вебхука: {info.url if info.url else 'Нет вебхука'}")

            # 3. Получаем информацию о боте
            me = await bot.get_me()
            print(f"✅ Бот: @{me.username}")

            # 4. Отправляем тестовое сообщение (если есть админ)
            if config.ADMIN_IDS:
                try:
                    await bot.send_message(
                        chat_id=config.ADMIN_IDS[0],
                        text="🔄 Бот перезапускается..."
                    )
                    print("✅ Тестовое сообщение отправлено")
                except Exception as e:
                    print(f"⚠️ Не удалось отправить сообщение: {e}")

    except Exception as e:
        print(f"❌ Ошибка очистки: {e}")


def main():
    """Запуск бота"""
    try:
        print("🚀 ЗАПУСК БОТА...")
        print(f"📁 Директория: {project_root}")

        # Очистка
        asyncio.run(force_cleanup())

        # Ждём 5 секунд
        print("⏳ Ожидание 5 секунд...")
        time.sleep(5)

        # Запускаем бота
        from app.main import main as bot_main
        asyncio.run(bot_main())

    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
# опять коммент 1