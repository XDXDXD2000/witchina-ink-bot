import re
import logging
import random
import os
import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    ADMIN_ID, SECRET_WORDS, SECRET_HINT, PINTEREST_LINK, 
    SKETCHES_PATH, STUDIO_PATH, WORK_DAYS, MIN_ADVANCE_HOURS, MAX_ADVANCE_DAYS,
    BOT_AUTHOR, BOT_AUTHOR_NICK, BOT_VERSION,
    STUDIO_PHONE, STUDIO_TG, STUDIO_INSTAGRAM, STUDIO_ADDRESS
)
from db import db
from states import BookingStates, ReviewStates, AdminStates
from keyboards import (
    get_main_keyboard, get_services_keyboard,
    get_dates_keyboard, get_time_keyboard, get_confirmation_keyboard,
    get_cancel_booking_keyboard, get_review_rating_keyboard,
    get_admin_reviews_keyboard, get_yes_no_keyboard, get_back_keyboard,
    get_admin_main_keyboard
)

router = Router()
logger = logging.getLogger(__name__)

# ========== СПИСОК АДМИНОВ ==========
ADMIN_IDS = [623268834, 566312940]

# ========== ЦИТАТЫ ==========

QUOTES = [
    "«Жизнь — это то, что с тобой происходит, пока ты строишь планы» — Джон Леннон",
    "«Будь собой, остальные роли уже заняты» — Оскар Уайльд",
    "«Ты должен быть тем изменением, которое хочешь видеть в мире» — Махатма Ганди",
    "«Не бойся совершенства — тебе его не достичь» — Сальвадор Дали",
    "«Дорогу осилит идущий» — Сенека",
    "«Сложнее всего начать действовать, все остальное зависит только от упорства» — Амелия Эрхарт",
    "«Лучший способ предсказать будущее — создать его» — Питер Друкер",
    "«Искусство — это ложь, которая позволяет нам понять правду» — Пабло Пикассо",
    "«Татуировка — это история, написанная на коже»",
    "«Каждое тату имеет свою душу»",
]

def get_random_quote() -> str:
    return random.choice(QUOTES)

# ========== КЭШ ==========

_services_cache = []
_services_cache_time = None
_users_cache = []
_users_cache_time = None

async def get_cached_services():
    global _services_cache, _services_cache_time
    now = datetime.now()
    if _services_cache_time is None or (now - _services_cache_time).seconds > 3600:
        _services_cache = await db.get_services()
        _services_cache_time = now
    return _services_cache

async def get_cached_users():
    global _users_cache, _users_cache_time
    now = datetime.now()
    if _users_cache_time is None or (now - _users_cache_time).seconds > 300:
        _users_cache = await db.get_all_users()
        _users_cache_time = now
    return _users_cache

def validate_phone(phone: str) -> bool:
    clean = re.sub(r"\D", "", phone)
    return len(clean) >= 10 and len(clean) <= 12

def format_phone(phone: str) -> str:
    clean = re.sub(r"\D", "", phone)
    if len(clean) == 11 and clean.startswith("8"):
        clean = "7" + clean[1:]
    if len(clean) == 10:
        clean = "7" + clean
    return "+" + clean

def get_available_dates():
    now = datetime.now()
    dates = []
    months = {
        1: "янв", 2: "фев", 3: "мар", 4: "апр",
        5: "май", 6: "июн", 7: "июл", 8: "авг",
        9: "сен", 10: "окт", 11: "ноя", 12: "дек"
    }
    weekdays_short = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    
    for i in range(MAX_ADVANCE_DAYS + 1):
        date = now + timedelta(days=i)
        if date.weekday() not in WORK_DAYS:
            continue
        if date < now + timedelta(hours=MIN_ADVANCE_HOURS):
            continue
        
        day = date.day
        month = months[date.month]
        weekday = weekdays_short[date.weekday()]
        
        date_str = date.strftime("%Y-%m-%d")
        display_str = f"{weekday} {day}.{month}"  # Пример: "ПН 6.июл"
        dates.append((date_str, display_str))
    return dates

