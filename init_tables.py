import asyncio
from app.db.session import engine
from app.db.base import Base

async def init():
    print("⏳ Подключение к базе...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ УСПЕХ: Таблицы созданы!")

if __name__ == "__main__":
    asyncio.run(init())
