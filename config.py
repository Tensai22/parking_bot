import os
from dotenv import load_dotenv

load_dotenv()
print("Файл .env загружен") 

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # <-- исправлено
