import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import re

# File to store reminders persistently
REMINDERS_FILE = "reminders.json"

class ReminderBot:
    def __init__(self):
        self.reminders = self.load_reminders()
    
    def load_reminders(self):
        """Load reminders from file"""
        if os.path.exists(REMINDERS_FILE):
            try:
                with open(REMINDERS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_reminders(self):
        """Save reminders to file"""
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(self.reminders, f)
    
    def add_reminder(self, chat_id, message, remind_time):
        """Add a new reminder"""
        reminder_id = f"{chat_id}_{remind_time.timestamp()}"
        self.reminders[reminder_id] = {
            'chat_id': chat_id,
            'message': message,
            'time': remind_time.isoformat()
        }
        self.save_reminders()
        return reminder_id
    
    def get_user_reminders(self, chat_id):
        """Get all reminders for a user"""
        return {k: v for k, v in self.reminders.items() if v['chat_id'] == chat_id}
    
    def delete_reminder(self, reminder_id):
        """Delete a reminder"""
        if reminder_id in self.reminders:
            del self.reminders[reminder_id]
            self.save_reminders()
            return True
        return False

bot_instance = ReminderBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = (
        "🔔 *Welcome to MemoryPing!*\n\n"
        "I'll help you remember important things!\n\n"
        "*How to use:*\n"
        "Just talk naturally! I understand casual language.\n\n"
        "*Examples:*\n"
        "• Remind me to call mom at 5:30pm\n"
        "• Send me a hey in 2 minutes\n"
        "• Tell me to take medicine at 2pm\n"
        "• Ping me about meeting in 1 hour\n"
        "• Remember to workout at 6am tomorrow\n\n"
        "*Commands:*\n"
        "/start - Show this message\n"
        "/list - View all your reminders\n"
        "/help - Get help\n\n"
        "_Created by Achu Vijayakumar_ ✨"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "🔔 *MemoryPing Help*\n\n"
        "*I understand natural language!*\n"
        "Just talk to me like you would to a friend.\n\n"
        "*Supported time formats:*\n"
        "• `at 5:30pm` or `at 17:30`\n"
        "• `at 9am tomorrow`\n"
        "• `in 30 minutes` or `in 30 mins`\n"
        "• `in 2 hours`\n"
        "• `in 1 hour 30 minutes`\n"
        "• `after 5 mins`\n\n"
        "*Ways to ask:*\n"
        "• Remind me to...\n"
        "• Send me...\n"
        "• Tell me...\n"
        "• Ping me...\n"
        "• Remember...\n"
        "• Alert me...\n\n"
        "*Examples:*\n"
        "• Send me a hey in 5 minutes\n"
        "• Remind me to buy groceries at 6pm\n"
        "• Tell me to call John after 1 hour\n"
        "• Ping me about meeting at 2:30pm tomorrow\n\n"
        "_Created by Achu Vijayakumar_ ✨"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all reminders for the user"""
    chat_id = update.effective_chat.id
    reminders = bot_instance.get_user_reminders(chat_id)
    
    if not reminders:
        await update.message.reply_text("📭 You have no active reminders.\n\n_Created by Achu Vijayakumar_ ✨", parse_mode='Markdown')
        return
    
    message = "📋 *Your Reminders:*\n\n"
    keyboard = []
    
    for idx, (reminder_id, reminder) in enumerate(sorted(reminders.items(), key=lambda x: x[1]['time']), 1):
        remind_time = datetime.fromisoformat(reminder['time'])
        message += f"{idx}. {reminder['message']}\n   ⏰ {remind_time.strftime('%I:%M %p, %b %d')}\n\n"
        keyboard.append([InlineKeyboardButton(f"❌ Delete #{idx}", callback_data=f"delete_{reminder_id}")])
    
    message += "_Created by Achu Vijayakumar_ ✨"
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

def parse_time(time_str, current_time):
    """Parse various time formats"""
    time_str = time_str.lower().strip()
    
    # Check for "tomorrow"
    is_tomorrow = "tomorrow" in time_str
    time_str = time_str.replace("tomorrow", "").strip()
    
    # Parse "in/after X minutes/hours" format - supports variations
    # Matches: in 30 minutes, in 30 mins, in 30min, after 2 hours, in 1 hour 30 minutes, etc.
    in_pattern = r'(?:in|after)\s+(?:(\d+)\s*(?:hours?|hrs?|h)\s*)?(?:(\d+)\s*(?:minutes?|mins?|min|m))?'
    in_match = re.search(in_pattern, time_str)
    if in_match and (in_match.group(1) or in_match.group(2)):
        hours = int(in_match.group(1)) if in_match.group(1) else 0
        minutes = int(in_match.group(2)) if in_match.group(2) else 0
        return current_time + timedelta(hours=hours, minutes=minutes)
    
    # Parse "at HH:MM" format (24-hour)
    at_pattern = r'at\s+(\d{1,2}):(\d{2})'
    at_match = re.search(at_pattern, time_str)
    if at_match:
        hour = int(at_match.group(1))
        minute = int(at_match.group(2))
        remind_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if is_tomorrow:
            remind_time += timedelta(days=1)
        elif remind_time <= current_time:
            remind_time += timedelta(days=1)
        
        return remind_time
    
    # Parse "at H:MMam/pm" or "at Ham/pm" format
    at_pattern_ampm = r'at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)'
    at_match_ampm = re.search(at_pattern_ampm, time_str)
    if at_match_ampm:
        hour = int(at_match_ampm.group(1))
        minute = int(at_match_ampm.group(2)) if at_match_ampm.group(2) else 0
        period = at_match_ampm.group(3)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        remind_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if is_tomorrow:
            remind_time += timedelta(days=1)
        elif remind_time <= current_time:
            remind_time += timedelta(days=1)
        
        return remind_time
    
    return None

def extract_task_and_time(text):
    """Extract task and time from casual natural language"""
    text = text.strip()
    text_lower = text.lower()
    
    # Common trigger phrases for reminders (more casual variations)
    trigger_patterns = [
        r'remind\s+me\s+to\s+',
        r'send\s+me\s+(?:a\s+)?',
        r'tell\s+me\s+(?:to\s+)?',
        r'ping\s+me\s+(?:about\s+|to\s+)?',
        r'alert\s+me\s+(?:about\s+|to\s+)?',
        r'remember\s+(?:to\s+)?',
        r'notify\s+me\s+(?:about\s+|to\s+)?',
    ]
    
    # Time indicator patterns (at, in, after)
    time_patterns = [
        r'\s+(?:at|in|after)\s+',
    ]
    
    # Try to find trigger and time indicator
    for trigger in trigger_patterns:
        trigger_match = re.search(trigger, text_lower)
        if trigger_match:
            # Get text after trigger
            after_trigger = text[trigger_match.end():]
            after_trigger_lower = after_trigger.lower()
            
            # Find time indicator
            for time_pattern in time_patterns:
                time_match = re.search(time_pattern, after_trigger_lower)
                if time_match:
                    # Task is between trigger and time indicator
                    task = after_trigger[:time_match.start()].strip()
                    # Time is from time indicator onwards
                    time_str = after_trigger[time_match.start():].strip()
                    return task, time_str
    
    # Fallback: Try to split by common time indicators without trigger phrases
    for time_pattern in time_patterns:
        time_match = re.search(time_pattern, text_lower)
        if time_match:
            task = text[:time_match.start()].strip()
            time_str = text[time_match.start():].strip()
            if task:  # Make sure we have a task
                return task, time_str
    
    return None, None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages with natural language understanding"""
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Extract task and time from the message
    task, time_str = extract_task_and_time(text)
    
    if not task or not time_str:
        await update.message.reply_text(
            "❌ I couldn't understand that.\n\n"
            "Try something like:\n"
            "• Remind me to call mom at 5pm\n"
            "• Send me a hey in 2 minutes\n"
            "• Tell me to workout at 6am tomorrow\n\n"
            "_Created by Achu Vijayakumar_ ✨",
            parse_mode='Markdown'
        )
        return
    
    current_time = datetime.now()
    remind_time = parse_time(time_str, current_time)
    
    if not remind_time:
        await update.message.reply_text(
            "❌ I couldn't understand that time format.\n\n"
            "Try formats like:\n"
            "• at 5:30pm\n"
            "• in 30 minutes\n"
            "• at 14:00 tomorrow\n"
            "• after 2 hours\n\n"
            "_Created by Achu Vijayakumar_ ✨",
            parse_mode='Markdown'
        )
        return
    
    if remind_time <= current_time:
        await update.message.reply_text(
            "❌ That time is in the past!\n\n"
            "_Created by Achu Vijayakumar_ ✨",
            parse_mode='Markdown'
        )
        return
    
    # Add reminder
    bot_instance.add_reminder(chat_id, task, remind_time)
    
    # Schedule the reminder
    delay = (remind_time - current_time).total_seconds()
    context.job_queue.run_once(send_reminder, delay, data={'chat_id': chat_id, 'message': task})
    
    time_until = remind_time - current_time
    hours = int(time_until.total_seconds() // 3600)
    minutes = int((time_until.total_seconds() % 3600) // 60)
    
    time_msg = ""
    if hours > 0:
        time_msg += f"{hours} hour{'s' if hours > 1 else ''} "
    if minutes > 0:
        time_msg += f"{minutes} minute{'s' if minutes > 1 else ''}"
    
    await update.message.reply_text(
        f"✅ *Got it!*\n\n"
        f"📝 I'll remind you: {task}\n"
        f"⏰ At: {remind_time.strftime('%I:%M %p, %b %d, %Y')}\n"
        f"⏳ In: {time_msg.strip()}\n\n"
        f"_Created by Achu Vijayakumar_ ✨",
        parse_mode='Markdown'
    )

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send the reminder message"""
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message = job_data['message']
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 *PING!*\n\n{message}\n\n_Created by Achu Vijayakumar_ ✨",
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("delete_"):
        reminder_id = query.data.replace("delete_", "")
        if bot_instance.delete_reminder(reminder_id):
            await query.edit_message_text(
                "✅ Reminder deleted successfully!\n\n_Created by Achu Vijayakumar_ ✨",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ Reminder not found!\n\n_Created by Achu Vijayakumar_ ✨",
                parse_mode='Markdown'
            )

async def reschedule_reminders(application):
    """Reschedule all pending reminders on bot restart"""
    current_time = datetime.now()
    
    for reminder_id, reminder in list(bot_instance.reminders.items()):
        remind_time = datetime.fromisoformat(reminder['time'])
        
        if remind_time > current_time:
            delay = (remind_time - current_time).total_seconds()
            application.job_queue.run_once(
                send_reminder,
                delay,
                data={'chat_id': reminder['chat_id'], 'message': reminder['message']}
            )
        else:
            # Delete expired reminders
            bot_instance.delete_reminder(reminder_id)

def main():
    """Start the bot"""
    # Replace with your actual bot token
    TOKEN = "8435749626:AAFdsDqtjmvvqfF6jOdXpGEc8UO2lsrf39U"
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Reschedule reminders after startup
    application.post_init = reschedule_reminders
    
    # Run the bot
    print("🤖 MemoryPing is running... Created by Achu Vijayakumar")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()