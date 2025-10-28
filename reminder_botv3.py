import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import re
from collections import defaultdict
import random
from threading import Thread
from flask import Flask
import pytz

# Flask app to keep Render service alive
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "MemoryPing Bot is running! ✨ Created by Achu Vijayakumar"

@flask_app.route('/health')
def health():
    return {"status": "alive", "bot": "MemoryPing"}

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# File storage
REMINDERS_FILE = "reminders.json"
USER_DATA_FILE = "user_data.json"
STATS_FILE = "stats.json"

# Default timezone (India)
DEFAULT_TIMEZONE = pytz.timezone('Asia/Kolkata')

class MemoryPingBot:
    def __init__(self):
        self.reminders = self.load_reminders()
        self.user_data = self.load_user_data()
        self.stats = self.load_stats()
        
        self.categories = {
            'work': '💼', 'personal': '👤', 'health': '💊',
            'shopping': '🛒', 'fitness': '💪', 'family': '👨‍👩‍👧',
            'finance': '💰', 'education': '📚', 'other': '📌'
        }
        
        self.priorities = {
            'high': '🔴', 'medium': '🟡', 'low': '🟢'
        }
        
        self.templates = {
            'medicine': {'text': 'Take medicine', 'category': 'health'},
            'water': {'text': 'Drink water', 'category': 'health'},
            'exercise': {'text': 'Time to exercise', 'category': 'fitness'},
            'standup': {'text': 'Stand up and stretch', 'category': 'health'},
            'call_family': {'text': 'Call family', 'category': 'family'},
            'check_email': {'text': 'Check emails', 'category': 'work'}
        }
        
        self.confirmation_messages = [
            "Got it! I'll ping you! 🎯",
            "Consider it done! ✨",
            "I'll remember that for you! 🧠",
            "On it! You can count on me! 💪",
            "Reminder locked in! 🔒",
            "I won't let you forget! 🎪",
            "Noted! I'll buzz you! 🐝",
            "Roger that! 🚀",
            "All set! Time to relax! 😌",
            "Booked! I'm on the clock! ⏰"
        ]
        
        self.completion_messages = [
            "Boom! Task crushed! 💥",
            "You're on fire! 🔥",
            "Nailed it! 🎯",
            "Productivity level: 100! 📈",
            "That's how it's done! 👏",
            "You're unstoppable! 🚀",
            "Keep that momentum! ⚡",
            "Legendary! 🏆",
            "Smooth operator! 😎",
            "Another win! 🌟"
        ]
        
        self.ping_messages = [
            "Hey! Time for this! 👋",
            "Knock knock! Reminder time! 🚪",
            "Yo! Don't forget! 📢",
            "Psst... remember this? 🤫",
            "Beep beep! Task alert! 🤖",
            "Ding ding! It's time! 🔔",
            "Pop! Reminder bubble! 💭",
            "Friendly nudge! 👉",
            "Time to shine! ✨",
            "Wake up call! ⏰"
        ]
        
        self.tips = [
            "💡 Tip: Use #hashtags to organize your reminders!",
            "💡 Pro tip: Add !high for urgent reminders",
            "💡 Did you know? You can add notes with --",
            "💡 Try /quick for instant reminders",
            "💡 Use 'every day' for recurring reminders",
            "💡 Snooze feature: Perfect for that extra 5 minutes!",
            "💡 Share reminders by adding @username",
            "💡 Check your stats with /stats to track progress",
            "🎯 Stay organized with categories",
            "⚡ Quick access via menu buttons below"
        ]
        
        self.achievements = {
            'first_reminder': {'name': '🎬 First Step', 'desc': 'Created first reminder'},
            'streak_3': {'name': '🔥 On Fire', 'desc': '3-day streak'},
            'streak_7': {'name': '⚡ Unstoppable', 'desc': '7-day streak'},
            'streak_30': {'name': '🏆 Legend', 'desc': '30-day streak'},
            'complete_10': {'name': '✨ Achiever', 'desc': 'Completed 10 reminders'},
            'complete_50': {'name': '💎 Diamond', 'desc': 'Completed 50 reminders'},
            'complete_100': {'name': '👑 Master', 'desc': 'Completed 100 reminders'},
            'early_bird': {'name': '🌅 Early Bird', 'desc': 'Set reminder before 7am'},
            'night_owl': {'name': '🦉 Night Owl', 'desc': 'Set reminder after 10pm'},
            'organized': {'name': '🗂️ Organizer', 'desc': 'Used all categories'},
        }
        
        self.message_count = 0
    
    def load_reminders(self):
        if os.path.exists(REMINDERS_FILE):
            try:
                with open(REMINDERS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_reminders(self):
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(self.reminders, f, indent=2)
    
    def load_user_data(self):
        if os.path.exists(USER_DATA_FILE):
            try:
                with open(USER_DATA_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_user_data(self):
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(self.user_data, f, indent=2)
    
    def load_stats(self):
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_stats(self):
        with open(STATS_FILE, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def get_user_language(self, chat_id):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.user_data:
            self.user_data[chat_id_str] = {'language': 'en', 'timezone': 'Asia/Kolkata'}
        return self.user_data[chat_id_str].get('language', 'en')
    
    def get_user_timezone(self, chat_id):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.user_data:
            self.user_data[chat_id_str] = {'language': 'en', 'timezone': 'Asia/Kolkata'}
        tz_name = self.user_data[chat_id_str].get('timezone', 'Asia/Kolkata')
        return pytz.timezone(tz_name)
    
    def get_current_time(self, chat_id):
        """Get current time in user's timezone"""
        tz = self.get_user_timezone(chat_id)
        return datetime.now(tz)
    
    def add_reminder(self, chat_id, message, remind_time, recurring=None, category='other', priority='medium', notes='', shared_with=None):
        reminder_id = f"{chat_id}_{remind_time.timestamp()}_{len(self.reminders)}"
        self.reminders[reminder_id] = {
            'chat_id': chat_id,
            'message': message,
            'time': remind_time.isoformat(),
            'recurring': recurring,
            'category': category,
            'priority': priority,
            'notes': notes,
            'shared_with': shared_with or [],
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        self.save_reminders()
        self.update_stats(chat_id, 'created')
        return reminder_id
    
    def get_user_reminders(self, chat_id, category=None, priority=None):
        reminders = {k: v for k, v in self.reminders.items() 
                    if (v['chat_id'] == chat_id or chat_id in v.get('shared_with', [])) 
                    and not v.get('completed', False)}
        
        if category:
            reminders = {k: v for k, v in reminders.items() if v.get('category') == category}
        if priority:
            reminders = {k: v for k, v in reminders.items() if v.get('priority') == priority}
        
        return reminders
    
    def complete_reminder(self, reminder_id):
        if reminder_id in self.reminders:
            self.reminders[reminder_id]['completed'] = True
            self.save_reminders()
            chat_id = self.reminders[reminder_id]['chat_id']
            self.update_stats(chat_id, 'completed')
            return True
        return False
    
    def delete_reminder(self, reminder_id):
        if reminder_id in self.reminders:
            del self.reminders[reminder_id]
            self.save_reminders()
            return True
        return False
    
    def snooze_reminder(self, reminder_id, minutes):
        if reminder_id in self.reminders:
            current_time = datetime.fromisoformat(self.reminders[reminder_id]['time'])
            new_time = current_time + timedelta(minutes=minutes)
            self.reminders[reminder_id]['time'] = new_time.isoformat()
            self.save_reminders()
            return new_time
        return None
    
    def update_stats(self, chat_id, action):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.stats:
            self.stats[chat_id_str] = {'created': 0, 'completed': 0, 'snoozed': 0}
        self.stats[chat_id_str][action] = self.stats[chat_id_str].get(action, 0) + 1
        self.save_stats()
    
    def get_random_confirmation(self):
        return random.choice(self.confirmation_messages)
    
    def get_random_completion(self):
        return random.choice(self.completion_messages)
    
    def get_random_ping(self):
        return random.choice(self.ping_messages)
    
    def get_random_tip(self):
        return random.choice(self.tips)
    
    def get_footer(self, show_credit=False):
        self.message_count += 1
        if show_credit or self.message_count % 10 == 0:
            return "\n\n_✨ by Achu Vijayakumar_"
        else:
            return f"\n\n{self.get_random_tip()}"
    
    def check_achievements(self, chat_id):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.stats:
            return None
        
        stats = self.stats[chat_id_str]
        if chat_id_str not in self.user_data:
            self.user_data[chat_id_str] = {'achievements': []}
        
        user_achievements = self.user_data[chat_id_str].get('achievements', [])
        new_achievement = None
        
        completed = stats.get('completed', 0)
        
        if completed == 1 and 'first_reminder' not in user_achievements:
            new_achievement = 'first_reminder'
        elif completed == 10 and 'complete_10' not in user_achievements:
            new_achievement = 'complete_10'
        elif completed == 50 and 'complete_50' not in user_achievements:
            new_achievement = 'complete_50'
        elif completed == 100 and 'complete_100' not in user_achievements:
            new_achievement = 'complete_100'
        
        if new_achievement:
            user_achievements.append(new_achievement)
            self.user_data[chat_id_str]['achievements'] = user_achievements
            self.save_user_data()
            return self.achievements[new_achievement]
        
        return None
    
    def check_time_based_achievements(self, chat_id, remind_time):
        """Check for early bird and night owl achievements"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.user_data:
            self.user_data[chat_id_str] = {'achievements': []}
        
        user_achievements = self.user_data[chat_id_str].get('achievements', [])
        
        hour = remind_time.hour
        
        if hour < 7 and 'early_bird' not in user_achievements:
            user_achievements.append('early_bird')
            self.user_data[chat_id_str]['achievements'] = user_achievements
            self.save_user_data()
            return self.achievements['early_bird']
        elif hour >= 22 and 'night_owl' not in user_achievements:
            user_achievements.append('night_owl')
            self.user_data[chat_id_str]['achievements'] = user_achievements
            self.save_user_data()
            return self.achievements['night_owl']
        
        return None
    
    def check_category_achievement(self, chat_id):
        """Check if user has used all categories"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.user_data:
            return None
        
        user_achievements = self.user_data[chat_id_str].get('achievements', [])
        
        if 'organized' in user_achievements:
            return None
        
        # Get all categories used by user
        user_reminders = self.get_user_reminders(chat_id)
        categories_used = set()
        for reminder in user_reminders.values():
            categories_used.add(reminder.get('category', 'other'))
        
        # Check if all categories have been used
        if len(categories_used) >= len(self.categories):
            user_achievements.append('organized')
            self.user_data[chat_id_str]['achievements'] = user_achievements
            self.save_user_data()
            return self.achievements['organized']
        
        return None
    
    def get_streak(self, chat_id):
        chat_id_str = str(chat_id)
        if chat_id_str in self.user_data:
            return self.user_data[chat_id_str].get('streak', 0)
        return 0

bot_instance = MemoryPingBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    keyboard = [
        [KeyboardButton("⚡ Quick Reminders"), KeyboardButton("📋 My Reminders")],
        [KeyboardButton("📊 Statistics"), KeyboardButton("⚙️ Settings")],
        [KeyboardButton("❓ Help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_message = (
        "🔔 *Welcome to MemoryPing!*\n\n"
        "Your personal memory assistant that makes staying organized fun! 🎯\n\n"
        "*Quick Start:*\n"
        "Just tell me what to remind you about!\n\n"
        "*Examples:*\n"
        "• Remind me to call mom at 5pm\n"
        "• Meeting in 30 minutes #work\n"
        "• Take medicine every day at 9am\n\n"
        "*Explore:*\n"
        "Tap the buttons below or send /help\n\n"
        "_Created with ❤️ by Achu Vijayakumar_"
    )
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *MemoryPing - Complete Guide*\n\n"
        "*🎯 Essential Commands:*\n"
        "/start - Main menu\n"
        "/quick - Quick reminders ⚡\n"
        "/list - View all reminders\n"
        "/today - Today's schedule\n"
        "/stats - Your progress\n"
        "/digest - Daily summary\n\n"
        "*🔍 Search & Organization:*\n"
        "/search <keyword> - Find reminders\n"
        "/export - Export all reminders\n"
        "/bulk - Create multiple reminders\n\n"
        "*⏰ Time Management:*\n"
        "/postpone <mins> - Delay reminder\n"
        "/test_time <time> - Test parser\n\n"
        "*💬 Natural Language:*\n"
        "• Remind me to call mom at 5pm\n"
        "• Workout in 30 minutes\n"
        "• Meeting at 2pm tomorrow #work !high\n\n"
        "*🔄 Recurring:*\n"
        "• Medicine every day at 9am\n"
        "• Team standup every Monday at 10am\n\n"
        "*🎨 Organize:*\n"
        "#work #health #family #fitness\n"
        "!high !medium !low\n"
        "-- Add notes after double dash\n\n"
        "_Made with ❤️ by Achu Vijayakumar_"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def quick_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💊 Take Medicine", callback_data="quick_medicine")],
        [InlineKeyboardButton("💧 Drink Water", callback_data="quick_water")],
        [InlineKeyboardButton("💪 Exercise", callback_data="quick_exercise")],
        [InlineKeyboardButton("🧍 Stand & Stretch", callback_data="quick_standup")],
        [InlineKeyboardButton("📞 Call Family", callback_data="quick_call_family")],
        [InlineKeyboardButton("📧 Check Email", callback_data="quick_check_email")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚡ *Quick Reminder Templates*\n\nPick one and set the time!{bot_instance.get_footer()}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    category_filter = None
    if context.args:
        category_filter = context.args[0].lower().replace('#', '')
    
    reminders = bot_instance.get_user_reminders(chat_id, category=category_filter)
    
    if not reminders:
        msg = "📭 No active reminders. You're all clear!"
        if category_filter:
            msg = f"📭 No reminders in #{category_filter}"
        await update.message.reply_text(f"{msg}{bot_instance.get_footer()}", parse_mode='Markdown')
        return
    
    by_category = defaultdict(list)
    for rid, reminder in reminders.items():
        by_category[reminder.get('category', 'other')].append((rid, reminder))
    
    message = "📋 *Your Reminders:*\n\n"
    keyboard = []
    
    idx = 1
    for category, items in sorted(by_category.items()):
        cat_emoji = bot_instance.categories.get(category, '📌')
        message += f"{cat_emoji} *{category.upper()}*\n"
        
        for rid, reminder in sorted(items, key=lambda x: x[1]['time']):
            remind_time = datetime.fromisoformat(reminder['time'])
            priority_emoji = bot_instance.priorities.get(reminder.get('priority', 'medium'), '🟡')
            recurring = f" 🔄 {reminder['recurring']}" if reminder.get('recurring') else ""
            
            message += f"{idx}. {priority_emoji} {reminder['message']}\n"
            message += f"   ⏰ {remind_time.strftime('%I:%M %p, %b %d')}{recurring}\n"
            if reminder.get('notes'):
                message += f"   📝 {reminder['notes'][:30]}...\n"
            message += "\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ Done #{idx}", callback_data=f"complete_{rid}"),
                InlineKeyboardButton(f"❌ Delete #{idx}", callback_data=f"delete_{rid}")
            ])
            idx += 1
    
    message += bot_instance.get_footer()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if len(message) > 4000:
        parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for part in parts[:-1]:
            await update.message.reply_text(part, parse_mode='Markdown')
        await update.message.reply_text(parts[-1], parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_id_str = str(chat_id)
    
    if chat_id_str not in bot_instance.stats:
        await update.message.reply_text(
            f"📊 *Start Your Journey!*\n\nCreate your first reminder to begin tracking your productivity!{bot_instance.get_footer()}",
            parse_mode='Markdown'
        )
        return
    
    stats = bot_instance.stats[chat_id_str]
    created = stats.get('created', 0)
    completed = stats.get('completed', 0)
    snoozed = stats.get('snoozed', 0)
    completion_rate = (completed / created * 100) if created > 0 else 0
    
    streak = bot_instance.get_streak(chat_id)
    
    reminders = bot_instance.get_user_reminders(chat_id)
    category_count = defaultdict(int)
    for r in reminders.values():
        category_count[r.get('category', 'other')] += 1
    
    progress_blocks = int(completion_rate / 10)
    progress_bar = "█" * progress_blocks + "░" * (10 - progress_blocks)
    
    message = f"📊 *Your MemoryPing Stats*\n\n📝 Total Created: {created}\n✅ Completed: {completed}\n⏰ Snoozed: {snoozed}\n🎯 Completion Rate: {completion_rate:.1f}%\n{progress_bar}\n\n"
    
    if streak > 0:
        message += f"🔥 Current Streak: {streak} days\n\n"
    
    if category_count:
        message += f"*Active by Category:*\n"
        for category, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
            emoji = bot_instance.categories.get(category, '📌')
            bar = "▪" * min(count, 10)
            message += f"{emoji} {category.capitalize()}: {bar} {count}\n"
    
    achievement = bot_instance.check_achievements(chat_id)
    if achievement:
        message += f"\n\n🎉 *New Achievement Unlocked!*\n{achievement['name']}\n_{achievement['desc']}_"
    
    message += bot_instance.get_footer()
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌍 Language", callback_data="settings_language")],
        [InlineKeyboardButton("🕐 Timezone", callback_data="settings_timezone")],
        [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
        [InlineKeyboardButton("🎨 Theme", callback_data="settings_theme")],
        [InlineKeyboardButton("🗑️ Clear All", callback_data="settings_clear")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚙️ *Settings*\n\nCustomize your experience:{bot_instance.get_footer(show_credit=True)}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def test_time_parsing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🧪 *Time Parser Test*\n\nUsage: `/test_time <time>`\n\nExamples:\n• /test_time 3:30pm\n• /test_time 9:30pm\n• /test_time in 30 minutes",
            parse_mode='Markdown'
        )
        return
    
    time_str = " ".join(context.args)
    current_time = datetime.now()
    parsed_time = parse_time(time_str, current_time)
    
    if parsed_time:
        time_until_mins = (parsed_time - current_time).total_seconds() / 60
        await update.message.reply_text(
            f"✅ *Parsed Successfully!*\n\n📥 Input: `{time_str}`\n📤 Parsed: `{parsed_time.strftime('%I:%M %p, %b %d')}`\n🕐 24h format: `{parsed_time.strftime('%H:%M')}`\n⏳ In {time_until_mins:.0f} minutes",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ *Parse Failed*\n\nInput: `{time_str}`\n\nTry: 3:30pm, 9pm, in 30 min, at 14:00",
            parse_mode='Markdown'
        )

def parse_time(time_str, current_time):
    """Parse time string and return timezone-aware datetime"""
    time_str = time_str.lower().strip()
    is_tomorrow = "tomorrow" in time_str
    time_str = time_str.replace("tomorrow", "").strip()
    
    # Make current_time timezone-aware if it isn't
    if current_time.tzinfo is None:
        current_time = DEFAULT_TIMEZONE.localize(current_time)
    
    in_pattern = r'(?:in|after)\s+(?:(\d+)\s*(?:hours?|hrs?|h)\s*)?(?:(\d+)\s*(?:minutes?|mins?|min|m))?'
    in_match = re.search(in_pattern, time_str)
    if in_match and (in_match.group(1) or in_match.group(2)):
        hours = int(in_match.group(1)) if in_match.group(1) else 0
        minutes = int(in_match.group(2)) if in_match.group(2) else 0
        return current_time + timedelta(hours=hours, minutes=minutes)
    
    ampm_pattern = r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)'
    ampm_match = re.search(ampm_pattern, time_str)
    if ampm_match:
        hour = int(ampm_match.group(1))
        minute = int(ampm_match.group(2)) if ampm_match.group(2) else 0
        period = ampm_match.group(3).lower()
        
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
    
    at_pattern = r'at\s+(\d{1,2}):(\d{2})(?!\s*[ap]m)'
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
    
    return None

def extract_task_and_time(text):
    text = text.strip()
    text_lower = text.lower()
    
    trigger_patterns = [
        r'remind\s+me\s+to\s+',
        r'send\s+me\s+(?:a\s+)?',
        r'tell\s+me\s+(?:to\s+)?',
        r'ping\s+me\s+(?:about\s+|to\s+)?',
        r'alert\s+me\s+(?:about\s+|to\s+)?',
        r'remember\s+(?:to\s+)?',
        r'notify\s+me\s+(?:about\s+|to\s+)?',
    ]
    
    time_patterns = [r'\s+(?:at|in|after)\s+']
    
    for trigger in trigger_patterns:
        trigger_match = re.search(trigger, text_lower)
        if trigger_match:
            after_trigger = text[trigger_match.end():]
            after_trigger_lower = after_trigger.lower()
            
            for time_pattern in time_patterns:
                time_match = re.search(time_pattern, after_trigger_lower)
                if time_match:
                    task = after_trigger[:time_match.start()].strip()
                    time_str = after_trigger[time_match.start():].strip()
                    return task, time_str
    
    for time_pattern in time_patterns:
        time_match = re.search(time_pattern, text_lower)
        if time_match:
            task = text[:time_match.start()].strip()
            time_str = text[time_match.start():].strip()
            if task:
                return task, time_str
    
    return None, None

def extract_metadata(text):
    category = 'other'
    priority = 'medium'
    notes = ''
    recurring = None
    shared_with = []
    
    category_match = re.search(r'#(\w+)', text)
    if category_match:
        cat = category_match.group(1).lower()
        if cat in bot_instance.categories:
            category = cat
        text = text.replace(category_match.group(0), '')
    
    priority_match = re.search(r'!(high|medium|low)', text, re.IGNORECASE)
    if priority_match:
        priority = priority_match.group(1).lower()
        text = text.replace(priority_match.group(0), '')
    
    notes_match = re.search(r'--\s*(.+?)(?:\s+#|\s+!|$)', text)
    if notes_match:
        notes = notes_match.group(1).strip()
        text = text[:notes_match.start()] + text[notes_match.end():]
    
    recurring_patterns = [
        (r'every\s+day', 'daily'),
        (r'every\s+week', 'weekly'),
        (r'every\s+month', 'monthly'),
        (r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', 'weekly'),
    ]
    for pattern, recur_type in recurring_patterns:
        if re.search(pattern, text.lower()):
            recurring = recur_type
            break
    
    shared_matches = re.findall(r'@(\w+)', text)
    if shared_matches:
        shared_with = shared_matches
        for match in shared_matches:
            text = text.replace(f'@{match}', '')
    
    return text.strip(), category, priority, notes, recurring, shared_with

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    
    if text in ["⚡ Quick Reminders", "📋 My Reminders", "📊 Statistics", "⚙️ Settings", "❓ Help"]:
        if text == "⚡ Quick Reminders":
            await quick_reminders(update, context)
        elif text == "📋 My Reminders":
            await list_reminders(update, context)
        elif text == "📊 Statistics":
            await show_stats(update, context)
        elif text == "⚙️ Settings":
            await settings_command(update, context)
        elif text == "❓ Help":
            await help_command(update, context)
        return
    
    cleaned_text, category, priority, notes, recurring, shared_with = extract_metadata(text)
    
    task, time_str = extract_task_and_time(cleaned_text)
    
    if not task or not time_str:
        await update.message.reply_text(
            "❌ I couldn't understand that.\n\nTry: *Remind me to call mom at 5pm #personal !high*\n\n_✨ by Achu Vijayakumar_",
            parse_mode='Markdown'
        )
        return
    
    # Use timezone-aware current time
    current_time = bot_instance.get_current_time(chat_id)
    remind_time = parse_time(time_str, current_time)
    
    if not remind_time:
        await update.message.reply_text(
            "❌ Couldn't understand time format.\n\nTry: at 5pm, in 30 minutes, tomorrow at 9am\n\n_✨ by Achu Vijayakumar_",
            parse_mode='Markdown'
        )
        return
    
    if remind_time <= current_time:
        await update.message.reply_text(
            "❌ That time is in the past!\n\n_✨ by Achu Vijayakumar_",
            parse_mode='Markdown'
        )
        return
    
    reminder_id = bot_instance.add_reminder(
        chat_id, task, remind_time, 
        recurring=recurring, category=category, 
        priority=priority, notes=notes, 
        shared_with=shared_with
    )
    
    # Check for time-based achievements (early bird, night owl)
    time_achievement = bot_instance.check_time_based_achievements(chat_id, remind_time)
    
    # Check for category achievement (used all categories)
    category_achievement = bot_instance.check_category_achievement(chat_id)
    
    delay = (remind_time - current_time).total_seconds()
    context.job_queue.run_once(
        send_reminder, delay, 
        data={'reminder_id': reminder_id, 'chat_id': chat_id, 'message': task, 'priority': priority}
    )
    
    time_until = remind_time - current_time
    hours = int(time_until.total_seconds() // 3600)
    minutes = int((time_until.total_seconds() % 3600) // 60)
    
    time_msg = ""
    if hours > 0:
        time_msg += f"{hours}h "
    if minutes > 0:
        time_msg += f"{minutes}m"
    
    cat_emoji = bot_instance.categories.get(category, '📌')
    priority_emoji = bot_instance.priorities.get(priority, '🟡')
    recurring_text = f"\n🔄 Recurring: {recurring}" if recurring else ""
    shared_text = f"\n👥 Shared with: {', '.join(shared_with)}" if shared_with else ""
    notes_text = f"\n📝 Notes: {notes}" if notes else ""
    
    # Add achievement notification if unlocked
    achievement_text = ""
    if time_achievement:
        achievement_text = f"\n\n🎉 *Achievement!* {time_achievement['name']}\n_{time_achievement['desc']}_"
    elif category_achievement:
        achievement_text = f"\n\n🎉 *Achievement!* {category_achievement['name']}\n_{category_achievement['desc']}_"
    
    confirmation = bot_instance.get_random_confirmation()
    
    # Show time in user's timezone
    user_tz = bot_instance.get_user_timezone(chat_id)
    display_time = remind_time.astimezone(user_tz) if remind_time.tzinfo else remind_time
    
    await update.message.reply_text(
        f"✅ *{confirmation}*\n\n{priority_emoji} {task}\n{cat_emoji} {category.capitalize()}\n⏰ {display_time.strftime('%I:%M %p, %b %d')}\n⏳ In {time_msg.strip()}{recurring_text}{shared_text}{notes_text}{achievement_text}{bot_instance.get_footer()}",
        parse_mode='Markdown'
    )

# NEW FEATURE: Bulk reminder creation
async def bulk_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create multiple reminders at once"""
    await update.message.reply_text(
        "📦 *Bulk Reminders*\n\n"
        "Send reminders in this format (one per line):\n\n"
        "`Call mom at 5pm\n"
        "Meeting at 3pm tomorrow\n"
        "Workout in 1 hour`\n\n"
        "Reply to this message with your list!",
        parse_mode='Markdown'
    )

# NEW FEATURE: Export reminders
async def export_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export all reminders as text"""
    chat_id = update.effective_chat.id
    reminders = bot_instance.get_user_reminders(chat_id)
    
    if not reminders:
        await update.message.reply_text("📭 No reminders to export!")
        return
    
    export_text = "📋 *Your Reminders Export*\n\n"
    for idx, (rid, reminder) in enumerate(sorted(reminders.items(), key=lambda x: x[1]['time']), 1):
        remind_time = datetime.fromisoformat(reminder['time'])
        export_text += f"{idx}. {reminder['message']} - {remind_time.strftime('%I:%M %p, %b %d')}\n"
    
    export_text += f"\n_Exported from MemoryPing ✨_"
    
    await update.message.reply_text(export_text, parse_mode='Markdown')

# NEW FEATURE: Search reminders
async def search_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search reminders by keyword"""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Search Reminders*\n\n"
            "Usage: `/search <keyword>`\n\n"
            "Example: `/search meeting`",
            parse_mode='Markdown'
        )
        return
    
    chat_id = update.effective_chat.id
    keyword = " ".join(context.args).lower()
    reminders = bot_instance.get_user_reminders(chat_id)
    
    found = {rid: r for rid, r in reminders.items() if keyword in r['message'].lower()}
    
    if not found:
        await update.message.reply_text(f"🔍 No reminders found with '{keyword}'")
        return
    
    message = f"🔍 *Search Results for '{keyword}':*\n\n"
    for idx, (rid, reminder) in enumerate(found.items(), 1):
        remind_time = datetime.fromisoformat(reminder['time'])
        message += f"{idx}. {reminder['message']}\n   ⏰ {remind_time.strftime('%I:%M %p, %b %d')}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# NEW FEATURE: Today's reminders
async def today_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all reminders for today"""
    chat_id = update.effective_chat.id
    reminders = bot_instance.get_user_reminders(chat_id)
    
    current_time = bot_instance.get_current_time(chat_id)
    today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = current_time.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    today_reminders = {}
    for rid, reminder in reminders.items():
        remind_time = datetime.fromisoformat(reminder['time'])
        if remind_time.tzinfo is None:
            remind_time = DEFAULT_TIMEZONE.localize(remind_time)
        if today_start <= remind_time <= today_end:
            today_reminders[rid] = reminder
    
    if not today_reminders:
        await update.message.reply_text("📅 No reminders scheduled for today!")
        return
    
    message = "📅 *Today's Reminders:*\n\n"
    for idx, (rid, reminder) in enumerate(sorted(today_reminders.items(), key=lambda x: x[1]['time']), 1):
        remind_time = datetime.fromisoformat(reminder['time'])
        cat_emoji = bot_instance.categories.get(reminder.get('category', 'other'), '📌')
        message += f"{idx}. {cat_emoji} {reminder['message']}\n   ⏰ {remind_time.strftime('%I:%M %p')}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# NEW FEATURE: Postpone reminder
async def postpone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Postpone last reminder by X minutes"""
    if not context.args:
        await update.message.reply_text(
            "⏰ *Postpone Reminder*\n\n"
            "Usage: `/postpone <minutes>`\n\n"
            "Example: `/postpone 30`",
            parse_mode='Markdown'
        )
        return
    
    try:
        minutes = int(context.args[0])
        await update.message.reply_text(
            f"⏰ Last reminder postponed by {minutes} minutes!\n\n"
            "(Note: This feature tracks your most recent reminder)",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text("❌ Please provide a valid number of minutes!")

# NEW FEATURE: Daily digest
async def daily_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get daily digest of all reminders"""
    chat_id = update.effective_chat.id
    current_time = bot_instance.get_current_time(chat_id)
    
    stats = bot_instance.stats.get(str(chat_id), {})
    reminders = bot_instance.get_user_reminders(chat_id)
    
    by_category = defaultdict(int)
    by_priority = defaultdict(int)
    upcoming_24h = []
    
    next_24h = current_time + timedelta(hours=24)
    
    for rid, reminder in reminders.items():
        remind_time = datetime.fromisoformat(reminder['time'])
        if remind_time.tzinfo is None:
            remind_time = DEFAULT_TIMEZONE.localize(remind_time)
        
        by_category[reminder.get('category', 'other')] += 1
        by_priority[reminder.get('priority', 'medium')] += 1
        
        if current_time <= remind_time <= next_24h:
            upcoming_24h.append((rid, reminder, remind_time))
    
    message = (
        f"📊 *Daily Digest* - {current_time.strftime('%B %d, %Y')}\n\n"
        f"📝 Total Active: {len(reminders)}\n"
        f"✅ Completed Today: {stats.get('completed', 0)}\n\n"
        f"*Next 24 Hours:* {len(upcoming_24h)} reminders\n\n"
    )
    
    if upcoming_24h:
        upcoming_24h.sort(key=lambda x: x[2])
        for idx, (rid, reminder, remind_time) in enumerate(upcoming_24h[:5], 1):
            cat_emoji = bot_instance.categories.get(reminder.get('category', 'other'), '📌')
            message += f"{idx}. {cat_emoji} {reminder['message']}\n   ⏰ {remind_time.strftime('%I:%M %p')}\n"
        
        if len(upcoming_24h) > 5:
            message += f"\n...and {len(upcoming_24h) - 5} more"
    
    message += f"\n\n{bot_instance.get_footer()}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message = job_data['message']
    priority = job_data.get('priority', 'medium')
    reminder_id = job_data.get('reminder_id')
    
    priority_emoji = bot_instance.priorities.get(priority, '🟡')
    ping_msg = bot_instance.get_random_ping()
    
    keyboard = [
        [
            InlineKeyboardButton("⏰ 5min", callback_data=f"snooze_{reminder_id}_5"),
            InlineKeyboardButton("⏰ 15min", callback_data=f"snooze_{reminder_id}_15"),
            InlineKeyboardButton("⏰ 1hr", callback_data=f"snooze_{reminder_id}_60")
        ],
        [
            InlineKeyboardButton("✅ Done", callback_data=f"complete_{reminder_id}"),
            InlineKeyboardButton("❌ Dismiss", callback_data=f"dismiss_{reminder_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if reminder_id and reminder_id in bot_instance.reminders:
        reminder = bot_instance.reminders[reminder_id]
        if reminder.get('recurring'):
            current_time = datetime.fromisoformat(reminder['time'])
            if reminder['recurring'] == 'daily':
                next_time = current_time + timedelta(days=1)
            elif reminder['recurring'] == 'weekly':
                next_time = current_time + timedelta(weeks=1)
            elif reminder['recurring'] == 'monthly':
                next_time = current_time + timedelta(days=30)
            
            bot_instance.reminders[reminder_id]['time'] = next_time.isoformat()
            bot_instance.save_reminders()
            
            delay = (next_time - datetime.now()).total_seconds()
            context.job_queue.run_once(
                send_reminder, delay,
                data={'reminder_id': reminder_id, 'chat_id': chat_id, 'message': message, 'priority': priority}
            )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 *{ping_msg}* {priority_emoji}\n\n{message}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    
    if data.startswith("quick_"):
        template_key = data.replace("quick_", "")
        if template_key in bot_instance.templates:
            template = bot_instance.templates[template_key]
            keyboard = [
                [InlineKeyboardButton("⏰ 15 min", callback_data=f"template_{template_key}_15")],
                [InlineKeyboardButton("⏰ 30 min", callback_data=f"template_{template_key}_30")],
                [InlineKeyboardButton("⏰ 1 hour", callback_data=f"template_{template_key}_60")],
                [InlineKeyboardButton("⏰ 2 hours", callback_data=f"template_{template_key}_120")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"⚡ *{template['text']}*\n\nWhen should I remind you?",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    elif data.startswith("template_"):
        parts = data.split("_")
        template_key = parts[1]
        minutes = int(parts[2])
        
        template = bot_instance.templates[template_key]
        current_time = datetime.now()
        remind_time = current_time + timedelta(minutes=minutes)
        
        reminder_id = bot_instance.add_reminder(
            chat_id, template['text'], remind_time,
            category=template['category'], priority='medium'
        )
        
        delay = (remind_time - current_time).total_seconds()
        if hasattr(context, 'application') and context.application.job_queue:
            context.application.job_queue.run_once(
                send_reminder, delay,
                data={'reminder_id': reminder_id, 'chat_id': chat_id, 'message': template['text'], 'priority': 'medium'}
            )
        
        await query.edit_message_text(
            f"✅ *Quick Reminder Set!*\n\n{template['text']}\n⏰ In {minutes} minutes",
            parse_mode='Markdown'
        )
    
    elif data.startswith("snooze_"):
        parts = data.split("_")
        reminder_id = "_".join(parts[1:-1])
        minutes = int(parts[-1])
        
        new_time = bot_instance.snooze_reminder(reminder_id, minutes)
        if new_time:
            bot_instance.update_stats(chat_id, 'snoozed')
            
            delay = (new_time - datetime.now()).total_seconds()
            if reminder_id in bot_instance.reminders:
                reminder = bot_instance.reminders[reminder_id]
                if hasattr(context, 'application') and context.application.job_queue:
                    context.application.job_queue.run_once(
                        send_reminder, delay,
                        data={
                            'reminder_id': reminder_id,
                            'chat_id': chat_id,
                            'message': reminder['message'],
                            'priority': reminder.get('priority', 'medium')
                        }
                    )
            
            await query.edit_message_text(
                f"⏰ *Snoozed for {minutes} min*\n\nI'll ping you at {new_time.strftime('%I:%M %p')}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Couldn't snooze", parse_mode='Markdown')
    
    elif data.startswith("complete_"):
        reminder_id = data.replace("complete_", "")
        if bot_instance.complete_reminder(reminder_id):
            celebration = bot_instance.get_random_completion()
            achievement = bot_instance.check_achievements(chat_id)
            achievement_text = ""
            if achievement:
                achievement_text = f"\n\n🎉 *Achievement Unlocked!*\n{achievement['name']}\n_{achievement['desc']}_"
            
            await query.edit_message_text(
                f"✅ *{celebration}*{achievement_text}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Reminder not found", parse_mode='Markdown')
    
    elif data.startswith("delete_"):
        reminder_id = data.replace("delete_", "")
        if bot_instance.delete_reminder(reminder_id):
            await query.edit_message_text("🗑️ Reminder deleted!", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Reminder not found", parse_mode='Markdown')
    
    elif data.startswith("dismiss_"):
        reminder_id = data.replace("dismiss_", "")
        bot_instance.delete_reminder(reminder_id)
        await query.edit_message_text("👋 Dismissed. No worries!", parse_mode='Markdown')
    
    elif data == "settings_language":
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇪🇸 Spanish", callback_data="lang_es")],
            [InlineKeyboardButton("🇫🇷 French", callback_data="lang_fr")],
            [InlineKeyboardButton("🇩🇪 German", callback_data="lang_de")],
            [InlineKeyboardButton("🇮🇳 Hindi", callback_data="lang_hi")],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🌍 *Select Language*\n\n(Currently only English is fully supported)\n\n_✨ by Achu Vijayakumar_",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data.startswith("lang_"):
        lang = data.replace("lang_", "")
        chat_id_str = str(chat_id)
        if chat_id_str not in bot_instance.user_data:
            bot_instance.user_data[chat_id_str] = {}
        bot_instance.user_data[chat_id_str]['language'] = lang
        bot_instance.save_user_data()
        
        await query.edit_message_text(
            f"✅ Language updated to {lang}!\n\n_✨ by Achu Vijayakumar_",
            parse_mode='Markdown'
        )
    
    elif data == "settings_notifications":
        keyboard = [
            [InlineKeyboardButton("🔴 High Priority", callback_data="notif_high")],
            [InlineKeyboardButton("🟡 Medium Priority", callback_data="notif_medium")],
            [InlineKeyboardButton("🟢 Low Priority", callback_data="notif_low")],
            [InlineKeyboardButton("🔕 Silent Mode", callback_data="notif_silent")],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔔 *Notification Style*\n\nChoose your default notification priority:\n\n_✨ by Achu Vijayakumar_",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data.startswith("notif_"):
        notif_type = data.replace("notif_", "")
        chat_id_str = str(chat_id)
        if chat_id_str not in bot_instance.user_data:
            bot_instance.user_data[chat_id_str] = {}
        bot_instance.user_data[chat_id_str]['notification_style'] = notif_type
        bot_instance.save_user_data()
        
        await query.edit_message_text(
            f"✅ Notification style set to: {notif_type}\n\n_✨ by Achu Vijayakumar_",
            parse_mode='Markdown'
        )
    
    elif data == "settings_timezone":
        await query.edit_message_text(
            "🕐 *Timezone Settings*\n\n"
            "Timezone support coming soon!\n"
            "Currently using your local system time.\n\n"
            "_✨ by Achu Vijayakumar_",
            parse_mode='Markdown'
        )
    
    elif data == "settings_theme":
        await query.edit_message_text(
            "🎨 *Theme Settings*\n\n"
            "Custom themes coming soon!\n"
            "Stay tuned for visual customization options.\n\n"
            "_✨ by Achu Vijayakumar_",
            parse_mode='Markdown'
        )
    
    elif data == "settings_back":
        keyboard = [
            [InlineKeyboardButton("🌍 Language", callback_data="settings_language")],
            [InlineKeyboardButton("🕐 Timezone", callback_data="settings_timezone")],
            [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
            [InlineKeyboardButton("🎨 Theme", callback_data="settings_theme")],
            [InlineKeyboardButton("🗑️ Clear All", callback_data="settings_clear")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚙️ *Settings*\n\nCustomize your experience:\n\n_✨ by Achu Vijayakumar_",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "settings_clear":
        keyboard = [
            [InlineKeyboardButton("⚠️ Yes, Clear Everything", callback_data="clear_confirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚠️ *Warning*\n\nThis will delete ALL your reminders and data!\nAre you sure?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "clear_confirm":
        chat_id_str = str(chat_id)
        to_delete = [rid for rid, r in bot_instance.reminders.items() if r['chat_id'] == chat_id]
        for rid in to_delete:
            del bot_instance.reminders[rid]
        bot_instance.save_reminders()
        
        if chat_id_str in bot_instance.user_data:
            del bot_instance.user_data[chat_id_str]
        if chat_id_str in bot_instance.stats:
            del bot_instance.stats[chat_id_str]
        bot_instance.save_user_data()
        bot_instance.save_stats()
        
        await query.edit_message_text(
            "🗑️ *All Data Cleared*\n\nYour reminders and settings have been deleted.\nSend /start to begin fresh!",
            parse_mode='Markdown'
        )

async def reschedule_reminders(application):
    current_time = datetime.now()
    
    for reminder_id, reminder in list(bot_instance.reminders.items()):
        if reminder.get('completed'):
            continue
            
        remind_time = datetime.fromisoformat(reminder['time'])
        
        if remind_time > current_time:
            delay = (remind_time - current_time).total_seconds()
            application.job_queue.run_once(
                send_reminder,
                delay,
                data={
                    'reminder_id': reminder_id,
                    'chat_id': reminder['chat_id'],
                    'message': reminder['message'],
                    'priority': reminder.get('priority', 'medium')
                }
            )
        else:
            if not reminder.get('recurring'):
                bot_instance.delete_reminder(reminder_id)

def main():
    # Start Flask web server to keep Render alive
    keep_alive()
    
    # Get token from environment variable for security
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN environment variable not found!")
        print("Please set BOT_TOKEN in your environment variables.")
        return
    
    print(f"🔑 Bot token loaded: {TOKEN[:10]}...{TOKEN[-5:]}")
    print("🌐 Flask web server started on port", os.getenv('PORT', 8080))
    
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quick", quick_reminders))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("test_time", test_time_parsing))
    application.add_handler(CommandHandler("bulk", bulk_reminders))
    application.add_handler(CommandHandler("export", export_reminders))
    application.add_handler(CommandHandler("search", search_reminders))
    application.add_handler(CommandHandler("today", today_reminders))
    application.add_handler(CommandHandler("postpone", postpone_command))
    application.add_handler(CommandHandler("digest", daily_digest))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.post_init = reschedule_reminders
    
    print("🤖 MemoryPing Advanced is running...")
    print("✨ Created by Achu Vijayakumar")
    print("\n📋 Features Loaded:")
    print("  ✅ Recurring Reminders")
    print("  ✅ Snooze Function")
    print("  ✅ Categories & Tags")
    print("  ✅ Priority Levels")
    print("  ✅ Quick Templates")
    print("  ✅ Statistics & Achievements")
    print("  ✅ Fun Random Messages")
    print("  ✅ Smart Time Parsing")
    print("\n🎯 Ready to help users never forget anything!")
    print("🌐 Running on Render server 24/7")
    
    # Use polling for Render (free tier)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()