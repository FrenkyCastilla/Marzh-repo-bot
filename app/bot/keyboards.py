from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    kb = [
        [KeyboardButton(text="⚡️ Купить доступ")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="ℹ️ Помощь")],
        [KeyboardButton(text="🏠 Главная")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def plans_keyboard(plans):
    kb = []
    # Сортируем: сначала бесплатные
    sorted_plans = sorted(plans, key=lambda x: x.price)
    
    row = []
    for plan in sorted_plans:
        price_text = "БЕСПЛАТНО" if plan.price == 0 else f"{plan.price}₽"
        btn = InlineKeyboardButton(text=f"{plan.name} — {price_text}", callback_data=f"buy_plan_{plan.id}")
        
        row.append(btn)
        
        # Если в ряду уже 2 кнопки, добавляем ряд в клавиатуру и очищаем
        if len(row) == 2:
            kb.append(row)
            row = []
    
    # Если осталась одна кнопка в последнем ряду
    if row:
        kb.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_approval_keyboard(transaction_id: int):
    kb = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve_{transaction_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{transaction_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
