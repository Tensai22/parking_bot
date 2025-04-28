from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import config

engine = create_async_engine(config.DB_URL, echo=True) 

AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def test_db_connection():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda conn: print("✅ Подключение к базе установлено!"))
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")

import asyncio
asyncio.run(test_db_connection())
