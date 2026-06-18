import os
import sys
import logging
import asyncio
from flask import Flask

# Настройка логов для Render
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

logger.info("🚀 Starting application...")

# Проверяем файлы
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Files in directory: {os.listdir('.')}")

# Проверяем переменные окружения
logger.info(f"BOT_TOKEN exists: {bool(os.getenv('BOT_TOKEN'))}")
logger.info(f"ADMIN_ID: {os.getenv('ADMIN_ID', 'NOT SET')}")
logger.info(f"PORT: {os.getenv('PORT', 'NOT SET')}")

# Создаём папки
os.makedirs("sketches", exist_ok=True)
os.makedirs("stydiya", exist_ok=True)

app = Flask(__name__)

@app.route('/')
def home():
    logger.info("Home endpoint called")
    return "Бот 'Витчина INK' работает!"

@app.route('/health')
def health():
    logger.info("Health check called")
    return "OK", 200

@app.route('/debug')
def debug():
    """Отладочная страница"""
    info = {
        "status": "running",
        "files": os.listdir('.'),
        "env": {
            "BOT_TOKEN": "SET" if os.getenv('BOT_TOKEN') else "NOT SET",
            "ADMIN_ID": os.getenv('ADMIN_ID', "NOT SET"),
            "PORT": os.getenv('PORT', "NOT SET")
        }
    }
    return str(info)

if __name__ == "__main__":
    logger.info("📦 Starting main.py...")
    
    try:
        # Импортируем main
        from main import main
        logger.info("✅ Main imported successfully")
        
        # Запускаем бота в отдельном потоке
        import threading
        def run_bot():
            try:
                logger.info("🤖 Starting bot...")
                asyncio.run(main())
            except Exception as e:
                logger.error(f"Bot error: {e}")
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        logger.info("✅ Bot thread started")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Запускаем веб-сервер
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🌐 Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)