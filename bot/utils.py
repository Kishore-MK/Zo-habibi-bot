from telegram import Update
from telegram.ext import ContextTypes
from database.models import Quest, QuestSubmission
from config import QUEST_ID_PREFIX

async def send_quest_message(update: Update, context: ContextTypes.DEFAULT_TYPE, quest: Quest, step: int):
    """
    Sends a quest step message to the user
    """
    if step < len(quest.steps):
        step_data = quest.steps[step]
        await update.callback_query.message.edit_text(
            f"Quest: {quest.title}\n\nStep {step + 1}: {step_data['description']}",
            reply_markup=get_quest_keyboard(quest.id, step)
        )
    else:
        await update.callback_query.message.edit_text(
            f"Congratulations! You've completed the quest: {quest.title}",
            reply_markup=get_main_keyboard()
        )

async def format_quest_message(quest: Quest) -> str:
    """Format a quest message for display"""
    return (
        f"Quest: {quest.title}\n"
        f"ID: {quest.id}\n"
        f"Description: {quest.description}\n"
        f"Status: {quest.status}"
    )

async def format_submission_message(submission: QuestSubmission) -> str:
    """Format a submission message for display"""
    return (
        f"Submission ID: {submission.id}\n"
        f"Quest ID: {submission.quest_id}\n"
        f"Status: {submission.status}\n"
        f"Submitted at: {submission.submitted_at}"
    )

async def extract_quest_id(text: str) -> str:
    """Extract quest ID from message text"""
    if QUEST_ID_PREFIX in text:
        parts = text.split(QUEST_ID_PREFIX)
        if len(parts) > 1:
            quest_id = parts[1].split()[0]
            return f"{QUEST_ID_PREFIX}{quest_id}"
    return None 