from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import time

# Импорты твоих модулей
from ..core.models import User, Plan, Subscription, Transaction
from ..core.config import settings
from .keyboards import main_menu, plans_keyboard, admin_approval_keyboard
from ..services.payment_service import process_new_payment, approve_payment, reject_payment
from ..services.marzban_api import MarzbanAPI

router = Router()
api = MarzbanAPI() # Инициализируем API для работы с панелью

# --- КОНСТАНТЫ И ТЕКСТЫ ---

INSTRUCTION_TEXT = (
    "<b>🚀 Настройка подключения</b>\n\n"
    "1. Скачайте приложение:\n"
    "📱 <b>Android:</b> <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>v2rayNG</a>\n"
    "🍏 <b>iOS:</b> <a href='https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690'>V2Box</a>\n"
    "💻 <b>PC:</b> <a href='https://github.com/hiddify/hiddify-next/releases'>Hiddify Next</a>\n\n"
    "2. Скопируйте выданный ключ (начинается с <code>vless://</code>).\n"
    "3. Откройте приложение — оно предложит добавить ключ из буфера.\n"
    "4. Нажмите кнопку подключения (Connect)."
)

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def calculate_new_expire(username: str, days_to_add: int) -> int:
    """Суммирует дни подписки или создает новую дату."""
    user_info = await api.get_user(username)
    current_timestamp = int(time.time())
    seconds_to_add = days_to_add * 24 * 60 * 60

    if not user_info or not user_info.get("expire"):
        return current_timestamp + seconds_to_add

    old_expire = user_info.get("expire")
    
    # Если подписка активна -> добавляем к старой дате
    if old_expire > current_timestamp:
        return old_expire + seconds_to_add
    else:
        return current_timestamp + seconds_to_add

# --- ХЕНДЛЕРЫ ---

@router.message(Command("start"))
async def cmd_start(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    user_query = await session.execute(select(User).where(User.telegram_id == user_id))
    user = user_query.scalar_one_or_none()
    
    if not user:
        user = User(
            telegram_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        session.add(user)
        await session.commit()
    
    welcome_text = (
        f"Привет, <b>{message.from_user.first_name}</b>! 👋\n\n"
        "Я бот для выдачи скоростного доступа в сеть.\n"
        "Youtube 4K, Instagram, Игры — без ограничений скорости.\n\n"
        "🔐 Трафик шифруется. Логи не ведутся.\n"
        "Жми <b>«⚡️ Купить доступ»</b>, чтобы начать."
    )
    
    await message.answer(welcome_text, reply_markup=main_menu(), parse_mode="HTML")

@router.message(F.text == "ℹ️ Помощь")
async def help_command(message: types.Message):
    await message.answer(INSTRUCTION_TEXT, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text == "⚡️ Купить доступ")
async def shop_menu(message: types.Message, session: AsyncSession):
    plans_query = await session.execute(select(Plan).where(Plan.is_active == True))
    plans = plans_query.scalars().all()
    
    if not plans:
        await message.answer("К сожалению, сейчас нет доступных тарифов.")
        return
        
    await message.answer("Выберите подходящий тариф:", reply_markup=plans_keyboard(plans))

@router.callback_query(F.data.startswith("buy_plan_"))
async def process_buy_plan(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    plan_id = int(callback.data.split("_")[-1])
    plan_query = await session.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_query.scalar_one_or_none()
    
    if not plan:
        await callback.answer("Тариф не найден.")
        return

    # --- ЛОГИКА БЕСПЛАТНОГО ТЕСТА (0 РУБЛЕЙ) ---
    if plan.price == 0:
        await callback.answer("Активируем тестовый доступ...", show_alert=False)
        
        # 1. Считаем дату (суммируем или с нуля)
        expire_date = await calculate_new_expire(callback.from_user.username, plan.duration)
        
        # 2. Создаем в Marzban
        user_data = await api.create_user(
            username=callback.from_user.username,
            data_limit=plan.limit_gb,
            expire=expire_date
        )
        
        if user_data:
            sub_url = user_data.get('subscription_url', '')
            
            # 3. Отправляем Ключ
            await callback.message.answer(
                f"🎁 <b>Тестовый доступ активирован!</b>\n\n"
                f"Действует до: <code>{datetime.fromtimestamp(expire_date).strftime('%d.%m.%Y %H:%M')}</code>\n\n"
                f"<b>🔗 Твой ключ доступа (нажми, чтобы скопировать):</b>\n"
                f"<code>{sub_url}</code>",
                parse_mode="HTML"
            )
            
            # 4. Отправляем Инструкцию
            await callback.message.answer(INSTRUCTION_TEXT, parse_mode="HTML", disable_web_page_preview=True)
        else:
            await callback.message.answer("⚠️ Ошибка выдачи теста. Обратитесь к администратору.")
        
        return # Выходим, оплата не нужна

    # --- ЛОГИКА ОБЫЧНОЙ ПОКУПКИ (ПЛАТНО) ---
    await state.update_data(plan_id=plan_id, amount=plan.price)
    await state.set_state(PaymentStates.waiting_for_receipt)
    
    await callback.message.answer(
        f"💳 Вы выбрали: {plan.name}\n"
        f"💰 К оплате: {plan.price} RUB\n\n"
        f"{settings.PAYMENT_INFO}\n\n"
        "После пере
