from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.core.config import settings

def get_main_menu():
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Купить VPN / Тест", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton(text="💬 Поддержка", url=f"tg://user?id={settings.ADMIN_ID}")]
    ])
    return keyboard

def get_plans_keyboard(plans):
    """Список тарифов + Кнопка Назад"""
    buttons = []
    # Сортируем: сначала бесплатные, потом дешевые
    sorted_plans = sorted(plans, key=lambda x: x.price)

    for plan in sorted_plans:
        # Красивое отображение: "1 Месяц - 100 RUB" или "Тест - БЕСПЛАТНО"
        price_text = "БЕСПЛАТНО" if plan.price == 0 else f"{plan.price} RUB"
        btn_text = f"{plan.name} — {price_text}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"plan_{plan.id}")])

    # Кнопка НАЗАД
    buttons.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_support_keyboard():
    """Меню оплаты + Отмена"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил (Отправить чек)", callback_data="check_payment")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="main_menu")]
    ])
    return keyboard

def get_profile_keyboard():
    """Меню профиля с кнопкой Продлить"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
    ])
    return keyboard

def get_admin_transaction_keyboard(tx_id):
    """Админка"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_approve_{tx_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_decline_{tx_id}")
        ]
    ])
    return keyboard
