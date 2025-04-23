from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import QUEST_ID_PREFIX, SUBMISSION_ID_PREFIX

def get_approval_keyboard(submission_id: str):
    """
    Returns the keyboard for approving/denying submissions
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{submission_id}"),
            InlineKeyboardButton("❌ Deny", callback_data=f"deny_{submission_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quest_list_keyboard(quests: list):
    """
    Returns a keyboard with a list of active quests
    """
    keyboard = []
    for quest in quests:
        keyboard.append([InlineKeyboardButton(
            f"{quest.title} ({quest.id})",
            callback_data=f"view_quest_{quest.id}"
        )])
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard(is_admin: bool = False):
    """
    Returns the main menu keyboard
    """
    keyboard = [
        [InlineKeyboardButton("View Active Quests", callback_data="view_quests")],
        [InlineKeyboardButton("My Submissions", callback_data="my_submissions")]
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("Create New Quest", callback_data="create_quest")])
    
    return InlineKeyboardMarkup(keyboard)

def get_quest_keyboard(quest_id: int, step: int):
    """
    Returns the keyboard for quest navigation
    """
    keyboard = [
        [InlineKeyboardButton("Next Step", callback_data=f"quest_{quest_id}_step_{step + 1}")],
        [InlineKeyboardButton("Main Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard) 