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
    
    PAYMENT_INFO: str = os.getenv("PAYMENT_INFO", "Transfer RUB to Ozon Bank: +79990000000")

    class Config:
        env_file = ".env"

settings = Settings()
