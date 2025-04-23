import logging
from telegram import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database.models import User, Quest, Submission, LeaderboardEntry
from database.supabase import get_client
from .keyboards import get_main_keyboard, get_approval_keyboard, get_quest_list_keyboard
from config import ADMIN_GROUP_ID, USER_GROUP_ID
from .utils import send_quest_message, format_quest_message, format_submission_message, extract_quest_code
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    logger.info(f"Start command from user {update.effective_user.id}")
    user = await User.get_or_create(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
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
        "- Submit quests with their code\n"
        "- Track your submissions and points\n\n"
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
        parts = update.message.text.split('\n', 3)
        if len(parts) >= 3:
            title = parts[0].strip()
            description = parts[1].strip()
            quest_code = parts[2].strip()
            
            # Check for deadline in the format "Deadline: YYYY-MM-DD HH:MM"
            deadline = None
            points = 10  # Default points
            if len(parts) > 3:
                for line in parts[3:]:
                    if line.startswith('Deadline:'):
                        try:
                            deadline_str = line.replace('Deadline:', '').strip()
                            deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M')
                        except ValueError:
                            await update.message.reply_text(
                                "Invalid deadline format. Please use: Deadline: YYYY-MM-DD HH:MM"
                            )
                            return
                    elif line.startswith('Points:'):
                        try:
                            points = int(line.replace('Points:', '').strip())
                        except ValueError:
                            await update.message.reply_text(
                                "Invalid points format. Please use: Points: [number]"
                            )
                            return
            
            # Store pending quest
            context.user_data['pending_quest'] = {
                'title': title,
                'description': description,
                'quest_code': quest_code,
                'deadline': deadline,
                'points': points
            }
            
            # Get image if attached
            if update.message.photo:
                # Get the largest photo
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                image_url = file.file_path
                context.user_data['pending_quest']['image_url'] = image_url
            
            # Send confirmation message
            message = f"Create new quest?\n\nTitle: {title}\nDescription: {description}\nCode: {quest_code}\nPoints: {points}"
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
                "Quest Code\n"
                "Deadline: YYYY-MM-DD HH:MM (optional)\n"
                "Points: [number] (optional, default 10)\n\n"
                "You can also attach an image to the message."
            )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in the user group for quest submissions"""
    if update.effective_chat.id != USER_GROUP_ID:
        return
    
    message_text = update.message.text
    logger.info(f"User message from {update.effective_user.id}: {message_text}")
    
    # Check if message contains a quest code
    quest_code = await extract_quest_code(message_text)
    if quest_code:
        quest = await Quest.get_by_code(quest_code)
        
        if quest:
            logger.info(f"Creating submission for quest {quest_code} by user {update.effective_user.id}")
            # Create submission
            submission = await Submission.create(
                quest_id=quest.id,
                user_id=update.effective_user.id,
                submission_text=message_text,
                original_message_id=update.message.message_id
            )
            
            # Forward to admin group with approval buttons
            forwarded_msg = await context.bot.forward_message(
                chat_id=ADMIN_GROUP_ID,
                from_chat_id=USER_GROUP_ID,
                message_id=update.message.message_id
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=f"New submission for quest {quest.title} ({quest.quest_code})",
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
            # Ensure admin user exists
            admin = await User.get_or_create(
                telegram_id=query.from_user.id,
                username=query.from_user.username,
                first_name=query.from_user.first_name,
                last_name=query.from_user.last_name,
                is_admin=True
            )
            
            # Get image URL if available
            image_url = pending_quest.get('image_url')
            
            # Create the quest in Supabase
            quest = await Quest.create(
                title=pending_quest['title'],
                description=pending_quest['description'],
                quest_code=pending_quest['quest_code'],
                image_url=image_url,
                deadline=pending_quest['deadline'],
                points=pending_quest['points'],
                created_by=admin.telegram_id
            )
            
            # Send confirmation with image if available
            if image_url:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=image_url,
                    caption=f"Quest created successfully!\n\n"
                           f"Title: {quest.title}\n"
                           f"Code: {quest.quest_code}\n"
                           f"Points: {quest.points}\n"
                           f"Description: {quest.description}",
                    reply_markup=get_main_keyboard(is_admin=True)
                )
            else:
                await query.message.edit_text(
                    f"Quest created successfully!\n\n"
                    f"Title: {quest.title}\n"
                    f"Code: {quest.quest_code}\n"
                    f"Points: {quest.points}\n"
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
        quests = await Quest.get_active()
        
        if quests:
            # Send each quest with its image if available
            for quest in quests:
                if quest.image_url:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=quest.image_url,
                        caption=f"Title: {quest.title}\n"
                               f"Code: {quest.quest_code}\n"
                               f"Points: {quest.points}\n"
                               f"Description: {quest.description}",
                        reply_markup=get_quest_list_keyboard([quest])
                    )
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"Title: {quest.title}\n"
                             f"Code: {quest.quest_code}\n"
                             f"Points: {quest.points}\n"
                             f"Description: {quest.description}",
                        reply_markup=get_quest_list_keyboard([quest])
                    )
        else:
            await query.message.edit_text(
                "No active quests found.",
                reply_markup=get_main_keyboard(is_admin=True)
            )
    
    elif query.data.startswith("approve_"):
        submission_id = uuid.UUID(query.data.split("_")[1])
        submission = await Submission.get_by_id(submission_id)
        if submission:
            logger.info(f"Approving submission {submission_id} by admin {query.from_user.id}")
            await submission.update_status("approved", query.from_user.id)
            await context.bot.send_message(
                chat_id=submission.user_id,
                text=f"Your submission for quest {submission.quest_id} has been approved! 🎉\n"
                     f"You earned {submission.quest.points} points!"
            )
            await query.message.edit_text("Submission approved!")
    
    elif query.data.startswith("deny_"):
        submission_id = uuid.UUID(query.data.split("_")[1])
        submission = await Submission.get_by_id(submission_id)
        if submission:
            logger.info(f"Denying submission {submission_id} by admin {query.from_user.id}")
            await submission.update_status("denied", query.from_user.id)
            await context.bot.send_message(
                chat_id=submission.user_id,
                text=f"Your submission for quest {submission.quest_id} has been denied. Please try again!"
            )
            await query.message.edit_text("Submission denied.")

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