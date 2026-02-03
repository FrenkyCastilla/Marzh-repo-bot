import asyncio
from sqlalchemy import delete
from app.core.db import AsyncSessionLocal
from app.core.models import Plan

async def seed_plans():
    print("💸 Обновляем экономическую модель...")
    async with AsyncSessionLocal() as session:
        # 1. Сначала чистим таблицу, чтобы не плодить дубли
        print("🧹 Удаляем старые цены...")
        await session.execute(delete(Plan))
        await session.commit()
        
        # 2. Заливаем актуальный прайс
        plans = [
            Plan(name="🚀 Тест (24 часа)", price=0, duration_days=1, limit_gb=3, is_active=True),
            Plan(name="📅 1 Месяц", price=500, duration_days=30, limit_gb=0, is_active=True),
            Plan(name="💎 3 Месяца", price=1350, duration_days=90, limit_gb=0, is_active=True),
            Plan(name="🔥 6 Месяцев", price=2500, duration_days=180, limit_gb=0, is_active=True),
            Plan(name="👑 1 Год", price=5000, duration_days=365, limit_gb=0, is_active=True),
        ]

        session.add_all(plans)
        await session.commit()
        print("✅ УСПЕХ: Новые тарифы загружены!")

if __name__ == "__main__":
    asyncio.run(seed_plans())
