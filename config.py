import os
from dotenv import load_dotenv

load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
ALLOWED_TELEGRAM_IDS = {int(id_) for id_ in os.getenv("ALLOWED_TELEGRAM_IDS", "").split(",") if id_}
ALLOWED_PHONE_NUMBERS = set(os.getenv("ALLOWED_PHONE_NUMBERS", "").split(","))

# Google Sheets
SHEET_NAME = "КАРТРИДЖИ ДЛЯ GEM PREMIER НА СКЛАДЕ"
ARCHIVE_SHEET_NAME = "Архив истории операций GEM Premier"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Equipment types
EQUIPMENT_TYPES = ["Gem", "Edan", "Getein"]
GEMS = ["3500", "4000", "5000"]
TESTS = ["150", "300", "450", "600"]
PURPOSES = ["Отгрузка по контракту", "Замена по вылету", "Даем в долг"]
EDAN_PRODUCTS = [
    "Анализатор Edan", "BG-10", "BG-10 MicroSample", "BG-3", "BG-8",
    "CP-100", "CP-50", "i-15 (level 1)", "i-15 (level 2)", "i-15 (level 3)",
    "Новое(введите вручную)"
]