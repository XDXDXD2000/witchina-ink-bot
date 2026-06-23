import os
import asyncio
import threading
from flask import Flask
from main import main

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот 'Витчина INK' работает!"

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    # Создаём новый event loop в потоке
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)