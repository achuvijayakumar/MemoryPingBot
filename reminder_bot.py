"""
MemoryPing v4.0 - The Intelligent Companion
Created by Achu Vijayakumar

Fully functional Telegram bot with advanced features:
- Personality Engine (4 personalities)
- XP & Leveling System
- Smart Habit Detection
- Mood Tracking & Reflection
- Daily Digest System
- Enhanced Natural Language Processing
- Gamified Achievements

Designed for Render deployment with external keep-alive monitoring.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatAction
import re
from collections import defaultdict
import random
from threading import Lock
import pytz
from typing import Dict, List, Optional, Tuple
import logging

# Import keep_alive for Render deployment
try:
    from keep_alive import keep_alive
    KEEP_ALIVE_AVAILABLE = True
except ImportError:
    KEEP_ALIVE_AVAILABLE = False
    logger.warning("⚠️ keep_alive.py not found - running without web server")

# Configure logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

# File storage paths
REMINDERS_FILE = "reminders.json"
USER_DATA_FILE = "user_data.json"
STATS_FILE = "stats.json"
HABITS_FILE = "habits.json"
MOODS_FILE = "moods.json"

# Default settings
DEFAULT_TIMEZONE = pytz.timezone('Asia/Kolkata')
XP_PER_COMPLETION = 10
XP_PER_LEVEL = 100
MAX_MESSAGE_LENGTH = 4000

# Thread-safe file locks
file_locks = {
    'reminders': Lock(),
    'user_data': Lock(),
    'stats': Lock(),
    'habits': Lock(),
    'moods': Lock()
}

# ============================================================================
# PERSONALITY ENGINE - 4 Distinct Bot Personalities
# ============================================================================

PERSONALITIES = {
    'zen': {
        'name': 'Zen Monk 🧘',
        'confirmation': [
            "Peace. I shall remind you.",
            "In stillness, I remember.",
            "Mindfully noted, friend."
        ],
        'completion': [
            "Harmony achieved.",
            "Balance restored.",
            "Inner peace attained."
        ],
        'ping': [
            "🧘 Gentle reminder...",
            "☯️ Time flows...",
            "🕉️ The moment arrives..."
        ]
    },
    'coach': {
        'name': 'Coach 🏋️',
        'confirmation': [
            "LET'S GO! 💪",
            "LOCKED IN! 🔥",
            "WE GOT THIS! 💯"
        ],
        'completion': [
            "BEAST MODE! 🔥",
            "CRUSHING IT! 💪",
            "THAT'S MY CHAMPION! 🏆"
        ],
        'ping': [
            "⏰ TIME TO EXECUTE!",
            "🔥 GAME TIME!",
            "💪 LET'S MOVE!"
        ]
    },
    'bestie': {
        'name': 'Bestie 💖',
        'confirmation': [
            "Gotchu boo! 💕",
            "Yass queen! ✨",
            "On it bestie! 💅"
        ],
        'completion': [
            "OMG YOU DID IT! 🎉",
            "SLAYYYY! 💅",
            "Proud of you babe! 💖"
        ],
        'ping': [
            "💕 Heyyyy!",
            "✨ Bestie reminder!",
            "👑 Queen, don't forget!"
        ]
    },
    'techbro': {
        'name': 'Tech Bro 🤓',
        'confirmation': [
            "Synced to cloud 🚀",
            "Committed to memory 💾",
            "Deployed successfully ✅"
        ],
        'completion': [
            "Shipped! 💻",
            "Merged to main! 🔀",
            "Build successful! ✓"
        ],
        'ping': [
            "⚡ API call received",
            "🔔 Event triggered",
            "📡 Webhook fired"
        ]
    }
}

# ============================================================================
# GAMIFICATION SYSTEM - Quotes, Tips, Achievements
# ============================================================================

MOTIVATIONAL_QUOTES = [
    "The secret of getting ahead is getting started.",
    "Small daily improvements lead to stunning results.",
    "Progress, not perfection.",
    "You don't have to be great to start, but you have to start to be great.",
    "The only way to do great work is to love what you do.",
    "Success is the sum of small efforts repeated day in and day out.",
    "Dream big. Start small. Act now.",
    "Your future self will thank you."
]

TIPS = [
    "💡 Tip: Tag reminders with #work #health for organization!",
    "💡 Pro tip: Add !high for urgent reminders",
    "💡 Try /digest for a daily summary of your productivity",
    "💡 Use 'every day' for recurring reminders",
    "💡 Set your personality with /personality for custom vibes",
    "💡 Check your level progress with /stats",
    "💡 Use /today to see what's coming up",
    "💡 Snooze is your friend - don't stress!",
    "💡 Build streaks for bonus XP",
    "💡 Try natural language: 'workout in 30 minutes'"
]

CATEGORIES = {
    'work': '💼',
    'personal': '👤',
    'health': '💊',
    'shopping': '🛒',
    'fitness': '💪',
    'family': '👨‍👩‍👧',
    'finance': '💰',
    'education': '📚',
    'other': '📌'
}

PRIORITIES = {
    'high': '🔴',
    'medium': '🟡',
    'low': '🟢'
}

TEMPLATES = {
    'medicine': {'text': 'Take medicine', 'category': 'health'},
    'water': {'text': 'Drink water', 'category': 'health'},
    'exercise': {'text': 'Time to exercise', 'category': 'fitness'},
    'standup': {'text': 'Stand up and stretch', 'category': 'health'},
    'call_family': {'text': 'Call family', 'category': 'family'},
    'check_email': {'text': 'Check emails', 'category': 'work'}
}

ACHIEVEMENTS = {
    'first_reminder': {
        'name': '🎬 First Step',
        'desc': 'Created your first reminder',
        'xp': 50
    },
    'complete_10': {
        'name': '✨ Achiever',
        'desc': 'Completed 10 reminders',
        'xp': 100
    },
    'complete_50': {
        'name': '💎 Diamond',
        'desc': 'Completed 50 reminders',
        'xp': 250
    },
    'complete_100': {
        'name': '👑 Master',
        'desc': 'Completed 100 reminders',
        'xp': 500
    },
    'early_bird': {
        'name': '🌅 Early Bird',
        'desc': 'Set a reminder before 7am',
        'xp': 25
    },
    'night_owl': {
        'name': '🦉 Night Owl',
        'desc': 'Set a reminder after 10pm',
        'xp': 25
    },
    'streak_3': {
        'name': '🔥 On Fire',
        'desc': '3-day completion streak',
        'xp': 50
    },
    'streak_7': {
        'name': '⚡ Unstoppable',
        'desc': '7-day completion streak',
        'xp': 150
    },
    'organized': {
        'name': '🗂️ Organizer',
        'desc': 'Used all categories',
        'xp': 100
    }
}

# ============================================================================
# DATA MANAGER - Thread-Safe Data Persistence
# ============================================================================

class DataManager:
    """Handles all data persistence with thread-safe file operations"""
    
    def __init__(self):
        self.reminders = self._load('reminders')
        self.user_data = self._load('user_data')
        self.stats = self._load('stats')
        self.habits = self._load('habits')
        self.moods = self._load('moods')
        self.message_count = 0
    
    def _load(self, key: str) -> dict:
        """Load JSON data from file with error handling"""
        filepath = f"{key}.json"
        if os.path.exists(filepath):
            try:
                with file_locks[key], open(filepath, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {filepath}: {e}")
        return {}
    
    def _save(self, data: dict, key: str):
        """Save JSON data to file with thread safety"""
        try:
            with file_locks[key], open(f"{key}.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving {key}: {e}")
    
    def save_reminders(self):
        self._save(self.reminders, 'reminders')
    
    def save_user_data(self):
        self._save(self.user_data, 'user_data')
    
    def save_stats(self):
        self._save(self.stats, 'stats')
    
    def save_habits(self):
        self._save(self.habits, 'habits')
    
    def save_moods(self):
        self._save(self.moods, 'moods')

# ============================================================================
# MEMORY PING ENGINE - Core Business Logic
# ============================================================================

class MemoryPingEngine:
    """Core engine handling all bot intelligence and logic"""
    
    def __init__(self, data: DataManager):
        self.data = data
    
    # ------------------------------------------------------------------------
    # Personality System
    # ------------------------------------------------------------------------
    
    def get_user_personality(self, chat_id: int) -> str:
        """Get user's selected personality (default: bestie)"""
        cid = str(chat_id)
        if cid not in self.data.user_data:
            self.data.user_data[cid] = {
                'personality': 'bestie',
                'timezone': 'Asia/Kolkata'
            }
        return self.data.user_data[cid].get('personality', 'bestie')
    
    def get_response_tone(self, chat_id: int, response_type: str = "confirmation") -> str:
        """Get personality-based response message"""
        personality = self.get_user_personality(chat_id)
        messages = PERSONALITIES.get(personality, PERSONALITIES['bestie'])[response_type]
        return random.choice(messages)
    
    # ------------------------------------------------------------------------
    # XP & Leveling System
    # ------------------------------------------------------------------------
    
    def get_user_xp(self, chat_id: int) -> int:
        """Get user's total XP"""
        cid = str(chat_id)
        return self.data.stats.get(cid, {}).get('xp', 0)
    
    def get_user_level(self, chat_id: int) -> int:
        """Calculate user's level from XP"""
        return max(1, self.get_user_xp(chat_id) // XP_PER_LEVEL + 1)
    
    def update_xp(self, chat_id: int, amount: int) -> Tuple[Optional[str], int]:
        """
        Update user XP and check for level up
        Returns: (achievement_type, new_level)
        """
        cid = str(chat_id)
        if cid not in self.data.stats:
            self.data.stats[cid] = {'xp': 0}
        
        old_level = self.get_user_level(chat_id)
        self.data.stats[cid]['xp'] = max(0, self.data.stats[cid].get('xp', 0) + amount)
        new_level = self.get_user_level(chat_id)
        self.data.save_stats()
        
        if new_level > old_level:
            return ('level_up', new_level)
        return (None, new_level)
    
    def calculate_memory_score(self, chat_id: int) -> int:
        """
        Calculate Memory Score (0-1000) based on:
        - XP earned
        - Completion rate
        - Streak days
        """
        stats = self.data.stats.get(str(chat_id), {})
        xp = stats.get('xp', 0)
        created = stats.get('created', 0)
        completed = stats.get('completed', 0)
        
        completion_rate = (completed / created * 100) if created > 0 else 0
        streak = self.get_streak(chat_id)
        
        score = int((xp / 10) + (completion_rate * 2) + (streak * 5))
        return min(1000, score)
    
    # ------------------------------------------------------------------------
    # Reminder Management
    # ------------------------------------------------------------------------
    
    def add_reminder(self, chat_id: int, message: str, remind_time: datetime, **kwargs) -> str:
        """Create a new reminder and return its ID"""
        reminder_id = f"{chat_id}_{remind_time.timestamp()}_{len(self.data.reminders)}"
        
        self.data.reminders[reminder_id] = {
            'chat_id': chat_id,
            'message': message,
            'time': remind_time.isoformat(),
            'recurring': kwargs.get('recurring'),
            'category': kwargs.get('category', 'other'),
            'priority': kwargs.get('priority', 'medium'),
            'notes': kwargs.get('notes', ''),
            'shared_with': kwargs.get('shared_with', []),
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        
        self.data.save_reminders()
        self.update_stats(chat_id, 'created')
        
        # Track for habit analysis
        self._track_habit(chat_id, message, remind_time)
        
        return reminder_id
    
    def get_user_reminders(self, chat_id: int, category: str = None) -> dict:
        """Get all active reminders for a user"""
        reminders = {
            k: v for k, v in self.data.reminders.items()
            if (v['chat_id'] == chat_id or chat_id in v.get('shared_with', []))
            and not v.get('completed')
        }
        
        if category:
            reminders = {k: v for k, v in reminders.items() if v.get('category') == category}
        
        return reminders
    
    def complete_reminder(self, reminder_id: str) -> Tuple[bool, Optional[dict], int]:
        """
        Mark reminder as complete and award XP
        Returns: (success, achievement, level)
        """
        if reminder_id in self.data.reminders:
            self.data.reminders[reminder_id]['completed'] = True
            self.data.save_reminders()
            
            chat_id = self.data.reminders[reminder_id]['chat_id']
            self.update_stats(chat_id, 'completed')
            
            # Award XP
            ach_key, level = self.update_xp(chat_id, XP_PER_COMPLETION)
            
            # Check for achievements
            achievement = self.check_achievements(chat_id)
            
            return True, achievement, level
        return False, None, 0
    
    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder"""
        if reminder_id in self.data.reminders:
            del self.data.reminders[reminder_id]
            self.data.save_reminders()
            return True
        return False
    
    def snooze_reminder(self, reminder_id: str, minutes: int) -> Optional[datetime]:
        """Snooze reminder by X minutes"""
        if reminder_id in self.data.reminders:
            current_time = datetime.fromisoformat(self.data.reminders[reminder_id]['time'])
            new_time = current_time + timedelta(minutes=minutes)
            self.data.reminders[reminder_id]['time'] = new_time.isoformat()
            self.data.save_reminders()
            return new_time
        return None
    
    # ------------------------------------------------------------------------
    # Statistics & Achievements
    # ------------------------------------------------------------------------
    
    def update_stats(self, chat_id: int, action: str):
        """Update user statistics"""
        cid = str(chat_id)
        if cid not in self.data.stats:
            self.data.stats[cid] = {
                'created': 0,
                'completed': 0,
                'snoozed': 0,
                'xp': 0
            }
        self.data.stats[cid][action] = self.data.stats[cid].get(action, 0) + 1
        self.data.save_stats()
    
    def get_streak(self, chat_id: int) -> int:
        """Get user's current streak"""
        return self.data.user_data.get(str(chat_id), {}).get('streak', 0)
    
    def check_achievements(self, chat_id: int) -> Optional[dict]:
        """Check if user unlocked any achievements"""
        cid = str(chat_id)
        stats = self.data.stats.get(cid, {})
        
        if cid not in self.data.user_data:
            self.data.user_data[cid] = {'achievements': []}
        
        user_achs = self.data.user_data[cid].get('achievements', [])
        completed = stats.get('completed', 0)
        
        # Check milestone achievements
        milestones = [
            (1, 'first_reminder'),
            (10, 'complete_10'),
            (50, 'complete_50'),
            (100, 'complete_100')
        ]
        
        for milestone, ach_key in milestones:
            if completed == milestone and ach_key not in user_achs:
                user_achs.append(ach_key)
                self.data.user_data[cid]['achievements'] = user_achs
                self.data.save_user_data()
                
                # Award XP bonus
                xp_reward = ACHIEVEMENTS[ach_key]['xp']
                if xp_reward > 0:
                    self.update_xp(chat_id, xp_reward)
                
                return ACHIEVEMENTS[ach_key]
        
        return None
    
    def check_time_achievements(self, chat_id: int, remind_time: datetime) -> Optional[dict]:
        """Check for time-based achievements (early bird, night owl)"""
        cid = str(chat_id)
        if cid not in self.data.user_data:
            self.data.user_data[cid] = {'achievements': []}
        
        user_achs = self.data.user_data[cid].get('achievements', [])
        hour = remind_time.hour
        
        ach_key = None
        if hour < 7 and 'early_bird' not in user_achs:
            ach_key = 'early_bird'
        elif hour >= 22 and 'night_owl' not in user_achs:
            ach_key = 'night_owl'
        
        if ach_key:
            user_achs.append(ach_key)
            self.data.user_data[cid]['achievements'] = user_achs
            self.data.save_user_data()
            self.update_xp(chat_id, ACHIEVEMENTS[ach_key]['xp'])
            return ACHIEVEMENTS[ach_key]
        
        return None
    
    def check_category_achievement(self, chat_id: int) -> Optional[dict]:
        """Check if user has used all categories"""
        cid = str(chat_id)
        if cid not in self.data.user_data:
            return None
        
        user_achs = self.data.user_data[cid].get('achievements', [])
        if 'organized' in user_achs:
            return None
        
        # Get all categories used
        user_reminders = self.get_user_reminders(chat_id)
        categories_used = set()
        for reminder in user_reminders.values():
            categories_used.add(reminder.get('category', 'other'))
        
        # Check if all categories used
        if len(categories_used) >= len(CATEGORIES):
            user_achs.append('organized')
            self.data.user_data[cid]['achievements'] = user_achs
            self.data.save_user_data()
            self.update_xp(chat_id, ACHIEVEMENTS['organized']['xp'])
            return ACHIEVEMENTS['organized']
        
        return None
    
    # ------------------------------------------------------------------------
    # Habit Detection System
    # ------------------------------------------------------------------------
    
    def _track_habit(self, chat_id: int, message: str, remind_time: datetime):
        """Track reminder patterns for habit detection"""
        cid = str(chat_id)
        if cid not in self.data.habits:
            self.data.habits[cid] = []
        
        self.data.habits[cid].append({
            'message': message.lower(),
            'hour': remind_time.hour,
            'weekday': remind_time.weekday(),
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 100 entries per user
        self.data.habits[cid] = self.data.habits[cid][-100:]
        self.data.save_habits()
    
    def analyze_habits(self, chat_id: int) -> Optional[List[dict]]:
        """
        Analyze user's reminder patterns and suggest recurring reminders
        Returns list of suggestions or None
        """
        patterns = self.data.habits.get(str(chat_id), [])
        if len(patterns) < 5:
            return None
        
        task_times = defaultdict(list)
        for p in patterns:
            task_times[p['message']].append(p['hour'])
        
        suggestions = []
        for task, hours in task_times.items():
            if len(hours) >= 3:
                avg_hour = int(sum(hours) / len(hours))
                suggestions.append({
                    'type': 'recurring',
                    'task': task,
                    'time': f"{avg_hour:02d}:00"
                })
        
        return suggestions if suggestions else None
    
    # ------------------------------------------------------------------------
    # Mood Tracking System
    # ------------------------------------------------------------------------
    
    def save_mood(self, chat_id: int, mood: str, note: str = ""):
        """Save user's daily mood"""
        cid = str(chat_id)
        today = datetime.now().strftime("%Y-%m-%d")
        
        if cid not in self.data.moods:
            self.data.moods[cid] = {}
        
        self.data.moods[cid][today] = {
            'mood': mood,
            'note': note,
            'timestamp': datetime.now().isoformat()
        }
        self.data.save_moods()
    
    def get_recent_moods(self, chat_id: int, days: int = 7) -> List[dict]:
        """Get user's mood history for last N days"""
        cid = str(chat_id)
        if cid not in self.data.moods:
            return []
        
        moods = self.data.moods[cid]
        recent = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in moods:
                recent.append({
                    'date': date,
                    **moods[date]
                })
        
        return recent
    
    # ------------------------------------------------------------------------
    # Timezone & Time Utilities
    # ------------------------------------------------------------------------
    
    def get_user_timezone(self, chat_id: int) -> pytz.timezone:
        """Get user's timezone"""
        cid = str(chat_id)
        tz_name = self.data.user_data.get(cid, {}).get('timezone', 'Asia/Kolkata')
        return pytz.timezone(tz_name)
    
    def get_current_time(self, chat_id: int) -> datetime:
        """Get current time in user's timezone"""
        return datetime.now(self.get_user_timezone(chat_id))
    
    # ------------------------------------------------------------------------
    # UI Helpers
    # ------------------------------------------------------------------------
    
    def get_footer(self) -> str:
        """Get rotating footer with tips/quotes/credits"""
        self.data.message_count += 1
        
        if self.data.message_count % 10 == 0:
            return "\n\n_✨ MemoryPing v4.0 by Achu Vijayakumar_"
        elif self.data.message_count % 5 == 0:
            return f"\n\n💭 _{random.choice(MOTIVATIONAL_QUOTES)}_"
        else:
            return f"\n\n{random.choice(TIPS)}"
    
    @staticmethod
    def format_progress_bar(percentage: float, length: int = 10) -> str:
        """Create emoji progress bar"""
        filled = int(percentage / 100 * length)
        return "█" * filled + "░" * (length - filled)
    
    @staticmethod
    def split_long_message(text: str) -> List[str]:
        """Split long messages into chunks"""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]
        
        parts = []
        while text:
            if len(text) <= MAX_MESSAGE_LENGTH:
                parts.append(text)
                break
            
            split_at = text.rfind('\n', 0, MAX_MESSAGE_LENGTH)
            if split_at == -1:
                split_at = MAX_MESSAGE_LENGTH
            
            parts.append(text[:split_at])
            text = text[split_at:].lstrip()
        
        return parts

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

data_manager = DataManager()
bot_engine = MemoryPingEngine(data_manager)

# ============================================================================
# TIME PARSING - Natural Language Understanding
# ============================================================================

def parse_time(time_str: str, current_time: datetime) -> Optional[datetime]:
    """
    Parse natural language time expressions
    Supports: 5pm, in 30 min, tomorrow, lunch, etc.
    """
    time_str = time_str.lower().strip()
    is_tomorrow = "tomorrow" in time_str
    time_str = time_str.replace("tomorrow", "").strip()
    
    # Make timezone-aware
    if current_time.tzinfo is None:
        current_time = DEFAULT_TIMEZONE.localize(current_time)
    
    # Special keywords
    if "lunch" in time_str:
        remind_time = current_time.replace(hour=13, minute=0, second=0, microsecond=0)
        if remind_time <= current_time:
            remind_time += timedelta(days=1)
        return remind_time
    
    if "dinner" in time_str:
        remind_time = current_time.replace(hour=19, minute=0, second=0, microsecond=0)
        if remind_time <= current_time:
            remind_time += timedelta(days=1)
        return remind_time
    
    if "morning" in time_str:
        remind_time = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
        if is_tomorrow or remind_time <= current_time:
            remind_time += timedelta(days=1)
        return remind_time
    
    if "evening" in time_str:
        remind_time = current_time.replace(hour=18, minute=0, second=0, microsecond=0)
        if is_tomorrow or remind_time <= current_time:
            remind_time += timedelta(days=1)
        return remind_time
    
    # Relative time: "in 2h 30m"
    match = re.search(
        r'(?:in|after)\s+(?:(\d+)\s*(?:hours?|hrs?|h))?\s*(?:(\d+)\s*(?:minutes?|mins?|min|m))?',
        time_str
    )
    if match and (match.group(1) or match.group(2)):
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        return current_time + timedelta(hours=hours, minutes=minutes)
    
    # 12-hour format: "5pm", "3:30am"
    match = re.search(r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        remind_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if is_tomorrow or remind_time <= current_time:
            remind_time += timedelta(days=1)
        
        return remind_time
    
    # 24-hour format: "14:30"
    match = re.search(r'at\s+(\d{1,2}):(\d{2})(?!\s*[ap]m)', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        remind_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if is_tomorrow or remind_time <= current_time:
            remind_time += timedelta(days=1)
        
        return remind_time
    
    return None

def extract_task_and_time(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract task and time from natural language
    Example: "Remind me to call mom at 5pm" -> ("call mom", "at 5pm")
    """
    text_lower = text.lower()
    
    # Common trigger patterns
    triggers = [
        r'remind\s+me\s+to\s+',
        r'send\s+me\s+(?:a\s+)?',
        r'tell\s+me\s+(?:to\s+)?',
        r'ping\s+me\s+(?:about\s+|to\s+)?',
        r'alert\s+me\s+(?:about\s+|to\s+)?'
    ]
    
    for trigger in triggers:
        trigger_match = re.search(trigger, text_lower)
        if trigger_match:
            after_trigger = text[trigger_match.end():]
            time_match = re.search(r'\s+(?:at|in|after)\s+', after_trigger.lower())
            if time_match:
                task = after_trigger[:time_match.start()].strip()
                time_str = after_trigger[time_match.start():].strip()
                return task, time_str
    
    # No trigger, just look for time pattern
    time_match = re.search(r'\s+(?:at|in|after)\s+', text_lower)
    if time_match:
        task = text[:time_match.start()].strip()
        time_str = text[time_match.start():].strip()
        if task:
            return task, time_str
    
    return None, None

def extract_metadata(text: str) -> Tuple[str, str, str, str, Optional[str], List[str]]:
    """
    Extract metadata from reminder text: category, priority, notes, recurring, shared
    Example: "Meeting #work !high -- Bring laptop" 
    """
    category = 'other'
    priority = 'medium'
    notes = ''
    recurring = None
    shared_with = []
    
    # Extract category (#work)
    cat_match = re.search(r'#(\w+)', text)
    if cat_match and cat_match.group(1).lower() in CATEGORIES:
        category = cat_match.group(1).lower()
        text = text.replace(cat_match.group(0), '')
    
    # Extract priority (!high)
    pri_match = re.search(r'!(high|medium|low)', text, re.IGNORECASE)
    if pri_match:
        priority = pri_match.group(1).lower()
        text = text.replace(pri_match.group(0), '')
    
    # Extract notes (-- Note text)
    notes_match = re.search(r'--\s*(.+?)(?:\s+#|\s+!|$)', text)
    if notes_match:
        notes = notes_match.group(1).strip()
        text = text[:notes_match.start()] + text[notes_match.end():]
    
    # Extract recurring patterns
    if 'every day' in text.lower() or 'daily' in text.lower():
        recurring = 'daily'
    elif 'every week' in text.lower() or 'weekly' in text.lower():
        recurring = 'weekly'
    elif re.search(r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', text.lower()):
        recurring = 'weekly'
    
    # Extract shared users (@username)
    shared_matches = re.findall(r'@(\w+)', text)
    if shared_matches:
        shared_with = shared_matches
        for match in shared_matches:
            text = text.replace(f'@{match}', '')
    
    return text.strip(), category, priority, notes, recurring, shared_with

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Welcome message with main menu"""
    keyboard = [
        [KeyboardButton("⚡ Quick"), KeyboardButton("📋 List"), KeyboardButton("📊 Stats")],
        [KeyboardButton("❓ Help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome = (
        "🧠 *MemoryPing v4.0*\n"
        "_The Intelligent Companion_\n\n"
        "I'm your productivity partner with personality, XP system, and smart features!\n\n"
        "*Quick Start:*\n"
        "Just talk naturally!\n"
        "_'Remind me to call mom at 5pm'_\n"
        "_'Workout in 30 minutes'_\n"
        "_'Take medicine every day at 9am'_\n\n"
        "*Features:*\n"
        "🎭 4 Personalities\n"
        "🎮 XP & Levels\n"
        "🧠 Habit Detection\n"
        "😊 Mood Tracking\n"
        "🏆 Achievements\n\n"
        "_Created by Achu Vijayakumar_"
    )
    
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command - Show all features and commands"""
    help_text = (
        "📖 *MemoryPing v4.0 Guide*\n\n"
        "*🎯 Commands:*\n"
        "/personality - Choose bot vibe\n"
        "/stats - View XP & level\n"
        "/today - Today's schedule\n"
        "/list - All reminders\n"
        "/digest - Daily summary\n"
        "/reflect - Mood history\n"
        "/habits - Smart suggestions\n"
        "/focus - Pomodoro timer\n\n"
        "*💬 Natural Language:*\n"
        "• Call mom at 5pm\n"
        "• Workout in 30 minutes #fitness\n"
        "• Meeting at 2pm tomorrow #work !high\n"
        "• Take medicine every day at 9am\n\n"
        "*🎨 Organize:*\n"
        "#work #health #fitness #family\n"
        "!high !medium !low\n"
        "-- Add notes after dash\n\n"
        "_by Achu Vijayakumar_"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Personality selection command"""
    keyboard = [
        [InlineKeyboardButton("🧘 Zen Monk", callback_data="personality_zen")],
        [InlineKeyboardButton("🏋️ Coach", callback_data="personality_coach")],
        [InlineKeyboardButton("💖 Bestie", callback_data="personality_bestie")],
        [InlineKeyboardButton("🤓 Tech Bro", callback_data="personality_techbro")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current = bot_engine.get_user_personality(update.effective_chat.id)
    current_name = PERSONALITIES[current]['name']
    
    await update.message.reply_text(
        f"🎭 *Choose Your Bot's Vibe*\n\nCurrent: {current_name}\n\nSelect a personality:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stats command - Show XP, level, memory score, achievements"""
    chat_id = update.effective_chat.id
    
    if str(chat_id) not in data_manager.stats:
        await update.message.reply_text(
            "📊 *Start Your Journey!*\n\n"
            "Create your first reminder to begin tracking!\n\n"
            "_✨ MemoryPing v4.0_",
            parse_mode='Markdown'
        )
        return
    
    stats = data_manager.stats[str(chat_id)]
    xp = bot_engine.get_user_xp(chat_id)
    level = bot_engine.get_user_level(chat_id)
    memory_score = bot_engine.calculate_memory_score(chat_id)
    
    created = stats.get('created', 0)
    completed = stats.get('completed', 0)
    snoozed = stats.get('snoozed', 0)
    completion_rate = (completed / created * 100) if created > 0 else 0
    
    # XP progress bar
    xp_in_level = xp % XP_PER_LEVEL
    xp_progress = (xp_in_level / XP_PER_LEVEL) * 100
    xp_bar = bot_engine.format_progress_bar(xp_progress)
    
    # Streak
    streak = bot_engine.get_streak(chat_id)
    streak_text = f"🔥 Streak: {streak} days\n" if streak > 0 else ""
    
    # Achievements
    user_achs = data_manager.user_data.get(str(chat_id), {}).get('achievements', [])
    ach_text = ""
    if user_achs:
        ach_emojis = [ACHIEVEMENTS[a]['name'].split()[0] for a in user_achs[:5]]
        ach_text = f"\n🏆 Achievements: {' '.join(ach_emojis)}"
    
    message = (
        f"📊 *Your MemoryPing Profile*\n\n"
        f"⭐ Level {level} | 💎 {xp} XP\n"
        f"{xp_bar} {xp_in_level}/{XP_PER_LEVEL}\n\n"
        f"🧠 Memory Score: {memory_score}/1000\n\n"
        f"📝 Created: {created}\n"
        f"✅ Completed: {completed}\n"
        f"⏰ Snoozed: {snoozed}\n"
        f"🎯 Completion Rate: {completion_rate:.1f}%\n"
        f"{streak_text}"
        f"{ach_text}"
        f"{bot_engine.get_footer()}"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def today_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all reminders scheduled for today"""
    chat_id = update.effective_chat.id
    reminders = bot_engine.get_user_reminders(chat_id)
    
    current_time = bot_engine.get_current_time(chat_id)
    today_start = current_time.replace(hour=0, minute=0, second=0)
    today_end = current_time.replace(hour=23, minute=59, second=59)
    
    today_reminders = {}
    for rid, rdata in reminders.items():
        remind_time = datetime.fromisoformat(rdata['time'])
        if remind_time.tzinfo is None:
            remind_time = DEFAULT_TIMEZONE.localize(remind_time)
        if today_start <= remind_time <= today_end:
            today_reminders[rid] = (rdata, remind_time)
    
    if not today_reminders:
        await update.message.reply_text(
            "📅 No reminders today! Enjoy your free time! 🎉"
        )
        return
    
    message = f"📅 *Today's Schedule* - {current_time.strftime('%b %d')}\n\n"
    
    for idx, (rid, (rdata, rtime)) in enumerate(
        sorted(today_reminders.items(), key=lambda x: x[1][1]), 1
    ):
        cat_emoji = CATEGORIES.get(rdata.get('category', 'other'), '📌')
        pri_emoji = PRIORITIES.get(rdata.get('priority', 'medium'), '🟡')
        
        message += (
            f"{idx}. {cat_emoji} {pri_emoji} {rdata['message']}\n"
            f"   ⏰ {rtime.strftime('%I:%M %p')}\n\n"
        )
    
    message += bot_engine.get_footer()
    await update.message.reply_text(message, parse_mode='Markdown')

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active reminders with action buttons"""
    chat_id = update.effective_chat.id
    reminders = bot_engine.get_user_reminders(chat_id)
    
    if not reminders:
        await update.message.reply_text(
            f"📭 No active reminders!\n\nYou're all clear! 🎉{bot_engine.get_footer()}",
            parse_mode='Markdown'
        )
        return
    
    message = "📋 *Your Reminders*\n\n"
    keyboard = []
    
    for idx, (rid, rdata) in enumerate(
        sorted(reminders.items(), key=lambda x: x[1]['time']), 1
    ):
        remind_time = datetime.fromisoformat(rdata['time'])
        cat_emoji = CATEGORIES.get(rdata.get('category', 'other'), '📌')
        pri_emoji = PRIORITIES.get(rdata.get('priority', 'medium'), '🟡')
        recurring = f" 🔄 {rdata['recurring']}" if rdata.get('recurring') else ""
        
        message += (
            f"{idx}. {cat_emoji} {pri_emoji} {rdata['message']}\n"
            f"   ⏰ {remind_time.strftime('%I:%M %p, %b %d')}{recurring}\n\n"
        )
        
        keyboard.append([
            InlineKeyboardButton(f"✅ #{idx}", callback_data=f"complete_{rid}"),
            InlineKeyboardButton(f"❌ #{idx}", callback_data=f"delete_{rid}")
        ])
    
    message += bot_engine.get_footer()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Daily digest - Summary of productivity"""
    chat_id = update.effective_chat.id
    current_time = bot_engine.get_current_time(chat_id)
    
    stats = data_manager.stats.get(str(chat_id), {})
    reminders = bot_engine.get_user_reminders(chat_id)
    
    # Stats
    created = stats.get('created', 0)
    completed = stats.get('completed', 0)
    xp = bot_engine.get_user_xp(chat_id)
    level = bot_engine.get_user_level(chat_id)
    memory_score = bot_engine.calculate_memory_score(chat_id)
    
    # Upcoming in next 24h
    next_24h = current_time + timedelta(hours=24)
    upcoming = []
    
    for rid, rdata in reminders.items():
        remind_time = datetime.fromisoformat(rdata['time'])
        if remind_time.tzinfo is None:
            remind_time = DEFAULT_TIMEZONE.localize(remind_time)
        if current_time <= remind_time <= next_24h:
            upcoming.append((rid, rdata, remind_time))
    
    upcoming.sort(key=lambda x: x[2])
    
    # Build message
    message = (
        f"📊 *Daily Digest* - {current_time.strftime('%B %d, %Y')}\n\n"
        f"⭐ Level {level} | 💎 {xp} XP\n"
        f"🧠 Memory Score: {memory_score}/1000\n\n"
        f"📝 Total Created: {created}\n"
        f"✅ Completed: {completed}\n"
        f"📋 Active: {len(reminders)}\n\n"
        f"*Next 24 Hours:* {len(upcoming)} reminders\n\n"
    )
    
    if upcoming:
        for idx, (rid, rdata, rtime) in enumerate(upcoming[:5], 1):
            cat_emoji = CATEGORIES.get(rdata.get('category', 'other'), '📌')
            message += f"{idx}. {cat_emoji} {rdata['message']}\n   ⏰ {rtime.strftime('%I:%M %p')}\n"
        
        if len(upcoming) > 5:
            message += f"\n...and {len(upcoming) - 5} more"
    
    message += f"\n\n{bot_engine.get_footer()}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def reflect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mood history and reflection"""
    chat_id = update.effective_chat.id
    moods = bot_engine.get_recent_moods(chat_id, days=7)
    
    if not moods:
        keyboard = [
            [InlineKeyboardButton("😊 Great", callback_data="mood_great")],
            [InlineKeyboardButton("😐 Okay", callback_data="mood_okay")],
            [InlineKeyboardButton("😞 Rough", callback_data="mood_rough")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "😊 *Daily Reflection*\n\nHow was your day today?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    message = "😊 *Your Mood History*\n\n"
    
    mood_emojis = {
        'great': '😊',
        'okay': '😐',
        'rough': '😞'
    }
    
    for mood_data in moods:
        emoji = mood_emojis.get(mood_data['mood'], '😐')
        date = datetime.fromisoformat(mood_data['date']).strftime('%b %d')
        message += f"{emoji} {date}"
        if mood_data.get('note'):
            message += f" - {mood_data['note'][:30]}"
        message += "\n"
    
    message += f"\n{bot_engine.get_footer()}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def habits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show habit suggestions based on patterns"""
    chat_id = update.effective_chat.id
    suggestions = bot_engine.analyze_habits(chat_id)
    
    if not suggestions:
        await update.message.reply_text(
            "🧠 *Habit Detection*\n\n"
            "I'm learning your patterns!\n"
            "Create more reminders and I'll suggest recurring habits.\n\n"
            "_Need at least 5 reminders to analyze_"
        )
        return
    
    message = "🧠 *Smart Habit Suggestions*\n\n"
    message += "Based on your patterns, consider:\n\n"
    
    for idx, sug in enumerate(suggestions[:5], 1):
        message += f"{idx}. {sug['task'].title()}\n   Suggested: {sug['time']} daily\n\n"
    
    message += "_Tap any suggestion to create it!_"
    message += bot_engine.get_footer()
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def focus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a Pomodoro focus session (25 minutes)"""
    chat_id = update.effective_chat.id
    
    await update.message.reply_text(
        "🍅 *Focus Mode Activated!*\n\n"
        "25-minute Pomodoro session starting now.\n"
        "I'll ping you when it's break time!\n\n"
        "🎯 Stay focused! 💪"
    )
    
    # Schedule 25-minute timer
    context.job_queue.run_once(
        send_focus_complete,
        25 * 60,
        data={'chat_id': chat_id}
    )

async def send_focus_complete(context: ContextTypes.DEFAULT_TYPE):
    """Send focus session complete message"""
    chat_id = context.job.data['chat_id']
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "✅ *Focus Session Complete!*\n\n"
            "Great work! Take a 5-minute break.\n\n"
            "🧘 Stretch, hydrate, breathe 💧"
        ),
        parse_mode='Markdown'
    )

async def quick_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick reminder templates"""
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
        "⚡ *Quick Reminder Templates*\n\nPick one and set the time!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ============================================================================
# MESSAGE HANDLER - Natural Language Processing
# ============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler - Parse natural language reminders"""
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Handle button shortcuts
    button_handlers = {
        "⚡ Quick": quick_reminders,
        "📋 List": list_reminders,
        "📊 Stats": stats_command,
        "❓ Help": help_command
    }
    
    if text in button_handlers:
        await button_handlers[text](update, context)
        return
    
    # Extract metadata (category, priority, notes, etc.)
    cleaned_text, category, priority, notes, recurring, shared_with = extract_metadata(text)
    
    # Extract task and time
    task, time_str = extract_task_and_time(cleaned_text)
    
    if not task or not time_str:
        await update.message.reply_text(
            "❌ I couldn't understand that.\n\n"
            "Try: *Remind me to call mom at 5pm*\n"
            "Or: *Workout in 30 minutes #fitness*",
            parse_mode='Markdown'
        )
        return
    
    # Parse time
    current_time = bot_engine.get_current_time(chat_id)
    remind_time = parse_time(time_str, current_time)
    
    if not remind_time or remind_time <= current_time:
        await update.message.reply_text(
            "❌ Invalid time!\n\n"
            "Try: at 5pm, in 30 minutes, tomorrow at 9am",
            parse_mode='Markdown'
        )
        return
    
    # Create reminder
    reminder_id = bot_engine.add_reminder(
        chat_id, task, remind_time,
        recurring=recurring,
        category=category,
        priority=priority,
        notes=notes,
        shared_with=shared_with
    )
    
    # Check for achievements
    time_ach = bot_engine.check_time_achievements(chat_id, remind_time)
    category_ach = bot_engine.check_category_achievement(chat_id)
    
    # Schedule reminder
    delay = (remind_time - current_time).total_seconds()
    context.job_queue.run_once(
        send_reminder, delay,
        data={
            'reminder_id': reminder_id,
            'chat_id': chat_id,
            'message': task,
            'priority': priority
        }
    )
    
    # Build confirmation message
    time_until = remind_time - current_time
    hours = int(time_until.total_seconds() // 3600)
    minutes = int((time_until.total_seconds() % 3600) // 60)
    
    time_msg = ""
    if hours > 0:
        time_msg += f"{hours}h "
    if minutes > 0:
        time_msg += f"{minutes}m"
    
    confirmation = bot_engine.get_response_tone(chat_id, "confirmation")
    cat_emoji = CATEGORIES.get(category, '📌')
    pri_emoji = PRIORITIES.get(priority, '🟡')
    
    # Achievement notification
    achievement_text = ""
    if time_ach:
        achievement_text = f"\n\n🎉 *Achievement!* {time_ach['name']}\n+{time_ach['xp']} XP ✨"
    elif category_ach:
        achievement_text = f"\n\n🎉 *Achievement!* {category_ach['name']}\n+{category_ach['xp']} XP ✨"
    
    # Display time in user's timezone
    user_tz = bot_engine.get_user_timezone(chat_id)
    display_time = remind_time.astimezone(user_tz) if remind_time.tzinfo else remind_time
    
    response = (
        f"✅ *{confirmation}*\n\n"
        f"{pri_emoji} {cat_emoji} {task}\n"
        f"⏰ {display_time.strftime('%I:%M %p, %b %d')}\n"
        f"⏳ In {time_msg.strip()}"
        f"{achievement_text}"
        f"{bot_engine.get_footer()}"
    )
    
    await update.message.reply_text(response, parse_mode='Markdown')

# ============================================================================
# REMINDER DELIVERY
# ============================================================================

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send reminder notification with snooze/complete options"""
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message = job_data['message']
    priority = job_data.get('priority', 'medium')
    reminder_id = job_data.get('reminder_id')
    
    pri_emoji = PRIORITIES.get(priority, '🟡')
    ping_msg = bot_engine.get_response_tone(chat_id, "ping")
    
    # Action buttons
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
    
    # Handle recurring reminders
    if reminder_id and reminder_id in data_manager.reminders:
        rdata = data_manager.reminders[reminder_id]
        if rdata.get('recurring'):
            current_time = datetime.fromisoformat(rdata['time'])
            
            # Calculate next occurrence
            if rdata['recurring'] == 'daily':
                next_time = current_time + timedelta(days=1)
            elif rdata['recurring'] == 'weekly':
                next_time = current_time + timedelta(weeks=1)
            else:
                next_time = current_time + timedelta(days=1)
            
            # Update reminder time
            data_manager.reminders[reminder_id]['time'] = next_time.isoformat()
            data_manager.save_reminders()
            
            # Schedule next occurrence
            delay = (next_time - datetime.now()).total_seconds()
            context.job_queue.run_once(
                send_reminder, delay,
                data={
                    'reminder_id': reminder_id,
                    'chat_id': chat_id,
                    'message': message,
                    'priority': priority
                }
            )
    
    # Send notification
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 *{ping_msg}* {pri_emoji}\n\n{message}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ============================================================================
# BUTTON CALLBACKS
# ============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    
    # ------------------------------------------
    # Personality Selection
    # ------------------------------------------
    if data.startswith("personality_"):
        personality = data.replace("personality_", "")
        cid = str(chat_id)
        
        if cid not in data_manager.user_data:
            data_manager.user_data[cid] = {}
        
        data_manager.user_data[cid]['personality'] = personality
        data_manager.save_user_data()
        
        personality_name = PERSONALITIES[personality]['name']
        sample = bot_engine.get_response_tone(chat_id, "confirmation")
        
        await query.edit_message_text(
            f"✅ *Vibe Updated!*\n\n{personality_name}\n\nSample: _{sample}_",
            parse_mode='Markdown'
        )
        return
    
    # ------------------------------------------
    # Mood Tracking
    # ------------------------------------------
    if data.startswith("mood_"):
        mood = data.replace("mood_", "")
        bot_engine.save_mood(chat_id, mood)
        
        mood_responses = {
            'great': "😊 Awesome! Keep that energy!",
            'okay': "😐 Solid. Tomorrow can be better!",
            'rough': "😞 Hang in there. You've got this! 💪"
        }
        
        await query.edit_message_text(
            f"{mood_responses[mood]}\n\n_Mood saved for today_",
            parse_mode='Markdown'
        )
        return
    
    # ------------------------------------------
    # Quick Templates
    # ------------------------------------------
    if data.startswith("quick_"):
        template_key = data.replace("quick_", "")
        if template_key in TEMPLATES:
            template = TEMPLATES[template_key]
            keyboard = [
                [InlineKeyboardButton("⏰ 15 min", callback_data=f"template_{template_key}_15")],
                [InlineKeyboardButton("⏰ 30 min", callback_data=f"template_{template_key}_30")],
                [InlineKeyboardButton("⏰ 1 hour", callback_data=f"template_{template_key}_60")],
                [InlineKeyboardButton("⏰ 2 hours", callback_data=f"template_{template_key}_120")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"⚡ *{template['text']}*\n\nWhen should I remind you?",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        return
    
    # ------------------------------------------
    # Template Time Selection
    # ------------------------------------------
    if data.startswith("template_"):
        parts = data.split("_")
        template_key = parts[1]
        minutes = int(parts[2])
        
        template = TEMPLATES[template_key]
        current_time = datetime.now()
        remind_time = current_time + timedelta(minutes=minutes)
        
        reminder_id = bot_engine.add_reminder(
            chat_id, template['text'], remind_time,
            category=template['category'],
            priority='medium'
        )
        
        delay = (remind_time - current_time).total_seconds()
        if hasattr(context, 'application') and context.application.job_queue:
            context.application.job_queue.run_once(
                send_reminder, delay,
                data={
                    'reminder_id': reminder_id,
                    'chat_id': chat_id,
                    'message': template['text'],
                    'priority': 'medium'
                }
            )
        
        cat_emoji = CATEGORIES.get(template['category'], '📌')
        await query.edit_message_text(
            f"✅ *Quick Reminder Set!*\n\n{cat_emoji} {template['text']}\n⏰ In {minutes} minutes",
            parse_mode='Markdown'
        )
        return
    
    # ------------------------------------------
    # Snooze Reminder
    # ------------------------------------------
    if data.startswith("snooze_"):
        parts = data.split("_")
        reminder_id = "_".join(parts[1:-1])
        minutes = int(parts[-1])
        
        new_time = bot_engine.snooze_reminder(reminder_id, minutes)
        if new_time:
            bot_engine.update_stats(chat_id, 'snoozed')
            
            delay = (new_time - datetime.now()).total_seconds()
            if reminder_id in data_manager.reminders:
                rdata = data_manager.reminders[reminder_id]
                if hasattr(context, 'application') and context.application.job_queue:
                    context.application.job_queue.run_once(
                        send_reminder, delay,
                        data={
                            'reminder_id': reminder_id,
                            'chat_id': chat_id,
                            'message': rdata['message'],
                            'priority': rdata.get('priority', 'medium')
                        }
                    )
            
            await query.edit_message_text(
                f"⏰ *Snoozed!*\n\nI'll ping you at {new_time.strftime('%I:%M %p')}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Couldn't snooze reminder")
        return
    
    # ------------------------------------------
    # Complete Reminder
    # ------------------------------------------
    if data.startswith("complete_"):
        reminder_id = data.replace("complete_", "")
        success, achievement, level = bot_engine.complete_reminder(reminder_id)
        
        if success:
            completion_msg = bot_engine.get_response_tone(chat_id, "completion")
            
            achievement_text = ""
            if achievement:
                achievement_text = f"\n\n🎉 *{achievement['name']}*\n+{achievement['xp']} XP"
            
            await query.edit_message_text(
                f"✅ *{completion_msg}*\n\n+{XP_PER_COMPLETION} XP{achievement_text}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Reminder not found")
        return
    
    # ------------------------------------------
    # Delete Reminder
    # ------------------------------------------
    if data.startswith("delete_"):
        reminder_id = data.replace("delete_", "")
        if bot_engine.delete_reminder(reminder_id):
            await query.edit_message_text("🗑️ *Deleted!*", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Reminder not found")
        return
    
    # ------------------------------------------
    # Dismiss Reminder
    # ------------------------------------------
    if data.startswith("dismiss_"):
        reminder_id = data.replace("dismiss_", "")
        bot_engine.delete_reminder(reminder_id)
        await query.edit_message_text("👋 *Dismissed*", parse_mode='Markdown')
        return

# ============================================================================
# BOT INITIALIZATION
# ============================================================================

async def reschedule_reminders(application):
    """Reschedule all pending reminders on bot restart"""
    current_time = datetime.now()
    rescheduled = 0
    expired = 0
    
    logger.info("🔄 Rescheduling reminders...")
    
    for reminder_id, rdata in list(data_manager.reminders.items()):
        if rdata.get('completed'):
            continue
        
        try:
            remind_time = datetime.fromisoformat(rdata['time'])
            
            # Make timezone-aware if needed
            if remind_time.tzinfo is None:
                remind_time = DEFAULT_TIMEZONE.localize(remind_time)
            
            if remind_time > current_time:
                delay = (remind_time - current_time).total_seconds()
                application.job_queue.run_once(
                    send_reminder,
                    delay,
                    data={
                        'reminder_id': reminder_id,
                        'chat_id': rdata['chat_id'],
                        'message': rdata['message'],
                        'priority': rdata.get('priority', 'medium')
                    }
                )
                rescheduled += 1
            else:
                # Delete expired non-recurring reminders
                if not rdata.get('recurring'):
                    bot_engine.delete_reminder(reminder_id)
                    expired += 1
        
        except Exception as e:
            logger.error(f"Error rescheduling reminder {reminder_id}: {e}")
    
    logger.info(f"✅ Rescheduled {rescheduled} reminders")
    logger.info(f"🗑️ Cleaned up {expired} expired reminders")

def main():
    """Initialize and run MemoryPing v4.0"""
    
    # Get bot token from environment
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        logger.error("=" * 60)
        logger.error("❌ BOT_TOKEN environment variable not found!")
        logger.error("=" * 60)
        logger.error("Please set it with:")
        logger.error("  export BOT_TOKEN='your_bot_token_here'")
        logger.error("")
        logger.error("Get your token from @BotFather on Telegram")
        logger.error("=" * 60)
        return
    
    logger.info(f"🔑 Bot token loaded: {TOKEN[:10]}...{TOKEN[-5:]}")
    
    try:
        # Build application with extended timeouts
        application = (
            Application.builder()
            .token(TOKEN)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .pool_timeout(30.0)
            .build()
        )
        
        # ================================================
        # Register Command Handlers
        # ================================================
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("personality", personality_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("today", today_reminders))
        application.add_handler(CommandHandler("list", list_reminders))
        application.add_handler(CommandHandler("digest", digest_command))
        application.add_handler(CommandHandler("reflect", reflect_command))
        application.add_handler(CommandHandler("habits", habits_command))
        application.add_handler(CommandHandler("focus", focus_command))
        application.add_handler(CommandHandler("quick", quick_reminders))
        
        # Message and callback handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Set post-init hook for rescheduling reminders
        application.post_init = reschedule_reminders
        
        # ================================================
        # Startup Banner
        # ================================================
        logger.info("\n" + "=" * 60)
        logger.info("🧠 MemoryPing v4.0 - The Intelligent Companion")
        logger.info("=" * 60)
        logger.info("✨ Created by Achu Vijayakumar")
        logger.info("")
        logger.info("📋 Active Systems:")
        logger.info("  ✅ Personality Engine (4 personalities)")
        logger.info("  ✅ XP & Leveling System")
        logger.info("  ✅ Smart Habit Detection")
        logger.info("  ✅ Mood Tracking & Reflection")
        logger.info("  ✅ Achievement System (9 badges)")
        logger.info("  ✅ Natural Language Parser")
        logger.info("  ✅ Recurring Reminders")
        logger.info("  ✅ Daily Digest")
        logger.info("  ✅ Pomodoro Focus Timer")
        logger.info("  ✅ Memory Score Algorithm")
        logger.info("")
        logger.info("🎮 Gamification:")
        logger.info(f"  • XP per completion: {XP_PER_COMPLETION}")
        logger.info(f"  • XP per level: {XP_PER_LEVEL}")
        logger.info(f"  • Max memory score: 1000")
        logger.info("")
        logger.info("🎭 Personalities:")
        logger.info("  • Zen Monk 🧘")
        logger.info("  • Coach 🏋️")
        logger.info("  • Bestie 💖")
        logger.info("  • Tech Bro 🤓")
        logger.info("")
        logger.info("📊 Data Files:")
        logger.info(f"  • Reminders: {REMINDERS_FILE}")
        logger.info(f"  • User Data: {USER_DATA_FILE}")
        logger.info(f"  • Statistics: {STATS_FILE}")
        logger.info(f"  • Habits: {HABITS_FILE}")
        logger.info(f"  • Moods: {MOODS_FILE}")
        logger.info("")
        logger.info("🎯 Bot is ready to serve!")
        logger.info("🌐 Using external keep-alive (recommended: UptimeRobot)")
        logger.info("=" * 60 + "\n")
        
        # ================================================
        # Run with Auto-Restart on Errors
        # ================================================
        while True:
            try:
                logger.info("🚀 Starting polling...")
                application.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                    pool_timeout=30
                )
            except KeyboardInterrupt:
                logger.info("\n🛑 Bot stopped by user (Ctrl+C)")
                logger.info("👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"❌ Bot error: {e}")
                logger.error("🔄 Auto-restarting in 5 seconds...")
                asyncio.run(asyncio.sleep(5))
                logger.info("♻️ Restarting bot...")
                continue
    
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Failed to start bot: {e}")
        logger.error("=" * 60)
        raise

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    main()