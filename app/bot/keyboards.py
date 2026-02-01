from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    kb = [
        [KeyboardButton(text="🛒 Купить VPN")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def plans_keyboard(plans):
    kb = []
    for plan in plans:
        kb.append([InlineKeyboardButton(text=f"{plan.name} - {plan.price} RUB", callback_data=f"buy_plan_{plan.id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_approval_keyboard(transaction_id: int):
    kb = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve_{transaction_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{transaction_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
