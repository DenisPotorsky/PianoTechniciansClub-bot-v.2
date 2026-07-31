#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Инициализация белого списка - добавляет всех администраторов
"""

import sys
import os
import asyncio
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def init_whitelist():
    """Инициализация белого списка администраторами"""
    try:
        from app.config import config
        from app.database import Database
        from models.whitelist import WhitelistRole
        from repositories.user_repository import UserRepository
        from repositories.whitelist_repository import WhitelistRepository
        from services.user_service import UserService
        from services.whitelist_service import WhitelistService

        print("🔄 Инициализация базы данных...")
        db = Database(config.db_path)

        user_repo = UserRepository(db)
        whitelist_repo = WhitelistRepository(db)
        user_service = UserService(user_repo)
        whitelist_service = WhitelistService(whitelist_repo, user_repo)

        print(f"👑 Добавление администраторов в белый список...")
        print(f"Администраторы: {config.ADMIN_IDS}")

        for admin_id in config.ADMIN_IDS:
            # Получаем или создаем пользователя
            user = user_service.get_or_create(
                telegram_id=admin_id,
                username=None,
                first_name=f"Admin_{admin_id}",
                last_name=None
            )

            # Проверяем, есть ли уже в белом списке
            if whitelist_service.is_in_whitelist(user):
                role = whitelist_service.get_user_role(user)
                print(f"  ⚠️ Пользователь {user.telegram_id} уже в белом списке (роль: {role.display_name})")
                continue

            # Добавляем в белый список
            entry = whitelist_service.add_to_whitelist(
                user=user,
                role=WhitelistRole.FOUNDER,
                reason="Администратор клуба",
                added_by=user,
                days=None  # Бессрочно
            )

            print(f"  ✅ {user.telegram_id} добавлен как {WhitelistRole.FOUNDER.display_name}")

        print("\n📋 Текущий белый список:")
        users = whitelist_service.get_all_whitelist_users()
        if users:
            for user in users:
                entry = whitelist_service.get_by_user(user)
                print(f"  • {user.telegram_id} - {entry.role.display_name if entry else 'Unknown'}")
        else:
            print("  ❌ Белый список пуст")

        print("\n✅ Инициализация завершена!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(init_whitelist())