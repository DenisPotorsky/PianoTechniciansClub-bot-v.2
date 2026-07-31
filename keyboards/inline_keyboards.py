from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict
from app.config import config


def get_main_keyboard(has_access: bool, access_type: str = "") -> InlineKeyboardMarkup:
    """Создает главную клавиатуру в зависимости от доступа"""
    keyboard: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton("📖 О проекте", callback_data="about")]
    ]

    if has_access:
        # Доступ открыт - добавляем кнопки канала и чата
        keyboard.extend([
            [
                InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
                InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
            ],
            [InlineKeyboardButton("🔧 Калькулятор струн", callback_data="calculator")],
            [InlineKeyboardButton("🔄 Статус доступа", callback_data="status")]
        ])

        # Если есть права администратора, добавляем админ-кнопку
        if access_type.startswith("whitelist_"):
            role = access_type.replace("whitelist_", "")
            if role in ["founder", "expert"]:
                keyboard.append(
                    [InlineKeyboardButton("👑 Управление", callback_data="admin_menu")]
                )
    else:
        # Доступ закрыт
        keyboard.append([InlineKeyboardButton("🎹 Присоединиться", callback_data="subscribe")])

    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data="help")])

    return InlineKeyboardMarkup(keyboard)


def get_subscription_success_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после успешной подписки"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
            InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
        ],
        [InlineKeyboardButton("🔧 Калькулятор", callback_data="calculator")],
        [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
    ])