import os
from dotenv import load_dotenv

load_dotenv()
print("Файл .env загружен") 

BOT_TOKEN = os.getenv("BOT_TOKEN")
print(f"Загруженный токен: {BOT_TOKEN}")  

DB_URL = os.getenv("DATABASE_URL")
PARKING_API = os.getenv("PARKING_API")
PAYMENT_API = os.getenv("PAYMENT_API")
