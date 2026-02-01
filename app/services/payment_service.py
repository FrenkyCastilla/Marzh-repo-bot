from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import time
import logging

from ..core.models import User, Transaction, Subscription, Plan
from ..core.config import settings
from .marzban_api import MarzbanAPI

logger = logging.getLogger(__name__)
api = MarzbanAPI()

async def process_new_payment(session: AsyncSession, user_id: int, amount: int, receipt_file_id: str, plan_id: int):
    """
    Создает транзакцию и выдает временный доступ (если нужно), пока админ не проверит.
    """
    # 1. Записываем транзакцию в БД
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        plan_id=plan_id, # Запоминаем, какой план хотели купить
        receipt_file_id=receipt_file_id,
        status="pending",
        created_at=datetime.utcnow()
    )
    session.add(transaction)
    await session.commit()
    
    # 2. Находим юзера в базе бота
    user_query = await session.execute(select(User).where(User.telegram_id == user_id))
    user = user_query.scalar_one()

    # 3. Выдаем доступ (пока на 24 часа, до проверки чека)
    # Если юзер уже есть - продлеваем ему на сутки, чтобы не отключался
    # Если нет - создаем
    
    # Сначала проверим текущий статус в Marzban
    marzban_user = await api.get_user(user.username)
    current_ts = int(time.time())
    temp_seconds = 24 * 60 * 60 # 24 часа

    if marzban_user and marzban_user.get('expire'):
        # Если подписка жива, накидываем 24 часа к текущему сроку (аванс)
        # Если просрочена - от текущего момента
        old_expire = marzban_user.get('expire')
        if old_expire > current_ts:
            new_expire = old_expire + temp_seconds
        else:
            new_expire = current_ts + temp_seconds
    else:
        new_expire = current_ts + temp_seconds

    # Создаем/Обновляем в Marzban
    # ВАЖНО: Тут лимит ставим 0 (безлимит) или какой-то стартовый,
    # но полноценный лимит выставим при одобрении
    sub_data = await api.create_user(user.username, 0, new_expire)
    
    if not sub_data:
        return None, "Ошибка связи с Marzban"

    # Сохраняем подписку в БД бота
    sub = Subscription(
        user_id=user_id,
        marzban_key=sub_data.get("subscription_url", ""),
        status="active",
        expire_date=datetime.fromtimestamp(new_expire)
    )
    session.add(sub)
    await session.commit()
    
    return sub, None

async def approve_payment(session: AsyncSession, transaction_id: int):
    """
    Админ нажал 'Одобрить'. Начисляем полный срок тарифа.
    """
    # 1. Ищем транзакцию и подтягиваем План
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await session.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        return False, "Транзакция не найдена"

    # Получаем план, чтобы узнать duration_days
    plan_stmt = select(Plan).where(Plan.id == transaction.plan_id)
    plan_res = await session.execute(plan_stmt)
    plan = plan_res.scalar_one_or_none()

    if not plan:
        return False, "Тариф не найден в базе"

    # 2. Ищем юзера
    user_stmt = select(User).where(User.telegram_id == transaction.user_id)
    user_res = await session.execute(user_stmt)
    user = user_res.scalar_one()

    # 3. --- ГЛАВНАЯ МАГИЯ: СУММИРОВАНИЕ ВРЕМЕНИ ---
    marzban_user = await api.get_user(user.username)
    current_ts = int(time.time())
    
    # Переводим дни тарифа в секунды
    add_seconds = plan.duration_days * 24 * 60 * 60 

    if marzban_user and marzban_user.get('expire'):
        old_expire = marzban_user.get('expire')
        
        # Если подписка активна (не истекла) -> добавляем к КОНЦУ старой даты
        if old_expire > current_ts:
            final_expire = old_expire + add_seconds
        else:
            # Если истекла -> добавляем от СЕЙЧАС
            final_expire = current_ts + add_seconds
    else:
        # Новый юзер
        final_expire = current_ts + add_seconds

    # 4. Применяем изменения в Marzban
    # Также ставим правильный лимит ГБ из тарифа
    limit_gb = plan.limit_gb if plan.limit_gb > 0 else 0 # 0 = безлимит
    
    success = await api.modify_user(
        user.username, 
        {
            "expire": final_expire,
            "data_limit": limit_gb * 1024 * 1024 * 1024 if limit_gb > 0 else 0,
            "status": "active"
        }
    )

    if not success:
        return False, "Не удалось обновить пользователя в Marzban"

    # 5. Обновляем статус транзакции и подписки в БД бота
    transaction.status = "approved"
    
    # Обновим запись о подписке
    sub_stmt = select(Subscription).where(Subscription.user_id == user.telegram_id)
    sub_res = await session.execute(sub_stmt)
    sub = sub_res.scalars().first()
    
    if sub:
        sub.expire_date = datetime.fromtimestamp(final_expire)
        sub.status = "active"
    
    await session.commit()
    return True, "Успешно"

async def reject_payment(session: AsyncSession, transaction_id: int):
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await session.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if transaction:
        transaction.status = "rejected"
        await session.commit()
        
        # Опционально: можно отключать юзера в Marzban, если чек липовый
        # user_stmt = select(User).where(User.telegram_id == transaction.user_id)
        # user = (await session.execute(user_stmt)).scalar_one()
        # await api.modify_user(user.username, {"status": "disabled"})
        
        return True, "Отклонено"
    return False, "Транзакция не найдена"
