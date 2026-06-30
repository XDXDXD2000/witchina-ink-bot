import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env файле")

ADMIN_ID = os.getenv("ADMIN_ID", "623268834,566312940")

# ИНФО О БОТЕ
BOT_AUTHOR = "@akob007_228"
BOT_AUTHOR_NICK = "XDXDXD"
BOT_VERSION = "2.0"

# РАБОЧЕЕ ВРЕМЯ: ПН-ЧТ с 18:00 до 22:00
WORK_DAYS = [0, 1, 2, 3]
WORK_START_HOUR = 18
WORK_END_HOUR = 22
SLOT_DURATION_MINUTES = 60

MIN_ADVANCE_HOURS = 2
MAX_ADVANCE_DAYS = 14
REMIND_HOURS_BEFORE = 2

# КОНТАКТЫ СТУДИИ
STUDIO_PHONE = "+7 989 772 5484"
STUDIO_TG = "@dooble_chisburger"
STUDIO_INSTAGRAM = "https://www.instagram.com/w1tch1na"
STUDIO_ADDRESS = "Московская 158/2"

# СЕКРЕТНЫЕ СЛОВА ДЛЯ СКИДОК
SECRET_WORDS = {
    "ветчина": 15,
    "люблю маму": 10,
    "колбаса": 20,
    "тату": 5,
    "дина": 15,
    "витчина": 15,
}

# ПОДСКАЗКА ДЛЯ СЕКРЕТНЫХ СЛОВ (завуалированно)
SECRET_HINT = "🐷 Если ты знаешь пароль от нашей тусовки — введи его тайком..."

DB_PATH = "appointments.db"
SKETCHES_PATH = "sketches"
STUDIO_PATH = "stydiya"  # Папка с фото студии

PINTEREST_LINK = "https://ru.pinterest.com/hersplanetajopa/тати/?invite_code=3704bce89bb24709ab84638b19e75e7f&sender=761249280672518271"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")