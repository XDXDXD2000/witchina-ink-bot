import os
import threading
import asyncio
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
    asyncio.run(main())

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Запускаем веб-сервер
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)