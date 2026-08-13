#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import asyncio
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def cleanup():
    """Очистка перед запуском"""
    try:
        from app.config import config
        from telegram import Bot

        if config.BOT_TOKEN:
            bot = Bot(token=config.BOT_TOKEN)
            await bot.delete_webhook()
            print("✅ Webhook deleted")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


def main():
    """Запуск бота"""
    try:
        print("🚀 ЗАПУСК БОТА...")
        print(f"📁 Директория: {project_root}")

        asyncio.run(cleanup())

        from app.main import main as bot_main
        asyncio.run(bot_main())

    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()