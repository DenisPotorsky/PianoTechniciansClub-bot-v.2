import sys
import asyncio
from app.bot import PianoMasterBot
from utils.logger import setup_logger

logger = setup_logger()

async def main():
    """Точка входа в приложение"""
    try:
        bot = PianoMasterBot()
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())