import asyncio
import logging
from telegram import Update
from telegram.ext import Application

from config import BOT_TOKEN, DEBUG
from bot.handlers import setup_handlers
from bot.middlewares import setup_logging
from database.supabase import test_connection

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

async def main():
    """Start the bot"""
    application = None
    try:
        # Test Supabase connection
        if not await test_connection():
            logger.error("Failed to connect to Supabase. Exiting...")
            return
        
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        setup_handlers(application)
        
        # Start the bot
        logger.info("Starting bot...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Keep the bot running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")
    finally:
        if application and application.updater:
            try:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
            except Exception as e:
                logger.error(f"Error during application shutdown: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}") 