import asyncio
import logging
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, REMIND_HOURS_BEFORE, ADMIN_ID
from db import db
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def send_reminders(bot: Bot):
    while True:
        await asyncio.sleep(60)
        appointments = db.get_appointments_for_reminder(REMIND_HOURS_BEFORE)
        for app in appointments:
            try:
                user_id = app["user_id"]
                slot_time = app["slot_start"].replace("T", " ")[:16]
                message = (
                    f"🔔 НАПОМИНАНИЕ!\n\n"
                    f"Ты записан в «Витчина INK» через {REMIND_HOURS_BEFORE} часа(ов).\n\n"
                    f"🕐 {slot_time}\n"
                    f"🎨 Услуга: {app['service_name']}\n"
                    f"📞 Телефон: {app['phone']}\n"
                    f"📍 Адрес: Московская 158/2"
                )
                await bot.send_message(user_id, message)
                db.mark_reminder_sent(app["id"])
                logger.info(f"Напоминание отправлено для #{app['id']}")
            except Exception as e:
                logger.error(f"Ошибка напоминания: {e}")

async def main():
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    await bot.delete_webhook(drop_pending_updates=True)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    asyncio.create_task(send_reminders(bot))
    logger.info("🚀 Бот «Витчина INK» запущен!")
    try:
        await bot.send_message(ADMIN_ID, "✅ Бот запущен!")
    except:
        pass
    try:
        await dp.start_polling(bot, handle_signals=False)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())