def get_random_sketch():
    if not os.path.exists(SKETCHES_PATH):
        os.makedirs(SKETCHES_PATH)
        return None
    files = [f for f in os.listdir(SKETCHES_PATH) 
             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    if not files:
        return None
    return os.path.join(SKETCHES_PATH, random.choice(files))

def get_studio_photos():
    if not os.path.exists(STUDIO_PATH):
        os.makedirs(STUDIO_PATH)
        return []
    files = [f for f in os.listdir(STUDIO_PATH) 
             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    return sorted(files)

def format_prices():
    return (
        "💰 <b>Прайс-лист студии</b>\n\n"
        "• Консультация — БЕСПЛАТНО\n"
        "• Татуировка в стиле минимализм — от 2000 руб.\n"
        "• Татуировка до 20 см — от 6000 руб.\n"
        "• Цветная татуировка — от 4000 руб.\n"
        "• Татуировка 20 см и более — от 9000 руб.\n\n"
        "⚠️ <i>Цены являются приблизительными и могут меняться в зависимости от сложности, времени работы и других факторов. Точную стоимость уточняйте на консультации с мастером.</i>"
    )

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    name = message.from_user.first_name or "Чувак"
    
    if message.from_user.id in ADMIN_IDS:
        text = f"Йоу, {name}! 👋\n\nДобро пожаловать в админ-панель «Витчина INK»"
        await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
        return
    
    text = (
        f"Йоу, {name}! 👋\n\n"
        f"Добро пожаловать в <b>«Витчина INK»</b> 🖤\n\n"
        f"🎨 Мастер Дина — тату на все стили\n"
        f"🔥 Секретные скидки для своих\n"
        f"⭐ Отзывы от реальных людей\n"
        f"💀 Рандомайзер эскизов\n\n"
        f"Погнали? Выбирай, что хочешь:"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Админ-панель", reply_markup=get_admin_main_keyboard())
    else:
        await message.answer("Главное меню", reply_markup=get_main_keyboard())

# ========== ОБЩАЯ КНОПКА НАЗАД ==========

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    if callback.from_user.id in ADMIN_IDS:
        await callback.message.answer("Админ-панель", reply_markup=get_admin_main_keyboard())
    else:
        await callback.message.answer("Главное меню", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    services = await get_cached_services()
    await state.set_state(BookingStates.choosing_service)
    await callback.message.delete()
    await callback.message.answer(
        "🎨 <b>Выбери услугу</b>\n\nОт консультации до большой работы",
        reply_markup=get_services_keyboard(services),
        parse_mode="HTML"
    )
    await callback.answer()

# ========== АДМИН-ПАНЕЛЬ ==========

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ========== РАССЫЛКА ==========

@router.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.set_state(AdminStates.mailing_text)
    await callback.message.delete()
    await callback.message.answer(
        "📢 <b>Создание рассылки</b>\n\n"
        "Напиши текст сообщения для рассылки.\n"
        "Можно использовать HTML-разметку.\n\n"
        "Чтобы отменить — нажми /menu",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.mailing_text)
async def process_mailing_text(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён!")
        await state.clear()
        return
    
    text = message.text
    await state.update_data(mailing_text=text)
    
    users = await get_cached_users()
    
    if not users:
        await message.answer("❌ Нет пользователей для рассылки")
        await state.clear()
        return
    
    await state.set_state(AdminStates.mailing_confirm)
    await message.answer(
        f"📢 <b>Подтверждение рассылки</b>\n\n"
        f"Текст сообщения:\n{text[:200]}{'...' if len(text) > 200 else ''}\n\n"
        f"👥 Получателей: {len(users)}\n\n"
        f"Отправить?",
        reply_markup=get_yes_no_keyboard(0),
        parse_mode="HTML"
    )

@router.callback_query(AdminStates.mailing_confirm, F.data == "approve_0")
async def confirm_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    data = await state.get_data()
    text = data.get("mailing_text", "")
    users = await get_cached_users()
    
    if not users or not text:
        await callback.message.delete()
        await callback.message.answer("❌ Ошибка: нет текста или пользователей")
        await state.clear()
        await callback.answer()
        return
    
    await callback.message.delete()
    await callback.message.answer(
        f"📤 <b>Начинаю рассылку...</b>\n\n"
        f"👥 Получателей: {len(users)}",
        parse_mode="HTML"
    )
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            await callback.bot.send_message(
                user["user_id"],
                f"📢 <b>Новое сообщение от студии «Витчина INK»</b>\n\n{text}",
                parse_mode="HTML"
            )
            sent += 1
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user['user_id']}: {e}")
            failed += 1
        
        await asyncio.sleep(0.1)
    
    await state.clear()
    await callback.message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего: {len(users)}",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(AdminStates.mailing_confirm, F.data == "reject_0")
async def cancel_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "❌ Рассылка отменена",
        reply_markup=get_admin_main_keyboard()
    )
    await callback.answer()

# ========== О БОТЕ ==========

@router.callback_query(F.data == "about_bot")
async def about_bot(callback: CallbackQuery):
    quote = get_random_quote()
    text = (
        "🤖 <b>О боте «Витчина INK»</b>\n\n"
        "Бот для записи в тату-салон. Помогает выбрать услугу, время.\n"
        "Поддерживает секретные скидки, отзывы и рандомайзер эскизов.\n\n"
        "🔧 <b>Создатель:</b> @akob007_228\n"
        f"📦 <b>Версия:</b> {BOT_VERSION}\n"
        f"🐍 <b>Написан на:</b> Python + aiogram\n\n"
        f"✨ <i>{quote}</i>\n\n"
        f"— С любовью, XDXDXD"
    )
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ========== ИНФОРМАЦИОННЫЕ КНОПКИ ==========

@router.callback_query(F.data == "about")
async def about_salon(callback: CallbackQuery):
    text = (
        "🖤 <b>«Витчина INK»</b>\n\n"
        f"🎨 <b>Мастер:</b> Дина (тату на все стили)\n"
        f"📍 <b>Адрес:</b> {STUDIO_ADDRESS}\n"
        "🕐 <b>Часы работы:</b> ПН-ЧТ с 18:00 до 22:00\n"
        f"📞 {STUDIO_PHONE}\n\n"
        f"💬 {STUDIO_TG}\n"
        f"📸 <a href='{STUDIO_INSTAGRAM}'>Instagram: w1tch1na</a>"
    )
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "contacts")
async def contacts(callback: CallbackQuery):
    photos = get_studio_photos()
    
    text = (
        "📍 <b>Контакты</b>\n\n"
        f"🏠 <b>Адрес:</b> {STUDIO_ADDRESS}\n"
        f"📞 <b>Телефон:</b> {STUDIO_PHONE}\n"
        f"💬 <b>Telegram:</b> {STUDIO_TG}\n"
        f"📸 <b>Instagram:</b> <a href='{STUDIO_INSTAGRAM}'>w1tch1na</a>"
    )
    
    await callback.message.delete()
    
    if photos:
        try:
            photo_path = os.path.join(STUDIO_PATH, photos[0])
            photo = FSInputFile(photo_path)
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )
            if len(photos) > 1:
                for i, photo_file in enumerate(photos[1:4], 2):
                    photo_path = os.path.join(STUDIO_PATH, photo_file)
                    photo = FSInputFile(photo_path)
                    await callback.message.answer_photo(
                        photo=photo,
                        caption=f"📸 Фото студии ({i}/{len(photos)})",
                        parse_mode="HTML"
                    )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    
    await callback.answer()

@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery):
    text = format_prices()
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ========== РАНДОМАЙЗЕР ==========

