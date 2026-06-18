import asyncio
from main import main

if __name__ == "__main__":
    print("🚀 Бот 'Витчина INK' запускается...")
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Ошибка: {e}")