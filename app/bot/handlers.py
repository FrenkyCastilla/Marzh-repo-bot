from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.models import User, Plan, Subscription, Transaction
from ..core.config import settings
from .keyboards import main_menu, plans_keyboard, admin_approval_keyboard
from ..services.payment_service import process_new_payment, approve_payment, reject_payment

router = Router()

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

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
    
    await message.answer(
        "👋 Добро пожаловать в наш сервис!\n\nВыберите действие в меню ниже:",
        reply_markup=main_menu()
    )

@router.message(F.text == "🛒 Купить доступ")
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
        
    await state.update_data(plan_id=plan_id, amount=plan.price)
    await state.set_state(PaymentStates.waiting_for_receipt)
    
    await callback.message.answer(
        f"💳 Вы выбрали: {plan.name}\n"
        f"💰 К оплате: {plan.price} RUB\n\n"
        f"{settings.PAYMENT_INFO}\n\n"
        "После оплаты отправьте скриншот чека сюда."
    )
    await callback.answer()

@router.message(PaymentStates.waiting_for_receipt, F.photo)
async def handle_receipt(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    plan_id = data.get("plan_id")
    amount = data.get("amount")
    photo = message.photo[-1]
    
    await message.answer("⏳ Обрабатываем ваш платеж... Доступ будет предоставлен автоматически на 24 часа.")
    
    sub, error = await process_new_payment(session, message.from_user.id, amount, photo.file_id, plan_id)
    
    if error:
        await message.answer(f"❌ Ошибка: {error}")
    else:
        await message.answer(
            "✅ Платеж получен! Вам предоставлен доступ на 24 часа.\n"
            "Администратор проверит чек и продлит подписку на полный срок.\n\n"
            f"Ваша ссылка: `{sub.marzban_key}`",
            parse_mode="Markdown"
        )
        
        # Notify Admin
        admin_text = (
            f"🔔 Новый платеж!\n"
            f"Пользователь: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"Сумма: {amount} RUB\n"
            f"ID транзакции будет создан после сохранения."
        )
        # We need the transaction ID, let's fetch it
        tx_query = await session.execute(
            select(Transaction).where(Transaction.user_id == message.from_user.id).order_by(Transaction.id.desc())
        )
        tx = tx_query.scalars().first()
        
        await message.bot.send_photo(
            settings.ADMIN_ID,
            photo.file_id,
            caption=f"🔔 Новый платеж!\nID: {tx.id}\nСумма: {amount} RUB",
            reply_markup=admin_approval_keyboard(tx.id)
        )
    
    await state.clear()

@router.message(F.text == "👤 Профиль")
async def profile_menu(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    sub_query = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.id.desc())
    )
    sub = sub_query.scalars().first()
    
    if not sub:
        await message.answer("У вас пока нет активных подписок.")
    else:
        status = "✅ Активна" if sub.status == "active" else "❌ Истекла"
        await message.answer(
            f"👤 Профиль\n\n"
            f"Статус: {status}\n"
            f"Истекает: {sub.expire_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"Ключ: `{sub.marzban_key}`",
            parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve(callback: types.CallbackQuery, session: AsyncSession):
    tx_id = int(callback.data.split("_")[-1])
    success, msg = await approve_payment(session, tx_id)
    
    if success:
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ Одобрено!")
        # Notify user
        tx_query = await session.execute(select(Transaction).where(Transaction.id == tx_id))
        tx = tx_query.scalar_one()
        await callback.bot.send_message(tx.user_id, "✅ Ваш платеж подтвержден! Подписка продлена на полный срок.")
    else:
        await callback.answer(f"Ошибка: {msg}")

@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(callback: types.CallbackQuery, session: AsyncSession):
    tx_id = int(callback.data.split("_")[-1])
    success, msg = await reject_payment(session, tx_id)
    
    if success:
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ Отклонено!")
        # Notify user
        tx_query = await session.execute(select(Transaction).where(Transaction.id == tx_id))
        tx = tx_query.scalar_one()
        await callback.bot.send_message(tx.user_id, "❌ Ваш платеж отклонен. Доступ заблокирован.")
    else:
        await callback.answer(f"Ошибка: {msg}")
