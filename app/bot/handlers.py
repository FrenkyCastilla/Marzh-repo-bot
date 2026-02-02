import logging
import time
from datetime import datetime

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Импорты
from ..core.models import User, Plan, Subscription, Transaction
from ..core.config import settings
from .keyboards import main_menu, plans_keyboard, admin_approval_keyboard
from ..services.marzban_api import MarzbanAPI

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()
api = MarzbanAPI()

# --- ТЕКСТЫ ---
INSTRUCTION_TEXT = (
    "<b>🚀 Настройка подключения:</b>\n\n"
    "1. Скачай приложение:\n"
    "📱 <b>Android:</b> <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>v2rayNG (Google Play)</a>\n"
    "🍏 <b>iOS:</b> <a href='https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690'>V2Box (AppStore)</a>\n"
    "💻 <b>PC (Windows):</b> <a href='https://github.com/hiddify/hiddify-next/releases/latest/download/Hiddify-Windows-Setup-x64.exe'>Скачать Hiddify</a>\n\n"
    "2. Скопируй ключ (начинается с <code>vless://</code>).\n"
    "3. Вставь ключ в приложение и нажми подключиться."
)

WELCOME_TEXT = (
    "Привет, <b>{name}</b>! 👋\n\n"
    "Я бот для выдачи скоростного доступа в сеть.\n"
    "Youtube 4K, Instagram, Игры — без ограничений скорости.\n\n"
    "🔐 Трафик шифруется. Логи не ведутся.\n"
    "Жми <b>«⚡️ Купить доступ»</b>, чтобы начать."
)

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_username(user: types.User) -> str:
    """Генерирует логин: Никнейм (если есть) или user_ID"""
    if user.username:
        return user.username
    return f"user_{user.id}"

async def get_expire_date(username: str, days: int) -> int:
    """Считает дату окончания подписки"""
    current_ts = int(time.time())
    seconds_add = days * 24 * 60 * 60
    
    try:
        user_info = await api.get_user(username)
        old_expire = user_info.get("expire") or 0
        if old_expire > current_ts:
            return old_expire + seconds_add
    except:
        pass
        
    return current_ts + seconds_add

# --- ХЕНДЛЕРЫ ---

@router.message(Command("start"))
async def cmd_start(message: types.Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    
    # Проверка юзера
    result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
    if not result.scalars().first():
        session.add(User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        ))
        await session.commit()
    
    await message.answer(
        WELCOME_TEXT.format(name=message.from_user.first_name),
        reply_markup=main_menu(), 
        parse_mode="HTML"
    )

@router.message(F.text == "🏠 Главная")
async def cmd_home(message: types.Message, session: AsyncSession, state: FSMContext):
    await cmd_start(message, session, state)

@router.message(F.text == "ℹ️ Помощь")
async def help_command(message: types.Message):
    await message.answer(INSTRUCTION_TEXT, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text == "⚡️ Купить доступ")
async def shop_menu(message: types.Message, session: AsyncSession):
    result = await session.execute(select(Plan).where(Plan.is_active == True))
    plans = result.scalars().all()
    
    if not plans:
        await message.answer("Тарифы не найдены.")
        return
        
    await message.answer("💎 Выберите период:", reply_markup=plans_keyboard(plans))

