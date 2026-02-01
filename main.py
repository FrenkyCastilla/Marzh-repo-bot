import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, update
from datetime import datetime

from app.core.config import settings
from app.core.db import engine, AsyncSessionLocal, Base
from app.core.models import Subscription
from app.bot.handlers import router as bot_router
from app.web.admin import setup_admin
from app.services.marzban_api import MarzbanAPI

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot & Dispatcher
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Marzban API
marzban = MarzbanAPI()

async def check_expired_subscriptions():
    logger.info("Checking for expired subscriptions...")
    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        query = select(Subscription).where(
            Subscription.expire_date < now,
            Subscription.status == "active"
        )
        result = await session.execute(query)
        expired_subs = result.scalars().all()
        
        for sub in expired_subs:
            logger.info(f"Subscription {sub.id} for user {sub.user_id} expired.")
            # Disable in Marzban
            marzban_username = f"user_{sub.user_id}"
            await marzban.modify_user(marzban_username, {"status": "disabled"})
            
            # Update DB
            sub.status = "expired"
            
            # Notify User
            try:
                await bot.send_message(sub.user_id, "⚠️ Ваша подписка VPN истекла. Пожалуйста, продлите её в меню.")
            except Exception as e:
                logger.error(f"Failed to notify user {sub.user_id}: {e}")
        
        await session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Init DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Start Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_expired_subscriptions, 'interval', hours=1)
    scheduler.start()
    
    # 3. Start Bot
    dp.include_router(bot_router)
    # Inject session into handlers
    @dp.update.outer_middleware()
    async def database_middleware(handler, event, data):
        async with AsyncSessionLocal() as session:
            data["session"] = session
            return await handler(event, data)
            
    asyncio.create_task(dp.start_polling(bot))
    
    yield
    
    # Shutdown
    await bot.session.close()
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Setup Admin
setup_admin(app, engine)

@app.get("/")
async def root():
    return {"status": "running", "service": "VPN Shop Bot API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
