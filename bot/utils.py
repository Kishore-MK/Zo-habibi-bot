from telegram import Update, Message
from telegram.ext import ContextTypes
from database.models import Quest, Submission
from config import QUEST_ID_PREFIX
import re
from typing import Optional

async def send_quest_message(update: Update, quest: Quest):
    """Send a quest message with proper formatting"""
    message = await format_quest_message(quest)
    
    if quest.image_url:
        await update.message.reply_photo(
            photo=quest.image_url,
            caption=message,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )

async def format_quest_message(quest: Quest) -> str:
    """Format a quest message for display"""
    message = f"🎯 *{quest.title}*\n\n"
    message += f"🔑 Code: `{quest.quest_code}`\n"
    message += f"⭐ Points: {quest.points}\n\n"
    message += f"📝 {quest.description}\n\n"
    
    if quest.deadline:
        message += f"⏰ Deadline: {quest.deadline.strftime('%Y-%m-%d %H:%M')}\n"
    
    return message

async def format_submission_message(submission: Submission) -> str:
    """Format a submission message for display"""
    message = f"📝 *Submission*\n\n"
    message += f"User: {submission.user_id}\n"
    message += f"Quest: {submission.quest.title} ({submission.quest.quest_code})\n\n"
    message += f"Submission:\n{submission.submission_text}\n\n"
    
    if submission.submission_media:
        message += "📎 Attachments:\n"
        for media in submission.submission_media:
            message += f"- {media}\n"
    
    return message

async def extract_quest_code(text: str) -> Optional[str]:
    """Extract quest code from text"""
    # Look for code in format: QUEST123 or #QUEST123
    match = re.search(r'(?:#)?([A-Z0-9]{3,})', text)
    return match.group(1) if match else None 