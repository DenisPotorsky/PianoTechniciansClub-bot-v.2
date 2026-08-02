from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict
from app.config import config


def get_main_keyboard(has_access: bool, access_type: str = "") -> InlineKeyboardMarkup:
    """Создает главную клавиатуру"""
    keyboard: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton("📖 Зачем всё это", callback_data="about")]
    ]

    if has_access:
        keyboard.extend([
            [
                InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
                InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
            ],
            [InlineKeyboardButton("🧮 Калькулятор для изготовления басовых струн", callback_data="calculator")],
            [InlineKeyboardButton("🔄 Статус доступа", callback_data="status")]
        ])

        if access_type.startswith("whitelist_"):
            role = access_type.replace("whitelist_", "")
            if role in ["founder", "expert"]:
                keyboard.append(
                    [InlineKeyboardButton("👑 Админка", callback_data="admin_menu")]
                )
    else:
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
        [InlineKeyboardButton("🧮 Калькулятор", callback_data="calculator")],
        [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
    ])