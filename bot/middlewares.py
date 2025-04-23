import logging
from telegram import Update
from telegram.ext import ContextTypes
from functools import partial

logger = logging.getLogger(__name__)

class LoggingMiddleware:
    """Middleware for logging bot interactions"""
    
    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Log incoming updates"""
        if update.message:
            logger.info(
                f"Message from {update.effective_user.id} ({update.effective_user.username}): {update.message.text}"
            )
        elif update.callback_query:
            logger.info(
                f"Callback from {update.effective_user.id} ({update.effective_user.username}): {update.callback_query.data}"
            )
        return True

def setup_middlewares(application):
    """Setup all middlewares"""
    application.middleware.append(LoggingMiddleware())

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    ) 