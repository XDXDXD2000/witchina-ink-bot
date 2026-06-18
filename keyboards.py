from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записаться на тату", callback_data="book_start")
    builder.button(text="💰 Прайс-лист", callback_data="prices")
    builder.button(text="📋 Мои записи", callback_data="my_bookings")
    builder.button(text="🎨 Рандомный эскиз", callback_data="random_sketch")
    builder.button(text="📌 Pinterest", callback_data="pinterest")
    builder.button(text="⭐ Отзывы", callback_data="reviews_menu")
    builder.button(text="📍 Контакты и адрес", callback_data="contacts")
    builder.button(text="ℹ️ О салоне", callback_data="about")
    builder.button(text="🤖 О боте", callback_data="about_bot")
    builder.adjust(1)
    return builder.as_markup()

def get_services_keyboard(services):
    builder = InlineKeyboardBuilder()
    for service in services:
        price_str = f"{service.price} руб." if service.price > 0 else "БЕСПЛАТНО"
        builder.button(
            text=f"{service.name} ({service.duration_minutes} мин, {price_str})",
            callback_data=f"service_{service.id}"
        )
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_dates_keyboard(available_dates):
    builder = InlineKeyboardBuilder()
    for date_str, weekday in available_dates:
        builder.button(
            text=f"{weekday}, {date_str}",
            callback_data=f"date_{date_str}"
        )
    builder.button(text="🔙 Назад", callback_data="back_to_services")
    builder.adjust(2)
    return builder.as_markup()

def get_time_keyboard(time_slots):
    builder = InlineKeyboardBuilder()
    for slot in time_slots:
        builder.button(text=f"{slot}", callback_data=f"time_{slot}")
    if not time_slots:
        builder.button(text="❌ Нет свободных слотов", callback_data="no_slots")
    builder.button(text="🔙 Другая дата", callback_data="back_to_dates")
    builder.adjust(3)
    return builder.as_markup()

def get_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_yes")
    builder.button(text="❌ Отменить", callback_data="confirm_no")
    builder.adjust(2)
    return builder.as_markup()

def get_cancel_booking_keyboard(appointments):
    builder = InlineKeyboardBuilder()
    for app in appointments:
        date_time = app["slot_start"].replace("T", " ")[:16]
        builder.button(
            text=f"❌ {date_time} - {app['service_name']}",
            callback_data=f"cancel_{app['id']}"
        )
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_review_rating_keyboard():
    builder = InlineKeyboardBuilder()
    emojis = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
    for i in range(1, 6):
        builder.button(text=emojis[i-1], callback_data=f"rating_{i}")
    builder.adjust(5)
    return builder.as_markup()

def get_admin_reviews_keyboard(reviews):
    builder = InlineKeyboardBuilder()
    for review in reviews:
        text = review["text"][:30] + "..." if len(review["text"]) > 30 else review["text"]
        builder.button(
            text=f"📝 {text}",
            callback_data=f"review_{review['id']}"
        )
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_yes_no_keyboard(review_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"approve_{review_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_{review_id}")
    builder.adjust(2)
    return builder.as_markup()

def get_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    return builder.as_markup()
def get_admin_main_keyboard():

    """Клавиатура для админа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Рассылка", callback_data="admin_mailing")
    builder.button(text="⭐ Модерация отзывов", callback_data="moderate_reviews")
    builder.button(text="📋 Все записи", callback_data="admin_all_bookings")
    builder.button(text="🔙 В главное меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()