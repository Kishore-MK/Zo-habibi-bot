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

def main():
    """Start the bot"""
    # Test Supabase connection
    if not asyncio.run(test_connection()):
        logger.error("Failed to connect to Supabase. Exiting...")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup handlers
    setup_handlers(application)
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}") 