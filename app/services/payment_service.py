import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.models import User, Transaction, Subscription, Plan
from .marzban_api import MarzbanAPI

logger = logging.getLogger(__name__)
marzban = MarzbanAPI()

async def process_new_payment(session: AsyncSession, user_id: int, amount: float, file_id: str, plan_id: int):
    # 1. Create Transaction
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        proof_file_id=file_id,
        status="pending"
    )
    session.add(transaction)
    
    # 2. Optimistic UI: Grant 24h access
    user_query = await session.execute(select(User).where(User.telegram_id == user_id))
    user = user_query.scalar_one_or_none()
    
    plan_query = await session.execute(select(Plan).where(Plan.id == plan_id))
    plan = plan_query.scalar_one_or_none()
    
    if not user or not plan:
        return None, "User or Plan not found"

    # Marzban username based on telegram_id
    marzban_username = f"user_{user_id}"
    expire_24h = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
    
    # Call Marzban
    marzban_res = await marzban.create_user(
        username=marzban_username,
        data_limit=plan.limit_gb,
        expire=expire_24h
    )
    
    if marzban_res:
        # Save subscription
        subscription = Subscription(
            user_id=user_id,
            marzban_key=marzban_res.get("subscription_url", ""),
            expire_date=datetime.utcnow() + timedelta(hours=24),
            status="active"
        )
        session.add(subscription)
        await session.commit()
        return subscription, None
    else:
        await session.commit()
        return None, "Marzban service unavailable"

async def approve_payment(session: AsyncSession, transaction_id: int):
    tx_query = await session.execute(select(Transaction).where(Transaction.id == transaction_id))
    tx = tx_query.scalar_one_or_none()
    
    if not tx or tx.status != "pending":
        return False, "Transaction not found or already processed"
    
    # Update status
    tx.status = "approved"
    
    # Find subscription to extend
    sub_query = await session.execute(
        select(Subscription).where(Subscription.user_id == tx.user_id).order_by(Subscription.id.desc())
    )
    sub = sub_query.scalars().first()
    
    # In a real scenario, we'd need to know which plan was bought. 
    # For simplicity, let's assume we extend based on the last active subscription or a default.
    # Ideally, Transaction should have a plan_id.
    
    # Let's extend by 30 days for now (or logic to find plan)
    new_expire = datetime.utcnow() + timedelta(days=30)
    if sub:
        sub.expire_date = new_expire
        
        # Update Marzban
        marzban_username = f"user_{tx.user_id}"
        await marzban.modify_user(marzban_username, {"expire": int(new_expire.timestamp())})
    
    await session.commit()
    return True, "Approved"

async def reject_payment(session: AsyncSession, transaction_id: int):
    tx_query = await session.execute(select(Transaction).where(Transaction.id == transaction_id))
    tx = tx_query.scalar_one_or_none()
    
    if not tx or tx.status != "pending":
        return False, "Transaction not found"
    
    tx.status = "rejected"
    
    # Ban user and disable VPN
    user_query = await session.execute(select(User).where(User.telegram_id == tx.user_id))
    user = user_query.scalar_one_or_none()
    if user:
        user.is_banned = True
        
    marzban_username = f"user_{tx.user_id}"
    await marzban.delete_user(marzban_username)
    
    await session.commit()
    return True, "Rejected"
