import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db")
    
    MARZBAN_HOST: str = os.getenv("MARZBAN_HOST", "")
    MARZBAN_USERNAME: str = os.getenv("MARZBAN_USERNAME", "")
    MARZBAN_PASSWORD: str = os.getenv("MARZBAN_PASSWORD", "")
    
    # LYRA: Исправлено. Теперь по умолчанию берем первый попавшийся тег (авто-поиск)
    INBOUND_TAG: str = os.getenv("INBOUND_TAG", "") 
    
    # LYRA: ВАЖНОЕ ИСПРАВЛЕНИЕ. Убираем "xtls-rprx-vision" из дефолта.
    # Если в .env пусто, то и flow будет пустым ("none"), чтобы галочка ставилась.
    VLESS_FLOW: str = os.getenv("VLESS_FLOW", "")
    
    PAYMENT_INFO: str = os.getenv("PAYMENT_INFO", "Transfer RUB to Ozon Bank: +79990000000")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
