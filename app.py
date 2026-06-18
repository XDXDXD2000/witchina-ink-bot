from flask import Flask
import threading
import os
import asyncio
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
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)