@router.callback_query(F.data == "random_sketch")
async def random_sketch(callback: CallbackQuery):
    sketch_path = get_random_sketch()
    if not sketch_path:
        await callback.message.delete()
        await callback.message.answer(
            "😅 Эскизов пока нет! Загляни позже!",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    try:
        photo = FSInputFile(sketch_path)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption="🎨 <b>Вот тебе эскиз!</b>",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка эскиза: {e}")
        await callback.message.answer("🤔 Ошибка", reply_markup=get_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "pinterest")
async def show_pinterest(callback: CallbackQuery):
    text = (
        "🎨 <b>Наша доска на Pinterest</b>\n\n"
        f"👉 <a href='{PINTEREST_LINK}'>Перейти на Pinterest</a>"
    )
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()

# ========== ЗАПИСЬ ==========

@router.callback_query(F.data == "book_start")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    services = await get_cached_services()
    if not services:
        await callback.message.delete()
        await callback.message.answer("Ошибка", reply_markup=get_main_keyboard())
        await callback.answer()
        return
    await state.set_state(BookingStates.choosing_service)
    await callback.message.delete()
    await callback.message.answer(
        "🎨 <b>Выбери услугу</b>",
        reply_markup=get_services_keyboard(services),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(BookingStates.choosing_service, F.data.startswith("service_"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    await state.update_data(service_id=service_id)
    dates = get_available_dates()
    if not dates:
        await callback.message.delete()
        await callback.message.answer(
            "😕 Нет свободных дат",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return
    await state.set_state(BookingStates.choosing_date)
    await callback.message.delete()
    await callback.message.answer(
        "📅 <b>Выбери дату</b>\n\nПН-ЧТ с 18:00 до 22:00",
        reply_markup=get_dates_keyboard(dates),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(BookingStates.choosing_date, F.data.startswith("date_"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    slots = await db.get_free_slots(date_str)
    if not slots:
        dates = get_available_dates()
        await callback.message.delete()
        await callback.message.answer(
            "😕 Всё занято. Выбери другую дату:",
            reply_markup=get_dates_keyboard(dates)
        )
        await callback.answer()
        return
    await state.update_data(date=date_str)
    await state.set_state(BookingStates.choosing_time)
    await callback.message.delete()
    await callback.message.answer(
        f"🕐 <b>Выбери время на {date_str}</b>",
        reply_markup=get_time_keyboard(slots),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(BookingStates.choosing_time, F.data.startswith("time_"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_")[1]
    if time_str == "no_slots":
        await callback.answer("Нет слотов")
        return
    data = await state.get_data()
    date_str = data.get("date")
    if not date_str:
        await callback.message.delete()
        await callback.message.answer("Ошибка. Начни /start", reply_markup=get_main_keyboard())
        await callback.answer()
        return
    slot_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    slot_iso = slot_datetime.isoformat()
    await state.update_data(slot_iso=slot_iso, time_str=time_str)
    await state.set_state(BookingStates.entering_phone)
    await callback.message.delete()
    await callback.message.answer(
        "📞 <b>Введи номер телефона</b>\n\nПример: +7 999 123-45-67",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(BookingStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    phone_raw = message.text.strip()
    if not validate_phone(phone_raw):
        await message.answer(
            "❌ Неверный формат\n\nВведи: +7 999 123-45-67\nИли /menu"
        )
        return
    phone = format_phone(phone_raw)
    await state.update_data(phone=phone)
    await state.set_state(BookingStates.entering_secret)
    await message.answer(
        f"🔐 <b>Секретный код?</b>\n\n{SECRET_HINT}\n\nЕсли не знаешь — напиши 'нет'"
    )

@router.message(BookingStates.entering_secret)
async def enter_secret(message: Message, state: FSMContext):
    secret = message.text.strip().lower()
    data = await state.get_data()
    service_id = data.get("service_id")
    slot_iso = data.get("slot_iso")
    phone = data.get("phone")
    
    if not all([service_id, slot_iso, phone]):
        await message.answer("❌ Ошибка. Начни /start", reply_markup=get_main_keyboard())
        await state.clear()
        return
    
    discount = 0
    secret_used = None
    if secret in SECRET_WORDS:
        secret_used = secret
        discount = SECRET_WORDS[secret]
        await message.answer(f"🎉 Скидка {discount}% активирована!")
    else:
        await message.answer("Окей, без скидки")
    
    await state.update_data(secret_used=secret_used, discount=discount)
    await state.set_state(BookingStates.entering_description)
    await message.answer(
        "✍️ <b>Опиши тату</b>\n\nРазмер, стиль, место, цвет\n\nМожно «Не знаю»"
    )

@router.message(BookingStates.entering_description)
async def enter_description(message: Message, state: FSMContext):
    description = message.text.strip()
    await state.update_data(description=description)
    
    data = await state.get_data()
    service_id = data.get("service_id")
    slot_iso = data.get("slot_iso")
    phone = data.get("phone")
    discount = data.get("discount", 0)
    
    services = await get_cached_services()
    service = next((s for s in services if s.id == service_id), None)
    service_name = service.name if service else "Неизвестная"
    service_price = service.price if service else 0
    
    slot_dt = datetime.fromisoformat(slot_iso)
    slot_str = slot_dt.strftime("%d.%m.%Y в %H:%M")
    
    discount_text = f"\n💰 Скидка: {discount}%" if discount > 0 else ""
    total_price = service_price - int(service_price * discount / 100) if discount > 0 else service_price
    price_text = f"\n💵 Цена: {total_price} руб." if service_price > 0 else ""
    
    await state.set_state(BookingStates.confirming)
    await message.answer(
        f"✅ <b>Проверь данные</b>\n\n"
        f"🎨 Услуга: {service_name}\n"
        f"🕐 Время: {slot_str}\n"
        f"📞 Телефон: {phone}\n"
        f"✍️ Описание: {description}\n"
        f"{discount_text}{price_text}\n\n"
        f"Всё верно?",
        reply_markup=get_confirmation_keyboard(),
        parse_mode="HTML"
    )

# ========== ПОДТВЕРЖДЕНИЕ ==========

@router.callback_query(BookingStates.confirming, F.data == "confirm_yes")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name
    
    appointment_id = await db.book_appointment(
        user_id=user_id,
        username=username,
        phone=data.get("phone"),
        service_id=data.get("service_id"),
        slot_start=data.get("slot_iso"),
        description=data.get("description", ""),
        secret_used=data.get("secret_used"),
        discount_percent=data.get("discount", 0)
    )
    
    if appointment_id:
        await callback.message.delete()
        await callback.message.answer(
            "✅ <b>Запись подтверждена!</b>\n\n"
            "Мастер Дина уже готовит эскиз!\n"
            f"📍 {STUDIO_ADDRESS}\n"
            "📞 +7 989 772 5484\n\n"
            "/menu — главное меню",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        for admin_id in ADMIN_IDS:
            try:
                admin_text = (
                    f"📅 Новая запись!\n"
                    f"Пользователь: @{username or 'без юзернейма'}\n"
                    f"Телефон: {data.get('phone')}\n"
                    f"Время: {data.get('slot_iso')}\n"
                    f"Описание: {data.get('description', 'Без описания')}\n"
                    f"Скидка: {data.get('discount', 0)}%"
                )
                await callback.bot.send_message(admin_id, admin_text)
            except:
                pass
    else:
        await callback.message.delete()
        await callback.message.answer(
            "❌ Это время уже занято!\nПопробуй другое /menu",
            reply_markup=get_main_keyboard()
        )
    await callback.answer()
    await state.clear()

@router.callback_query(BookingStates.confirming, F.data == "confirm_no")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "❌ Запись отменена",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# ========== МОИ ЗАПИСИ ==========

@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery):
    user_id = callback.from_user.id
    appointments = await db.get_user_appointments(user_id)
    if not appointments:
        await callback.message.delete()
        await callback.message.answer("📋 Нет записей", reply_markup=get_main_keyboard())
        await callback.answer()
        return
    text = "📋 <b>Твои записи</b>\n\n"
    for app in appointments:
        date_time = app["slot_start"].replace("T", " ")[:16]
        text += f"🕐 {date_time}\n"
        text += f"🎨 {app['service_name']}\n"
        text += f"📞 {app['phone']}\n"
        if app.get('discount_percent', 0) > 0:
            text += f"💰 Скидка: {app['discount_percent']}%\n"
        text += "-" * 20 + "\n"
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=get_cancel_booking_keyboard(appointments[:5]),
        parse_mode="HTML"
    )
    await callback.answer()

# ========== ОТМЕНА ЗАПИСИ ==========

@router.callback_query(F.data.startswith("cancel_"))
async def cancel_booking_app(callback: CallbackQuery):
    appointment_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    appointment = await db.get_appointment_by_id(appointment_id)
    
    success = await db.cancel_appointment(appointment_id, user_id)
    await callback.message.delete()
    
    if success:
        await callback.message.answer("✅ Отменено", reply_markup=get_main_keyboard())
        
        for admin_id in ADMIN_IDS:
            try:
                admin_text = (
                    f"❌ <b>Отмена записи!</b>\n\n"
                    f"Пользователь: @{appointment['username'] or 'без юзернейма'}\n"
                    f"Телефон: {appointment['phone']}\n"
                    f"Время: {appointment['slot_start'].replace('T', ' ')[:16]}\n"
                    f"Услуга: {appointment['service_name']}"
                )
                await callback.bot.send_message(admin_id, admin_text, parse_mode="HTML")
            except:
                pass
    else:
        await callback.message.answer("❌ Ошибка", reply_markup=get_main_keyboard())
    await callback.answer()

# ========== ОТЗЫВЫ ==========

@router.callback_query(F.data == "reviews_menu")
async def reviews_menu(callback: CallbackQuery):
    is_admin = callback.from_user.id in ADMIN_IDS
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Посмотреть", callback_data="show_reviews")
    builder.button(text="✍️ Написать", callback_data="write_review")
    if is_admin:
        builder.button(text="🔨 Модерация", callback_data="moderate_reviews")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    
    await callback.message.delete()
    await callback.message.answer("⭐ <b>Отзывы</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "show_reviews")
async def show_reviews(callback: CallbackQuery):
    reviews = await db.get_approved_reviews(10)
    if not reviews:
        await callback.message.delete()
        await callback.message.answer("😅 Пока нет отзывов", reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    text = "⭐ <b>Отзывы</b>\n\n"
    for rev in reviews:
        stars = "⭐" * rev["rating"]
        text += f"{stars} {rev['rating']}/5\n"
        text += f"{rev['text']}\n"
        text += f"📅 {rev['created_at'][:10]}\n"
        text += "-" * 20 + "\n"
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "write_review")
async def write_review(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if await db.check_user_reviewed(user_id):
        await callback.message.delete()
        await callback.message.answer("😅 Ты уже писал отзыв!", reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    await state.set_state(ReviewStates.rating)
    await callback.message.delete()
    await callback.message.answer(
        "⭐ <b>Оцени нас</b>",
        reply_markup=get_review_rating_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(ReviewStates.rating, F.data.startswith("rating_"))
async def review_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[1])
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.text)
    await callback.message.delete()
    await callback.message.answer(
        f"✍️ <b>Напиши отзыв</b>\n\nОценка: {rating}/5",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ReviewStates.text)
async def review_text(message: Message, state: FSMContext):
    if len(message.text) < 10:
        await message.answer("❌ Минимум 10 символов")
        return
    
    data = await state.get_data()
    rating = data.get("rating", 5)
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    
    await db.add_review(user_id=user_id, username=username, rating=rating, text=message.text)
    await state.clear()
    await message.answer("✅ Спасибо! Отзыв пройдёт модерацию.", reply_markup=get_main_keyboard())
    
    for admin_id in ADMIN_IDS:
        try:
            admin_text = f"📝 Новый отзыв!\n@{username}\nОценка: {rating}/5\nТекст: {message.text}"
            await message.bot.send_message(admin_id, admin_text)
        except:
            pass

# ========== МОДЕРАЦИЯ ОТЗЫВОВ ==========

@router.callback_query(F.data == "moderate_reviews")
async def moderate_reviews(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Только для админа!", show_alert=True)
        return
    
    pending = await db.get_pending_reviews()
    if not pending:
        await callback.message.delete()
        await callback.message.answer("✅ Нет отзывов", reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    await callback.message.delete()
    await callback.message.answer(
        f"📝 Отзывы на модерации ({len(pending)})",
        reply_markup=get_admin_reviews_keyboard(pending[:10]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("review_"))
async def review_detail(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Только для админа!", show_alert=True)
        return
    
    review_id = int(callback.data.split("_")[1])
    pending = await db.get_pending_reviews()
    review = next((r for r in pending if r["id"] == review_id), None)
    
    if not review:
        await callback.message.delete()
        await callback.message.answer("❌ Уже обработано", reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    text = (
        f"📝 Отзыв #{review['id']}\n\n"
        f"Пользователь: @{review['username'] or 'без юзернейма'}\n"
        f"Оценка: {'⭐' * review['rating']} {review['rating']}/5\n"
        f"Текст: {review['text']}"
    )
    
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=get_yes_no_keyboard(review_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def approve_review(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Только для админа!", show_alert=True)
        return
    
    review_id = int(callback.data.split("_")[1])
    success = await db.moderate_review(review_id, "approved")
    await callback.message.delete()
    await callback.message.answer("✅ Одобрено" if success else "❌ Ошибка", reply_markup=get_back_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def reject_review(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Только для админа!", show_alert=True)
        return
    
    review_id = int(callback.data.split("_")[1])
    success = await db.moderate_review(review_id, "rejected")
    await callback.message.delete()
    await callback.message.answer("❌ Отклонено" if success else "❌ Ошибка", reply_markup=get_back_keyboard())
    await callback.answer()

# ========== ВСЕ ЗАПИСИ ==========

@router.callback_query(F.data == "admin_all_bookings")
async def admin_all_bookings(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Только для админа!", show_alert=True)
        return
    
    appointments = await db.get_all_appointments()
    
    if not appointments:
        await callback.message.delete()
        await callback.message.answer(
            "📋 Нет активных записей.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    
    text = "📋 <b>Все записи</b>\n\n"
    for app in appointments:
        date_time = app["slot_start"].replace("T", " ")[:16]
        text += f"🕐 {date_time}\n"
        text += f"🎨 Услуга: {app['service_name']}\n"
        text += f"👤 Пользователь: @{app['username'] or 'без юзернейма'}\n"
        text += f"📞 Телефон: {app['phone']}\n"
        if app.get('description'):
            text += f"✍️ Описание: {app['description'][:50]}...\n"
        if app.get('discount_percent', 0) > 0:
            text += f"💰 Скидка: {app['discount_percent']}%\n"
        text += "-" * 20 + "\n"
    
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ========== ДРУГАЯ ДАТА ==========

@router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext):
    dates = get_available_dates()
    if not dates:
        await callback.message.delete()
        await callback.message.answer(
            "😕 Сейчас нет свободных дат. Попробуй позже!",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    await state.set_state(BookingStates.choosing_date)
    await callback.message.delete()
    await callback.message.answer(
        "📅 <b>Выбери дату</b>\n\nРаботаем только ПН-ЧТ с 18:00 до 22:00.",
        reply_markup=get_dates_keyboard(dates),
        parse_mode="HTML"
    )
    await callback.answer()