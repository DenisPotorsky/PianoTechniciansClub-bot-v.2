#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для добавления пользователей в белый список
"""

import sys
import os
import asyncio
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def add_to_whitelist():
    """Добавляет пользователя в белый список"""
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

        print("📋 Текущие пользователи в белом списке:")
        users = whitelist_service.get_all_whitelist_users()
        if users:
            for user in users:
                entry = whitelist_service.get_by_user(user)
                print(f"  • {user.display_name} - {entry.role.display_name if entry else 'Unknown'}")
        else:
            print("  ❌ Белый список пуст")

        print("\n" + "=" * 50)
        print("Добавление пользователя в белый список")
        print("=" * 50)

        # Получаем данные
        telegram_id = int(input("Введите Telegram ID пользователя: "))
        role_str = input("Введите роль (founder, expert, vip, lifetime, temporary): ").lower()
        reason = input("Введите причину добавления: ")

        # Проверяем роль
        try:
            role = WhitelistRole(role_str)
        except ValueError:
            available = ", ".join([r.value for r in WhitelistRole])
            print(f"❌ Неизвестная роль. Доступные: {available}")
            return

        # Получаем или создаем пользователя
        user = user_service.get_or_create(
            telegram_id=telegram_id,
            username=None,
            first_name=f"User_{telegram_id}",
            last_name=None
        )

        # Добавляем в белый список (добавляем от имени самого пользователя)
        days = 30 if role == WhitelistRole.TEMPORARY else None
        entry = whitelist_service.add_to_whitelist(
            user=user,
            role=role,
            reason=reason,
            added_by=user,  # Добавляем от себя
            days=days
        )

        print(f"\n✅ Пользователь {user.display_name} добавлен в белый список!")
        print(f"   Роль: {role.display_name}")
        print(f"   Причина: {reason}")
        if days:
            print(f"   Действует до: {entry.expires_at.strftime('%d.%m.%Y %H:%M')}")

        print("\n📋 Обновленный список:")
        users = whitelist_service.get_all_whitelist_users()
        for user in users:
            entry = whitelist_service.get_by_user(user)
            print(f"  • {user.display_name} - {entry.role.display_name if entry else 'Unknown'}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_to_whitelist())