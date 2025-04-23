import logging
from telegram import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database.models import User, Quest, UserProgress, QuestSubmission
from database.supabase import get_client
from .keyboards import get_main_keyboard, get_approval_keyboard, get_quest_list_keyboard
from config import ADMIN_GROUP_ID, USER_GROUP_ID, QUEST_ID_PREFIX
from .utils import send_quest_message, format_quest_message, format_submission_message, extract_quest_id
from datetime import datetime

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    logger.info(f"Start command from user {update.effective_user.id}")
    user = await User.get_or_create(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username
    )
    
    is_admin = update.effective_chat.id == ADMIN_GROUP_ID
    await update.message.reply_text(
        "Welcome to the Quest Bot! Choose an option:",
        reply_markup=get_main_keyboard(is_admin)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    logger.info(f"Help command from user {update.effective_user.id}")
    is_admin = update.effective_chat.id == ADMIN_GROUP_ID
    help_text = (
        "This bot manages quests between admins and users.\n\n"
        "For Users:\n"
        "- View active quests\n"
        "- Submit quests with their ID\n"
        "- Track your submissions\n\n"
        "For Admins:\n"
        "- Create new quests\n"
        "- Review submissions\n"
        "- Approve/deny submissions"
    )
    await update.message.reply_text(help_text, reply_markup=get_main_keyboard(is_admin))

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages from admin group"""
    if update.message.chat_id != ADMIN_GROUP_ID:
        return
    
    # Check if message contains a quest
    if update.message.text:
        # Parse quest details
        parts = update.message.text.split('\n', 2)
        if len(parts) >= 2:
            title = parts[0].strip()
            description = parts[1].strip()
            
            # Check for deadline in the format "Deadline: YYYY-MM-DD HH:MM"
            deadline = None
            if len(parts) > 2:
                deadline_text = parts[2].strip()
                if deadline_text.startswith('Deadline:'):
                    try:
                        deadline_str = deadline_text.replace('Deadline:', '').strip()
                        deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        await update.message.reply_text(
                            "Invalid deadline format. Please use: Deadline: YYYY-MM-DD HH:MM"
                        )
                        return
            
            # Store pending quest
            context.user_data['pending_quest'] = {
                'title': title,
                'description': description,
                'deadline': deadline
            }
            
            # Get image if attached
            if update.message.photo:
                # Get the largest photo
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                image_url = file.file_path
                context.user_data['pending_quest']['image_url'] = image_url
            
            # Send confirmation message
            message = f"Create new quest?\n\nTitle: {title}\nDescription: {description}"
            if deadline:
                message += f"\nDeadline: {deadline.strftime('%Y-%m-%d %H:%M')}"
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Yes", callback_data="confirm_quest"),
                        InlineKeyboardButton("No", callback_data="cancel_quest")
                    ]
                ])
            )
        else:
            await update.message.reply_text(
                "Please provide quest details in the format:\n"
                "Title\n"
                "Description\n"
                "Deadline: YYYY-MM-DD HH:MM (optional)\n\n"
                "You can also attach an image to the message."
            )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in the user group for quest submissions"""
    if update.effective_chat.id != USER_GROUP_ID:
        return
    
    message_text = update.message.text
    logger.info(f"User message from {update.effective_user.id}: {message_text}")
    
    # Check if message contains a quest ID
    quest_id = await extract_quest_id(message_text)
    if quest_id:
        quest = await Quest.get_quest(quest_id)
        
        if quest:
            logger.info(f"Creating submission for quest {quest_id} by user {update.effective_user.id}")
            # Create submission
            submission = await QuestSubmission.create(
                quest_id=quest.id,
                user_id=update.effective_user.id,
                submission_text=message_text
            )
            
            # Forward to admin group with approval buttons
            forwarded_msg = await context.bot.forward_message(
                chat_id=ADMIN_GROUP_ID,
                from_chat_id=USER_GROUP_ID,
                message_id=update.message.message_id
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"New submission for quest {quest.title} ({quest.id})",
                reply_to_message_id=forwarded_msg.message_id,
                reply_markup=get_approval_keyboard(submission.id)
            )
            
            await update.message.reply_text("Your submission has been sent for review!")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    logger.info(f"Callback from {update.effective_user.id}: {query.data}")
    await query.answer()
    
    if query.data == "confirm_quest":
        # Get the pending quest from context
        pending_quest = context.user_data.get('pending_quest')
        if pending_quest:
            # Get image URL if available
            image_url = None
            if pending_quest.get('image_url'):
                image_url = pending_quest['image_url']
            
            # Create the quest in Supabase
            quest = await Quest.create(
                title=pending_quest['title'],
                description=pending_quest['description'],
                created_by=query.from_user.id,
                image_url=image_url
            )
            
            # Send confirmation with image if available
            if image_url:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=image_url,
                    caption=f"Quest created successfully!\n\n"
                           f"Title: {quest.title}\n"
                           f"ID: {quest.id}\n"
                           f"Description: {quest.description}",
                    reply_markup=get_main_keyboard(is_admin=True)
                )
            else:
                await query.message.edit_text(
                    f"Quest created successfully!\n\n"
                    f"Title: {quest.title}\n"
                    f"ID: {quest.id}\n"
                    f"Description: {quest.description}",
                    reply_markup=get_main_keyboard(is_admin=True)
                )
            context.user_data.pop('pending_quest', None)
        else:
            await query.message.edit_text(
                "No pending quest found. Please try creating a quest again.",
                reply_markup=get_main_keyboard(is_admin=True)
            )
    
    elif query.data == "cancel_quest":
        context.user_data.pop('pending_quest', None)
        await query.message.edit_text(
            "Quest creation cancelled.",
            reply_markup=get_main_keyboard(is_admin=True)
        )
    
    elif query.data == "view_quests":
        # Get active quests
        client = get_client()
        quests = client.table('quests').select('*').eq('status', 'active').execute()
        
        if quests.data:
            # Send each quest with its image if available
            for quest in quests.data:
                quest_obj = Quest(**quest)
                if quest_obj.image_url:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=quest_obj.image_url,
                        caption=f"Title: {quest_obj.title}\n"
                               f"ID: {quest_obj.id}\n"
                               f"Description: {quest_obj.description}",
                        reply_markup=get_quest_list_keyboard([quest_obj])
                    )
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"Title: {quest_obj.title}\n"
                             f"ID: {quest_obj.id}\n"
                             f"Description: {quest_obj.description}",
                        reply_markup=get_quest_list_keyboard([quest_obj])
                    )
        else:
            await query.message.edit_text(
                "No active quests found.",
                reply_markup=get_main_keyboard(is_admin=True)
            )
    
    elif query.data.startswith("approve_"):
        submission_id = query.data.split("_")[1]
        submission = await QuestSubmission.get_submission(submission_id)
        if submission:
            logger.info(f"Approving submission {submission_id} by admin {query.from_user.id}")
            await submission.update_status("approved", query.from_user.id)
            await context.bot.send_message(
                chat_id=submission.user_id,
                text=f"Your submission for quest {submission.quest_id} has been approved! 🎉"
            )
            await query.message.edit_text("Submission approved!")
    
    elif query.data.startswith("deny_"):
        submission_id = query.data.split("_")[1]
        submission = await QuestSubmission.get_submission(submission_id)
        if submission:
            logger.info(f"Denying submission {submission_id} by admin {query.from_user.id}")
            await submission.update_status("denied", query.from_user.id)
            await context.bot.send_message(
                chat_id=submission.user_id,
                text=f"Your submission for quest {submission.quest_id} has been denied. Please try again!"
            )
            await query.message.edit_text("Submission denied.")
    
    elif query.data == "create_quest":
        await query.message.edit_text(
            "Please send the quest details in the following format:\n"
            "Title: [Quest Title]\n"
            "Description: [Quest Description]\n\n"
            "You can also attach an image to the quest."
        )
        context.user_data['awaiting_quest'] = True

def setup_handlers(application):
    """Setup all handlers"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add message handlers for admin and user groups
    application.add_handler(MessageHandler(
        filters.Chat(ADMIN_GROUP_ID) & filters.TEXT & ~filters.COMMAND,
        handle_admin_message
    ))
    application.add_handler(MessageHandler(
        filters.Chat(USER_GROUP_ID) & filters.TEXT & ~filters.COMMAND,
        handle_user_message
    )) 