import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SHOP_ID = os.getenv("SHOP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./donate_bot.db")

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", "25575"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))

PRODUCTS_RAW = os.getenv("PRODUCTS", "VIP|500|lp user {nick} parent add vip")
PRODUCTS = []
for item in PRODUCTS_RAW.split(";"):
    parts = item.strip().split("|")
    if len(parts) == 3:
        PRODUCTS.append({
            "name": parts[0],
            "price": int(parts[1]),
            "command": parts[2]
        })

ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")
