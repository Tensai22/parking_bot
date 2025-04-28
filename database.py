from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import config
import ssl
ssl_context = ssl.create_default_context()

# Создаем асинхронный движок
engine = create_async_engine(
    config.DATABASE_URL,  # исправил название переменной
    echo=True,
    connect_args={"ssl": ssl_context}  # добавил SSL для Render
)

# Создаем фабрику сессий
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для моделей
Base = declarative_base()
