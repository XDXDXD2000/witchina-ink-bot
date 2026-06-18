import asyncio
import logging
import sys
from main import main

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Бот 'Витчина INK' запускается...")
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()