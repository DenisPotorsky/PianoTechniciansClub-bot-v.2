"""
Модуль с клавиатурами для бота
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict
from app.config import config


def get_main_keyboard(has_access: bool, access_type: str = "") -> InlineKeyboardMarkup:
    """
    Создаёт главную клавиатуру в зависимости от доступа пользователя.

    Args:
        has_access: Есть ли доступ к функциям клуба
        access_type: Тип доступа (subscription, whitelist_founder и т.д.)

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками
    """
    keyboard: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton("📖 О проекте", callback_data="about")]
    ]

    if has_access:
        # Доступ открыт — показываем все функции
        keyboard.extend([
            [
                InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
                InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
            ],
            [InlineKeyboardButton("🧮 Калькулятор струн", callback_data="calculator")],
            [InlineKeyboardButton("📅 Возраст фортепиано", callback_data="age")],
            [InlineKeyboardButton("🔄 Статус доступа", callback_data="status")]
        ])

        # Если пользователь в белом списке с правами админа — добавляем админ-кнопку
        if access_type.startswith("whitelist_"):
            role = access_type.replace("whitelist_", "")
            if role in ["founder", "expert"]:
                keyboard.append(
                    [InlineKeyboardButton("👑 Управление", callback_data="admin_menu")]
                )
    else:
        # Доступ закрыт — только кнопка подписки
        keyboard.append([InlineKeyboardButton("🎹 Присоединиться", callback_data="subscribe")])

    # Кнопка помощи всегда внизу
    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data="help")])

    return InlineKeyboardMarkup(keyboard)


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для оформления подписки.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой подписки
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎹 Оформить подписку", callback_data="subscribe")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu")]
    ])


def get_subscription_success_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура после успешной оплаты подписки.

    Returns:
        InlineKeyboardMarkup: Клавиатура со ссылками на канал и чат
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Канал", url=config.CHANNEL_URL),
            InlineKeyboardButton("💬 Чат", url=config.CHAT_URL)
        ],
        [InlineKeyboardButton("🧮 Калькулятор", callback_data="calculator")],
        [InlineKeyboardButton("📅 Возраст фортепиано", callback_data="age")],
        [InlineKeyboardButton("◀️ Меню", callback_data="menu")]
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой отмены.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой отмены
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Отмена", callback_data="cancel")]
    ])


def get_back_keyboard(callback_data: str = "menu") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопкой "Назад".

    Args:
        callback_data: Данные для callback-запроса

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой назад
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=callback_data)]
    ])