@router.callback_query(F.data.startswith("buy_plan_"))
async def process_buy_plan(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    plan_id = int(callback.data.split("_")[-1])
    plan = await session.get(Plan, plan_id)
    
    if not plan:
        await callback.answer("Тариф не найден.")
        return

    # Логин: Никнейм или ID
    username = get_username(callback.from_user)

    # === БЕСПЛАТНЫЙ ТАРИФ ===
    if plan.price == 0:
        await callback.answer("⏳ Активация...", show_alert=False)
        try:
            expire_ts = await get_expire_date(username, plan.duration_days)
            
            # 1. Создаем в Marzban
            user_data = await api.create_user(
                username=username,
                data_limit=plan.limit_gb,
                expire=expire_ts
            )
            
            if not user_data:
                await callback.message.answer("❌ Ошибка API Marzban.")
                return

            sub_url = user_data.get('subscription_url', '')
            links = user_data.get('links', [])
            vless_key = links[0] if links else "Ошибка ключа"
            
            # 2. Сохраняем в БД (Только существующие поля!)
            q = await session.execute(select(Subscription).where(Subscription.user_id == callback.from_user.id))
            existing_sub = q.scalars().first()

            if existing_sub:
                existing_sub.marzban_key = sub_url
                existing_sub.status = "active"
                existing_sub.expire_date = datetime.fromtimestamp(expire_ts)
                existing_sub.plan_id = plan.id
            else:
                new_sub = Subscription(
                    user_id=callback.from_user.id,
                    plan_id=plan.id,
                    marzban_key=sub_url,
                    status="active",
                    expire_date=datetime.fromtimestamp(expire_ts)
                )
                session.add(new_sub)
            
            await session.commit()
            
            await callback.message.answer(
                f"✅ <b>Доступ активирован!</b>\n"
                f"Тариф: {plan.name}\n\n"
                f"<b>Ваш ключ (ссылка):</b>\n{sub_url}\n\n"
                f"<b>Ваш ключ (VLESS):</b>\n<code>{vless_key}</code>",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await callback.message.answer(INSTRUCTION_TEXT, parse_mode="HTML", disable_web_page_preview=True)
            try: await callback.message.delete()
            except: pass
            
        except Exception as e:
            logger.error(f"Error free plan: {e}")
            await callback.message.answer(f"⚠️ Ошибка: {e}")
        return

    # === ПЛАТНЫЙ ТАРИФ ===
    await state.update_data(plan_id=plan_id, amount=plan.price)
    await state.set_state(PaymentStates.waiting_for_receipt)
    
    await callback.message.edit_text(
        f"💳 <b>Оплата: {plan.name}</b>\n"
        f"💰 Сумма: <b>{plan.price} RUB</b>\n\n"
        f"{settings.PAYMENT_INFO}\n\n"
        "📎 <b>Отправьте скриншот чека</b> в этот чат.",
        parse_mode="HTML"
    )

@router.message(PaymentStates.waiting_for_receipt, F.photo)
async def handle_receipt(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        data = await state.get_data()
        plan_id = data.get("plan_id")
        amount = data.get("amount")
        photo = message.photo[-1]
        
        plan = await session.get(Plan, plan_id)

        # 1. Работаем с Marzban (Логин = Никнейм)
        username = get_username(message.from_user)
        expire_ts = await get_expire_date(username, plan.duration_days)
        
        user_data = await api.create_user(
            username=username,
            data_limit=plan.limit_gb,
            expire=expire_ts
        )
        
        if not user_data:
            raise Exception("Marzban не вернул данные")

        sub_url = user_data.get('subscription_url', '')
        links = user_data.get('links', [])
        vless_key = links[0] if links else "Ключ генерируется..."
        expire_str = datetime.fromtimestamp(expire_ts).strftime('%d.%m.%Y')

        # 2. Сохраняем в БД (БЕЗ выдуманных полей)
        new_tx = Transaction(
            user_id=message.from_user.id,
            plan_id=plan_id,
            amount=amount,
            status="success",
            created_at=datetime.now()
        )
        session.add(new_tx)
        await session.flush()
        
        q = await session.execute(select(Subscription).where(Subscription.user_id == message.from_user.id))
        existing_sub = q.scalars().first()

        if existing_sub:
            existing_sub.marzban_key = sub_url
            existing_sub.status = "active"
            existing_sub.expire_date = datetime.fromtimestamp(expire_ts)
            existing_sub.plan_id = plan.id
        else:
            new_sub = Subscription(
                user_id=message.from_user.id,
                plan_id=plan_id,
                marzban_key=sub_url,
                status="active",
                expire_date=datetime.fromtimestamp(expire_ts)
            )
            session.add(new_sub)
        
        await session.commit()

        # 3. Ответ юзеру
        await message.answer(
            f"✅ <b>Платеж принят!</b>\n"
            f"Подписка продлена до: <b>{expire_str}</b>\n\n"
            f"<b>Ваш ключ (ссылка):</b>\n{sub_url}\n\n"
            f"<b>Ваш ключ (VLESS):</b>\n<code>{vless_key}</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        await message.answer(INSTRUCTION_TEXT, parse_mode="HTML", disable_web_page_preview=True)

        # 4. Админу
        try:
            await message.bot.send_photo(
                chat_id=settings.ADMIN_ID,
                photo=photo.file_id,
                caption=f"🔔 <b>Новый платеж!</b>\nЮзер: {message.from_user.full_name} (@{message.from_user.username})\nСумма: {amount} RUB\nТариф: {plan.name}\n\n✅ <i>Выдано автоматом</i>",
                reply_markup=admin_approval_keyboard(new_tx.id),
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    except Exception as e:
        logger.error(f"Receipt error: {e}", exc_info=True)
        await message.answer(f"🚫 Ошибка: {e}")
    
    finally:
        await state.clear()

@router.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message, session: AsyncSession):
    q = await session.execute(
        select(Subscription).where(Subscription.user_id == message.from_user.id).order_by(Subscription.id.desc())
    )
    sub = q.scalars().first()
    
    if not sub:
        await message.answer("У вас нет активных подписок.")
    else:
        status = "✅ Активна" if sub.status == "active" else "❌ Истекла"
        date_str = sub.expire_date.strftime('%d.%m.%Y %H:%M') if sub.expire_date else "Бессрочно"
        
        # Вычисляем логин
        username = get_username(message.from_user)
        
        try:
            user_info = await api.get_user(username)
            links = user_info.get('links', [])
            vless_key = links[0] if links else "Ошибка"
        except:
            vless_key = "..."

        await message.answer(
            f"👤 <b>Профиль</b>\n\n"
            f"Статус: {status}\n"
            f"Истекает: {date_str}\n\n"
            f"<b>Ваш ключ (ссылка):</b>\n{sub.marzban_key}\n\n"
            f"<b>Ваш ключ (VLESS):</b>\n<code>{vless_key}</code>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

# Callbacks админа
@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve(callback: types.CallbackQuery, session: AsyncSession):
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ Одобрено")

@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(callback: types.CallbackQuery, session: AsyncSession):
    tx_id = int(callback.data.split("_")[-1])
    tx = await session.get(Transaction, tx_id)
    if tx:
        tx.status = "failed"
        await session.commit()
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ Отклонено")
