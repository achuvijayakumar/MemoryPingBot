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
from threading import Thread, Lock
from flask import Flask
from typing import Dict, List, Optional, Tuple
# ============================================================================
# TIME PARSING & NLP
# ============================================================================

def parse_time(time_str: str, current_time: datetime) -> Optional[datetime]:
    """Enhanced NLP time parser with natural language support"""
    time_str = time_str.lower().strip()
    is_tomorrow = "tomorrow" in time_str
    time_str = time_str.replace("tomorrow", "").strip()
    
    # Ensure timezone-aware
    if current_time.tzinfo is None:
        current_time = DEFAULT_TIMEZONE.localize(current_time)
    
    # Special time phrases
    special_times = {
        'lunch': 13, 'after lunch': 13,
        'bedtime': 22, 'before bed': 22,
        'evening': 18, 'afternoon': 14, 'morning': 8
    }
    
    for phrase, hour in special_times.items():
        if phrase in time_str:
            remind_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            if is_tomorrow or remind_time <= current_time:
                remind_time += timedelta(days=1)
            return remind_time
    
    # "in 2h 30m" format
    complex_pattern = r'(?:in|after)\s+(?:(\d+)\s*(?:hours?|hrs?|h))?\s*(?:(\d+)\s*(?:minutes?|mins?|min|m))?'
    match = re.search(complex_pattern, time_str)
    if match and (match.group(1) or match.group(2)):
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        return current_time + timedelta(hours=hours, minutes=minutes)
    
    # AM/PM format
    ampm_pattern = r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)'
    match = re.search(ampm_pattern, time_str)
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
    
    # 24-hour format
    at_pattern = r'at\s+(\d{1,2}):(\d{2})(?!\s*[ap]m)'
    match = re.search(at_pattern, time_str)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        remind_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if is_tomorrow or remind_time <= current_time:
            remind_time += timedelta(days=1)
        return remind_time
    
    return None

def extract_task_and_time(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract task and time from natural language"""
    text_lower = text.lower()
    
    triggers = [
        r'remind\s+me\s+to\s+', r'send\s+me\s+(?:a\s+)?', r'tell\s+me\s+(?:to\s+)?',
        r'ping\s+me\s+(?:about\s+|to\s+)?', r'alert\s+me\s+(?:about\s+|to\s+)?',
        r'remember\s+(?:to\s+)?', r'notify\s+me\s+(?:about\s+|to\s+)?'
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
    
    # Fallback without trigger
    time_match = re.search(r'\s+(?:at|in|after)\s+', text_lower)
    if time_match:
        task = text[:time_match.start()].strip()
        time_str = text[time_match.start():].strip()
        if task:
            return task, time_str
    
    return None, None

def extract_metadata(text: str) -> Tuple[str, str, str, str, Optional[str], List[str]]:
    """Extract category, priority, notes, recurring, shared users"""
    category, priority, notes, recurring = 'other', 'medium', '', None
    shared_with = []
    
    # Category
    cat_match = re.search(r'#(\w+)', text)
    if cat_match and cat_match.group(1).lower() in CATEGORIES:
        category = cat_match.group(1).lower()
        text = text.replace(cat_match.group(0), '')
    
    # Priority
    pri_match = re.search(r'!(high|medium|low)', text, re.IGNORECASE)
    if pri_match:
        priority = pri_match.group(1).lower()
        text = text.replace(pri_match.group(0), '')
    
    # Notes
    notes_match = re.search(r'--\s*(.+?)(?:\s+#|\s+!|$)', text)
    if notes_match:
        notes = notes_match.group(1).strip()
        text = text[:notes_match.start()] + text[notes_match.end():]
    
    # Recurring
    recurring_patterns = [
        (r'every\s+day|daily', 'daily'),
        (r'every\s+week(?:ly)?', 'weekly'),
        (r'every\s+month(?:ly)?', 'monthly'),
        (r'every\s+weekday', 'weekday'),
        (r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', 'weekly')
    ]
    for pattern, recur_type in recurring_patterns:
        if re.search(pattern, text.lower()):
            recurring = recur_type
            break
    
    # Shared users
    shared_matches = re.findall(r'@(\w+)', text)
    if shared_matches:
        shared_with = shared_matches
    
    return text.strip(), category, priority, notes, recurring, shared_with

# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with v4.0 features"""
    await update.message.chat.send_action(ChatAction.TYPING)
    
    keyboard = [
        [KeyboardButton("⚡ Quick"), KeyboardButton("📋 List"), KeyboardButton("📅 Today")],
        [KeyboardButton("📊 Stats"), KeyboardButton("🎭 Vibe"), KeyboardButton("🏆 Badges")],
        [KeyboardButton("❓ Help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome = (
        "🧠 *Welcome to MemoryPing v4.0!*\n"
        "_The Intelligent Companion_\n\n"
        "I'm your productivity partner that learns, celebrates, and grows with you! 🎯\n\n"
        "*🌟 What's New:*\n"
        "• 🎭 4 unique vibes (personalities)\n"
        "• 📈 XP & leveling system\n"
        "• 🧠 Smart habit detection\n"
        "• 😊 Mood tracking\n"
        "• 🏆 13 achievements\n"
        "• 💬 Enhanced natural language\n\n"
        "*Quick Start:*\n"
        "Just talk naturally!\n"
        "_'Remind me to call mom at 5pm'_\n\n"
        "Try /personality to pick your vibe! 🎭\n\n"
        "_Created with ❤️ by Achu Vijayakumar_"
    )
    
    await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comprehensive help guide"""
    await update.message.chat.send_action(ChatAction.TYPING)
    
    help_text = (
        "📖 *MemoryPing v4.0 Guide*\n\n"
        "*🎯 Core Commands:*\n"
        "/personality - Choose your bot's vibe\n"
        "/stats - XP, level & memory score\n"
        "/achievements - Your badge collection\n"
        "/today - Today's schedule\n"
        "/digest - Daily summary\n"
        "/reflect - Mood journal\n"
        "/leaderboard - Top users by XP\n\n"
        "*💬 Natural Language:*\n"
        "• Workout at 6am tomorrow\n"
        "• Meeting in 2h 30m #work !high\n"
        "• Take medicine every day at 9am\n"
        "• Call mom after lunch\n\n"
        "*🎨 Tags:*\n"
        "#work #health #family #fitness\n"
        "!high !medium !low\n"
        "-- Add notes\n"
        "@user to share\n\n"
        "_Made with ❤️ by Achu Vijayakumar_"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ========================================================================
# PERSONALITY COMMANDS
# ========================================================================

async def personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Let user choose personality"""
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
        f"🎭 *Choose Your Vibe*\n\nCurrent: {current_name}\n\nPick a personality that vibes with you!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ========================================================================
# STATS & XP COMMANDS
# ========================================================================

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced stats with XP, level, memory score"""
    chat_id = update.effective_chat.id
    await update.message.chat.send_action(ChatAction.TYPING)
    
    chat_id_str = str(chat_id)
    if chat_id_str not in data_manager.stats:
        await update.message.reply_text(
            f"📊 *Start Your Journey!*\n\nCreate reminders to track progress!{bot_engine.get_footer()}",
            parse_mode='Markdown'
        )
        return
    
    stats = data_manager.stats[chat_id_str]
    xp = bot_engine.get_user_xp(chat_id)
    level = bot_engine.get_user_level(chat_id)
    memory_score = bot_engine.calculate_memory_score(chat_id)
    
    xp_for_next = (level * XP_PER_LEVEL) - xp
    created = stats.get('created', 0)
    completed = stats.get('completed', 0)
    completion_rate = (completed / created * 100) if created > 0 else 0
    
    xp_bar = bot_engine.format_progress_bar((xp % XP_PER_LEVEL) / XP_PER_LEVEL * 100)
    completion_bar = bot_engine.format_progress_bar(completion_rate)
    
    personality = bot_engine.get_user_personality(chat_id)
    personality_name = PERSONALITIES[personality]['name']
    streak = bot_engine.get_streak(chat_id)
    
    message = (
        f"📊 *Your Profile*\n{'=' * 25}\n\n"
        f"⭐ *Level {level}* | 💎 {xp} XP\n"
        f"{xp_bar} ({xp_for_next} to Level {level + 1})\n\n"
        f"🧠 *Memory Score: {memory_score}/1000*\n\n"
        f"📝 Created: {created} | ✅ Completed: {completed}\n"
        f"🎯 Completion: {completion_rate:.1f}%\n"
        f"{completion_bar}\n\n"
        f"🔥 Streak: {streak} days | 🎭 Vibe: {personality_name}\n"
        f"{'=' * 25}"
    )
    
    # Category breakdown
    reminders = bot_engine.get_user_reminders(chat_id)
    if reminders:
        category_count = defaultdict(int)
        for reminder_data in reminders.values():
            category_count[reminder_data.get('category', 'other')] += 1
        
        message += f"\n\n*📂 Active Reminders:*\n"
        for cat, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            emoji = CATEGORIES.get(cat, '📌')
            bar = "▪" * min(count, 10)
            message += f"{emoji} {cat}: {bar} {count}\n"
    
    message += bot_engine.get_footer()
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show achievement gallery"""
    chat_id = update.effective_chat.id
    chat_id_str = str(chat_id)
    
    user_achievements = data_manager.user_data.get(chat_id_str, {}).get('achievements', [])
    
    message = "🏆 *Achievement Gallery*\n" + "=" * 25 + "\n\n"
    unlocked_xp = 0
    
    for ach_id, ach_data in ACHIEVEMENTS.items():
        status = "✅" if ach_id in user_achievements else "🔒"
        message += f"{status} {ach_data['name']}\n_{ach_data['desc']}_\n"
        if ach_id in user_achievements:
            unlocked_xp += ach_data['xp']
        message += "\n"
    
    message += f"{'=' * 25}\n*Unlocked: {len(user_achievements)}/{len(ACHIEVEMENTS)}*\n"
    message += f"Total XP: {unlocked_xp}\n{bot_engine.get_footer()}"
    
    parts = bot_engine.split_long_message(message)
    for part in parts:
        await update.message.reply_text(part, parse_mode='Markdown')

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """XP leaderboard"""
    await update.message.chat.send_action(ChatAction.TYPING)
    
    leaderboard = [
        {'xp': stats.get('xp', 0), 'level': max(1, stats.get('xp', 0) // XP_PER_LEVEL + 1), 'id': cid}
        for cid, stats in data_manager.stats.items()
    ]
    leaderboard.sort(key=lambda x: x['xp'], reverse=True)
    
    if not leaderboard:
        await update.message.reply_text("🏆 Leaderboard is empty!")
        return
    
    message = "🏆 *MemoryPing Leaderboard*\n" + "=" * 25 + "\n\n"
    current_user_id = str(update.effective_chat.id)
    
    for idx, entry in enumerate(leaderboard[:10], 1):
        medal = ["🥇", "🥈", "🥉"][idx - 1] if idx <= 3 else f"{idx}."
        
        if entry['id'] == current_user_id:
            message += f"{medal} *YOU* - Level {entry['level']} ({entry['xp']} XP) ⭐\n"
        else:
            message += f"{medal} User #{entry['id'][:8]} - Level {entry['level']} ({entry['xp']} XP)\n"
    
    user_rank = next((i for i, e in enumerate(leaderboard, 1) if e['id'] == current_user_id), None)
    if user_rank and user_rank > 10:
        user_xp = bot_engine.get_user_xp(update.effective_chat.id)
        user_level = bot_engine.get_user_level(update.effective_chat.id)
        message += f"\n...\n{user_rank}. *YOU* - Level {user_level} ({user_xp} XP)\n"
    
    message += bot_engine.get_footer()
    
    await update.message.reply_text(message, parse_mode='Markdown')

# ========================================================================
# DIGEST & REFLECTION
# ========================================================================

async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Daily digest"""
    chat_id = update.effective_chat.id
    await update.message.chat.send_action(ChatAction.TYPING)
    
    current_time = bot_engine.get_current_time(chat_id)
    stats = data_manager.stats.get(str(chat_id), {})
    reminders = bot_engine.get_user_reminders(chat_id)
    
    xp = bot_engine.get_user_xp(chat_id)
    level = bot_engine.get_user_level(chat_id)
    memory_score = bot_engine.calculate_memory_score(chat_id)
    
    # Upcoming 24h
    next_24h = current_time + timedelta(hours=24)
    upcoming = []
    
    for rid, reminder_data in reminders.items():
        remind_time = datetime.fromisoformat(reminder_data['time'])
        if remind_time.tzinfo is None:
            remind_time = DEFAULT_TIMEZONE.localize(remind_time)
        if current_time <= remind_time <= next_24h:
            upcoming.append((rid, reminder_data, remind_time))
    
    upcoming.sort(key=lambda x: x[2])
    
    message = (
        f"📊 *Daily Digest* - {current_time.strftime('%B %d')}\n"
        f"{'=' * 30}\n\n"
        f"⭐ Level {level} | 💎 {xp} XP | 🧠 Score: {memory_score}\n\n"
        f"📝 Active: {len(reminders)} | ✅ Completed: {stats.get('completed', 0)}\n\n"
        f"*📅 Next 24h:* {len(upcoming)} reminders\n\n"
    )
    
    if upcoming:
        for idx, (_, reminder_data, remind_time) in enumerate(upcoming[:5], 1):
            cat_emoji = CATEGORIES.get(reminder_data.get('category', 'other'), '📌')
            message += f"{idx}. {cat_emoji} {reminder_data['message']}\n   ⏰ {remind_time.strftime('%I:%M %p')}\n"
        
        if len(upcoming) > 5:
            message += f"\n...and {len(upcoming) - 5} more\n"
    
    message += bot_engine.get_footer()
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def reflect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mood journal"""
    chat_id = update.effective_chat.id
    moods = bot_engine.get_recent_moods(chat_id, 7)
    
    if not moods:
        await update.message.reply_text(
            "😊 *Mood Journal*\n\nNo entries yet!\n\n"
            "I'll ask about your mood in the evening digest.",
            parse_mode='Markdown'
        )
        return
    
    mood_emoji_map = {'happy': '😊', 'neutral': '😐', 'sad': '😞'}
    
    message = "😊 *Your Mood Journal*\n" + "=" * 25 + "\n\n"
    
    for entry in moods:
        emoji = mood_emoji_map.get(entry['mood'], '😐')
        message += f"{emoji} *{entry['date']}*\n"
        if entry.get('note'):
            message += f"_{entry['note']}_\n"
        message += "\n"
    
    message += bot_engine.get_footer()
    
    await update.message.reply_text(message, parse_mode='Markdown')

# ========================================================================
# REMINDER MANAGEMENT
# ========================================================================

async def today_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Today's schedule"""
    chat_id = update.effective_chat.id
    await update.message.chat.send_action(ChatAction.TYPING)
    
    reminders = bot_engine.get_user_reminders(chat_id)
    current_time = bot_engine.get_current_time(chat_id)
    
    today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = current_time.replace(hour=23, minute=59, second=59)
    
    today_reminders = {}
    for rid, reminder_data in reminders.items():
        remind_time = datetime.fromisoformat(reminder_data['time'])
        if remind_time.tzinfo is None:
            remind_time = DEFAULT_TIMEZONE.localize(remind_time)
        if today_start <= remind_time <= today_end:
            today_reminders[rid] = (reminder_data, remind_time)
    
    if not today_reminders:
        response = bot_engine.get_response_tone(chat_id, "confirmation")
        await update.message.reply_text(
            f"📅 *Today's Schedule*\n\n{response}\n\nNo reminders! Enjoy your free time! 🎉"
        )
        return
    
    message = f"📅 *Today* - {current_time.strftime('%B %d')}\n" + "=" * 25 + "\n\n"
    
    sorted_reminders = sorted(today_reminders.items(), key=lambda x: x[1][1])
    
    for idx, (rid, (reminder_data, remind_time)) in enumerate(sorted_reminders, 1):
        cat_emoji = CATEGORIES.get(reminder_data.get('category', 'other'), '📌')
        pri_emoji = PRIORITIES.get(reminder_data.get('priority', 'medium'), '🟡')
        
        message += f"{idx}. {cat_emoji} {pri_emoji} {reminder_data['message']}\n"
        message += f"   ⏰ {remind_time.strftime('%I:%M %p')}\n\n"
    
    message += bot_engine.get_footer()
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def missed_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show overdue reminders"""
    chat_id = update.effective_chat.id
    reminders = bot_engine.get_user_reminders(chat_id)
    current_time = bot_engine.get_current_time(chat_id)
    
    missed = {}
    for rid, reminder_data in reminders.items():
        remind_time = datetime.fromisoformat(reminder_data['time'])
        if remind_time.tzinfo is None:
            remind_time = DEFAULT_TIMEZONE.localize(remind_time)
        if remind_time < current_time:
            missed[rid] = (reminder_data, remind_time)
    
    if not missed:
        await update.message.reply_text("✅ No missed reminders! You're all caught up!")
        return
    
    message = "⚠️ *Overdue Reminders*\n" + "=" * 25 + "\n\n"
    
    for idx, (rid, (reminder_data, remind_time)) in enumerate(sorted(missed.items(), key=lambda x: x[1][1]), 1):
        time_ago = current_time - remind_time
        hours_ago = int(time_ago.total_seconds() // 3600)
        
        message += f"{idx}. {reminder_data['message']}\n   ⏰ {hours_ago}h ago\n\n"
    
    message += bot_engine.get_footer()
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def focus_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """25-min Pomodoro focus session"""
    await update.message.reply_text(
        "🎯 *Focus Mode!*\n\n25 minutes of deep work starts now.\n\nStay focused! 💪"
    )
    
    context.job_queue.run_once(
        lambda ctx: ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🎉 *Session Complete!*\n\nGreat work! Take a 5-min break.\n\nStretch & hydrate! 💧",
            parse_mode='Markdown'
        ),
        25 * 60
    )

async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Random motivational quote"""
    quote = random.choice(MOTIVATIONAL_QUOTES)
    await update.message.reply_text(f"💭 *Daily Motivation*\n\n_{quote}_\n\n✨ Keep pushing!")

async def quick_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick templates"""
    keyboard = [
        [InlineKeyboardButton("💊 Medicine", callback_data="quick_medicine")],
        [InlineKeyboardButton("💧 Water", callback_data="quick_water")],
        [InlineKeyboardButton("💪 Exercise", callback_data="quick_exercise")],
        [InlineKeyboardButton("🧍 Stretch", callback_data="quick_standup")],
        [InlineKeyboardButton("📞 Family", callback_data="quick_call_family")],
        [InlineKeyboardButton("📧 Email", callback_data="quick_check_email")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚡ *Quick Templates*\n\nPick one!{bot_engine.get_footer()}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all reminders"""
    chat_id = update.effective_chat.id
    await update.message.chat.send_action(ChatAction.TYPING)
    
    reminders = bot_engine.get_user_reminders(chat_id)
    
    if not reminders:
        await update.message.reply_text(
            f"📭 No active reminders!{bot_engine.get_footer()}",
            parse_mode='Markdown'
        )
        return
    
    by_category = defaultdict(list)
    for rid, reminder_data in reminders.items():
        by_category[reminder_data.get('category', 'other')].append((rid, reminder_data))
    
    message = "📋 *Your Reminders*\n" + "=" * 25 + "\n\n"
    keyboard = []
    
    idx = 1
    for category, items in sorted(by_category.items()):
        cat_emoji = CATEGORIES.get(category, '📌')
        message += f"{cat_emoji} *{category.upper()}*\n"
        
        for rid, reminder_data in sorted(items, key=lambda x: x[1]['time']):
            remind_time = datetime.fromisoformat(reminder_data['time'])
            pri_emoji = PRIORITIES.get(reminder_data.get('priority', 'medium'), '🟡')
            recurring_icon = " 🔄" if reminder_data.get('recurring') else ""
            
            message += f"{idx}. {pri_emoji} {reminder_data['message']}{recurring_icon}\n"
            message += f"   ⏰ {remind_time.strftime('%I:%M %p, %b %d')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ #{idx}", callback_data=f"complete_{rid}"),
                InlineKeyboardButton(f"❌ #{idx}", callback_data=f"delete_{rid}")
            ])
            idx += 1
    
    message += bot_engine.get_footer()
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    parts = bot_engine.split_long_message(message)
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            await update.message.reply_text(part, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await update.message.reply_text(part, parse_mode='Markdown')

# ========================================================================
# MESSAGE HANDLER
# ========================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler with NLP and habit detection"""
    text = update.message.text
    chat_id = update.effective_chat.id
    
    # Menu buttons
    button_handlers = {
        "⚡ Quick": quick_reminders,
        "📋 List": list_reminders,
        "📅 Today": today_reminders,
        "📊 Stats": stats_command,
        "🎭 Vibe": personality_command,
        "🏆 Badges": achievements_command,
        "❓ Help": help_command
    }
    
    if text in button_handlers:
        await button_handlers[text](update, context)
        return
    
    # Easter eggs
    if "thank" in text.lower():
        await update.message.reply_text("💖 You're welcome! Happy to help!")
        return
    
    if "lazy" in text.lower():
        easter_eggs = {
            'zen': "Laziness is just energy waiting for purpose. 🧘",
            'coach': "LAZY?! Not on my watch! Get up and move! 💪",
            'bestie': "Bestie no! You got this! Let's goooo! ✨",
            'techbro': "Lazy = low optimization. Time to refactor. 🤓"
        }
        personality = bot_engine.get_user_personality(chat_id)
        await update.message.reply_text(easter_eggs.get(personality, "Let's turn that around! 💪"))
        return
    
    # Parse reminder
    cleaned_text, category, priority, notes, recurring, shared_with = extract_metadata(text)
    task, time_str = extract_task_and_time(cleaned_text)
    
    if not task or not time_str:
        await update.message.reply_text(
            "❌ I couldn't understand that.\n\n"
            "Try: *Remind me to call mom at 5pm*\n"
            "Or: *Meeting in 2h #work !high*",
            parse_mode='Markdown'
        )
        return
    
    current_time = bot_engine.get_current_time(chat_id)
    remind_time = parse_time(time_str, current_time)
    
    if not remind_time:
        await update.message.reply_text(
            "🤔 When should I remind you?\n\n"
            "Try: at 5pm, in 30min, tomorrow 9am, after lunch",
            parse_mode='Markdown'
        )
        return
    
    if remind_time <= current_time:
        await update.message.reply_text("❌ That time is in the past!")
        return
    
    # Create reminder
    reminder_id = bot_engine.add_reminder(
        chat_id, task, remind_time,
        recurring=recurring, category=category,
        priority=priority, notes=notes, shared_with=shared_with
    )
    
    # Check achievements
    time_ach = bot_engine.check_time_achievements(chat_id, remind_time)
    cat_ach = bot_engine.check_category_achievement(chat_id)
    
    # Schedule job
    delay = (remind_time - current_time).total_seconds()
    context.job_queue.run_once(
        send_reminder, delay,
        data={'reminder_id': reminder_id, 'chat_id': chat_id, 'message': task, 'priority': priority}
    )
    
    # Build response
    time_until = remind_time - current_time
    hours = int(time_until.total_seconds() // 3600)
    minutes = int((time_until.total_seconds() % 3600) // 60)
    time_msg = f"{hours}h " if hours > 0 else ""
    time_msg += f"{minutes}m" if minutes > 0 else ""
    
    confirmation = bot_engine.get_response_tone(chat_id, "confirmation")
    cat_emoji = CATEGORIES.get(category, '📌')
    pri_emoji = PRIORITIES.get(priority, '🟡')
    
    recurring_text = f"\n🔄 {recurring.title()}" if recurring else ""
    notes_text = f"\n📝 {notes}" if notes else ""
    
    achievement_text = ""
    if time_ach:
        achievement_text = f"\n\n🎉 *Achievement!* {time_ach['name']}\n+{time_ach['xp']} XP"
    elif cat_ach:
        achievement_text = f"\n\n🎉 *Achievement!* {cat_ach['name']}\n+{cat_ach['xp']} XP"
    
    # Habit suggestions
    suggestions = bot_engine.analyze_habits(chat_id)
    suggestion_text = ""
    if suggestions and len(suggestions) > 0:
        sug = suggestions[0]
        if sug['type'] == 'recurring':
            suggestion_text = f"\n\n💡 *Habit detected!* You often set '{sug['task']}'. Make it recurring?"
    
    user_tz = bot_engine.get_user_timezone(chat_id)
    display_time = remind_time.astimezone(user_tz) if remind_time.tzinfo else remind_time
    
    response = (
        f"✅ *{confirmation}*\n\n"
        f"{pri_emoji} {task}\n"
        f"{cat_emoji} {category.title()}\n"
        f"⏰ {display_time.strftime('%I:%M %p, %b %d')}\n"
        f"⏳ In {time_msg.strip()}"
        f"{recurring_text}{notes_text}{achievement_text}{suggestion_text}"
        f"{bot_engine.get_footer()}"
    )
    
    await update.message.reply_text(response, parse_mode='Markdown')

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send reminder with personality"""
    job_data = context.job.data
    chat_id = job_data['chat_id']
    message = job_data['message']
    priority = job_data.get('priority', 'medium')
    reminder_id = job_data.get('reminder_id')
    
    pri_emoji = PRIORITIES.get(priority, '🟡')
    ping_msg = bot_engine.get_response_tone(chat_id, "ping")
    
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
    
    # Handle recurring
    if reminder_id and reminder_id in data_manager.reminders:
        reminder_data = data_manager.reminders[reminder_id]
        if reminder_data.get('recurring'):
            current_time = datetime.fromisoformat(reminder_data['time'])
            
            if reminder_data['recurring'] == 'daily':
                next_time = current_time + timedelta(days=1)
            elif reminder_data['recurring'] == 'weekly':
                next_time = current_time + timedelta(weeks=1)
            elif reminder_data['recurring'] == 'monthly':
                next_time = current_time + timedelta(days=30)
            elif reminder_data['recurring'] == 'weekday':
                next_time = current_time + timedelta(days=1)
                while next_time.weekday() >= 5:
                    next_time += timedelta(days=1)
            
            data_manager.reminders[reminder_id]['time'] = next_time.isoformat()
            data_manager.save_reminders()
            
            delay = (next_time - datetime.now()).total_seconds()
            context.job_queue.run_once(
                send_reminder, delay,
                data={'reminder_id': reminder_id, 'chat_id': chat_id, 'message': message, 'priority': priority}
            )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 *{ping_msg}* {pri_emoji}\n\n{message}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ========================================================================
# CALLBACK HANDLER
# ========================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    
    # Personality selection
    if data.startswith("personality_"):
        personality = data.replace("personality_", "")
        chat_id_str = str(chat_id)
        
        if chat_id_str not in data_manager.user_data:
            data_manager.user_data[chat_id_str] = {}
        
        data_manager.user_data[chat_id_str]['personality'] = personality
        data_manager.save_user_data()
        
        personality_name = PERSONALITIES[personality]['name']
        sample = bot_engine.get_response_tone(chat_id, "confirmation")
        
        await query.edit_message_text(
            f"✅ *Vibe Updated!*\n\n{personality_name}\n\nSample: _{sample}_",
            parse_mode='Markdown'
        )
        return
    
    # Quick templates
    if data.startswith("quick_"):
        template_key = data.replace("quick_", "")
        if template_key in TEMPLATES:
            template = TEMPLATES[template_key]
            keyboard = [
                [InlineKeyboardButton("⏰ 15min", callback_data=f"template_{template_key}_15")],
                [InlineKeyboardButton("⏰ 30min", callback_data=f"template_{template_key}_30")],
                [InlineKeyboardButton("⏰ 1hr", callback_data=f"template_{template_key}_60")],
                [InlineKeyboardButton("⏰ 2hr", callback_data=f"template_{template_key}_120")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"⚡ *{template['text']}*\n\nWhen?",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    elif data.startswith("template_"):
        parts = data.split("_")
        template_key, minutes = parts[1], int(parts[2])
        
        template = TEMPLATES[template_key]
        current_time = datetime.now()
        remind_time = current_time + timedelta(minutes=minutes)
        
        reminder_id = bot_engine.add_reminder(
            chat_id, template['text'], remind_time,
            category=template['category'], priority='medium'
        )
        
        delay = (remind_time - current_time).total_seconds()
        if hasattr(context, 'application') and context.application.job_queue:
            context.application.job_queue.run_once(
                send_reminder, delay,
                data={'reminder_id': reminder_id, 'chat_id': chat_id, 'message': template['text'], 'priority': 'medium'}
            )
        
        confirmation = bot_engine.get_response_tone(chat_id, "confirmation")
        await query.edit_message_text(f"✅ *{confirmation}*\n\n{template['text']}\n⏰ In {minutes}min", parse_mode='Markdown')
    
    # Snooze
    elif data.startswith("snooze_"):
        parts = data.split("_")
        reminder_id = "_".join(parts[1:-1])
        minutes = int(parts[-1])
        
        new_time = bot_engine.snooze_reminder(reminder_id, minutes)
        if new_time:
            bot_engine.update_stats(chat_id, 'snoozed')
            
            delay = (new_time - datetime.now()).total_seconds()
            if reminder_id in data_manager.reminders:
                reminder_data = data_manager.reminders[reminder_id]
                if hasattr(context, 'application') and context.application.job_queue:
                    context.application.job_queue.run_once(
                        send_reminder, delay,
                        data={'reminder_id': reminder_id, 'chat_id': chat_id, 'message': reminder_data['message'], 'priority': reminder_data.get('priority', 'medium')}
                    )
            
            await query.edit_message_text(f"⏰ *Snoozed!*\n\nI'll ping at {new_time.strftime('%I:%M %p')}", parse_mode='Markdown')
    
    # Complete
    elif data.startswith("complete_"):
        reminder_id = data.replace("complete_", "")
        success, achievement, level = bot_engine.complete_reminder(reminder_id)
        
        if success:
            completion_msg = bot_engine.get_response_tone(chat_id, "completion")
            
            ach_text = ""
            if achievement:
                ach_text = f"\n\n🎉 {achievement['name']}\n+{achievement['xp']} XP"
            
            await query.edit_message_text(
                f"✅ *{completion_msg}*\n\n+{XP_PER_COMPLETION} XP{ach_text}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Not found")
    
    # Delete
    elif data.startswith("delete_"):
        reminder_id = data.replace("delete_", "")
        if bot_engine.delete_reminder(reminder_id):
            await query.edit_message_text("🗑️ Deleted!")
        else:
            await query.edit_message_text("❌ Not found")
    
    # Dismiss
    elif data.startswith("dismiss_"):
        reminder_id = data.replace("dismiss_", "")
        bot_engine.delete_reminder(reminder_id)
        await query.edit_message_text("👋 Dismissed")

# ========================================================================
# INITIALIZATION
# ========================================================================

async def reschedule_reminders(application):
    """Reschedule reminders on restart"""
    current_time = datetime.now()
    
    for reminder_id, reminder_data in list(data_manager.reminders.items()):
        if reminder_data.get('completed'):
            continue
        
        remind_time = datetime.fromisoformat(reminder_data['time'])
        
        if remind_time > current_time:
            delay = (remind_time - current_time).total_seconds()
            application.job_queue.run_once(
                send_reminder,
                delay,
                data={
                    'reminder_id': reminder_id,
                    'chat_id': reminder_data['chat_id'],
                    'message': reminder_data['message'],
                    'priority': reminder_data.get('priority', 'medium')
                }
            )
        else:
            if not reminder_data.get('recurring'):
                bot_engine.delete_reminder(reminder_id)

def main():
    """Initialize and run MemoryPing v4.0"""
    keep_alive()
    
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN not found!")
        return
    
    print(f"🔑 Token: {TOKEN[:10]}...{TOKEN[-5:]}")
    print(f"🌐 Flask: port {os.getenv('PORT', 8080)}")
    
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("personality", personality_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("achievements", achievements_command))
    application.add_handler(CommandHandler("reflect", reflect_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CommandHandler("today", today_reminders))
    application.add_handler(CommandHandler("missed", missed_reminders))
    application.add_handler(CommandHandler("digest", digest_command))
    application.add_handler(CommandHandler("focus", focus_mode))
    application.add_handler(CommandHandler("quote", quote_command))
    application.add_handler(CommandHandler("quick", quick_reminders))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.post_init = reschedule_reminders
    
    print("\n" + "=" * 50)
    print("🧠 MemoryPing v4.0 - The Intelligent Companion")
    print("=" * 50)
    print("✨ Created by Achu Vijayakumar")
    print("\n📋 Systems Active:")
    print("  ✅ Personality Engine (4 vibes)")
    print("  ✅ XP & Level System")
    print("  ✅ Smart Habit Detection")
    print("  ✅ Mood Tracking")
    print("  ✅ Achievement System (13 badges)")
    print("  ✅ Enhanced NLP Parser")
    print("  ✅ Recurring Reminders")
    print("  ✅ Gamification")
    print("  ✅ Focus Mode (Pomodoro)")
    print("\n🎯 Ready to transform productivity!")
    print("=" * 50 + "\n")
    
    # Run with auto-restart
    while True:
        try:
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                pool_timeout=30
            )
        except Exception as e:
            print(f"❌ Error: {e}")
            print("🔄 Restarting in 5s...")
            asyncio.run(asyncio.sleep(5))
            continue

if __name__ == '__main__':
    main()
"""MemoryPing v4.0 - The Intelligent Companion Update
Created by Achu Vijayakumar

A smart, emotional, and gamified productivity companion that learns from you.

Architecture:
- Python Telegram Bot v20+ with job queue
- Flask keep-alive server for 24/7 uptime
- JSON-based persistent storage with async safety
- Timezone-aware reminder scheduling
- Personality-driven response system
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
from threading import Thread, Lock
from flask import Flask
import pytz
from typing import Dict, List, Optional, Tuple

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

# File paths
REMINDERS_FILE = "reminders.json"
USER_DATA_FILE = "user_data.json"
STATS_FILE = "stats.json"
HABITS_FILE = "habits.json"
MOODS_FILE = "moods.json"

# Timezone
DEFAULT_TIMEZONE = pytz.timezone('Asia/Kolkata')

# XP & Gamification
XP_PER_COMPLETION = 10
XP_PER_STREAK_DAY = 2
XP_PENALTY_MISSED = -2
XP_PER_LEVEL = 100

# Message limits
MAX_MESSAGE_LENGTH = 4000  # Safe margin below Telegram's 4096 limit

# File operation locks (prevent race conditions)
file_locks = {
    'reminders': Lock(),
    'user_data': Lock(),
    'stats': Lock(),
    'habits': Lock(),
    'moods': Lock()
}

# ============================================================================
# PERSONALITY SYSTEM
# ============================================================================

PERSONALITIES = {
    'zen': {
        'name': 'Zen Monk 🧘',
        'confirmation': [
            "Peace. I shall remind you at the destined moment.",
            "Mindfully noted. All is as it should be.",
            "In stillness, I hold your intention.",
            "The universe will whisper your reminder."
        ],
        'completion': [
            "Harmony achieved. You are present.",
            "Balance restored. Well done.",
            "The task dissolves. You remain.",
            "Mindfulness embodied."
        ],
        'ping': [
            "🧘 A gentle reminder arrives...",
            "🕉️ The moment is now...",
            "🌸 Awareness calls...",
            "☮️ Return to this intention..."
        ]
    },
    'coach': {
        'name': 'Coach 🏋️',
        'confirmation': [
            "LET'S GO! I'll push you when it's time! 💪",
            "COMMITMENT LOCKED IN! You got this!",
            "That's what I'm talking about! Setting you up for success!",
            "BOOM! Another goal in the system! Keep crushing it!"
        ],
        'completion': [
            "BEAST MODE ACTIVATED! 🔥",
            "YOU'RE UNSTOPPABLE! Keep that momentum!",
            "CHAMPION MENTALITY! That's how winners do it!",
            "CRUSHING IT! Your future self thanks you!"
        ],
        'ping': [
            "⏰ TIME TO EXECUTE! Let's get after it!",
            "🔔 GAME TIME! Show up and show out!",
            "💪 IT'S GO TIME! Make it happen!",
            "🏆 REMINDER ALERT! Champions don't wait!"
        ]
    },
    'bestie': {
        'name': 'Bestie 💖',
        'confirmation': [
            "Gotchu boo! I'll totally remind you! 💕",
            "Yasss! Consider it done bestie! ✨",
            "Ofc!! I got your back always! 🥰",
            "Bet! I won't let you forget! 💗"
        ],
        'completion': [
            "OMG YOU DID IT! So proud of you! 🎉",
            "Slay queen/king! You're crushing it! 👑",
            "Bestie energy! That's my friend right there! 💖",
            "YOU'RE AMAZING! Literally the best! ✨"
        ],
        'ping': [
            "💕 Heyyyy! Time for this babe!",
            "✨ Reminder time bestie!",
            "🥰 Don't forget this hun!",
            "💗 Your bestie checking in!"
        ]
    },
    'techbro': {
        'name': 'Tech Bro 🤓',
        'confirmation': [
            "Synced to cloud. Reminder scheduled in prod. 🚀",
            "Database updated. Your task is now in the pipeline.",
            "Confirmed. Deploying reminder to your neural network.",
            "Roger that. Added to queue with O(1) complexity."
        ],
        'completion': [
            "Task executed successfully. Zero errors. 💻",
            "Shipped! Another feature merged to main.",
            "Unit test passed. You're scaling well.",
            "Performance metrics looking good. GG! 📊"
        ],
        'ping': [
            "⚡ API call received. Execute callback now.",
            "🔔 Event triggered. Handle this async.",
            "💻 Push notification deployed.",
            "⏰ Cron job fired. Process this task."
        ]
    }
}

# ============================================================================
# CONTENT RESOURCES
# ============================================================================

MOTIVATIONAL_QUOTES = [
    "The secret of getting ahead is getting started.",
    "Don't watch the clock; do what it does. Keep going.",
    "Small daily improvements lead to stunning results.",
    "You are never too old to set another goal.",
    "Success is the sum of small efforts repeated daily.",
    "The future depends on what you do today.",
    "Dream big, start small, act now.",
    "Progress, not perfection.",
    "Your only limit is you.",
    "Make today so awesome that yesterday gets jealous."
]

TIPS = [
    "💡 Pro tip: Use voice messages for quick reminders!",
    "💡 Tag reminders with #work #health for organization",
    "💡 Set recurring reminders with 'every day'",
    "💡 Try /digest for your daily summary",
    "💡 Level up by completing more reminders!",
    "🎯 Your Memory Score improves with consistency",
    "⚡ Morning digest keeps you on track",
    "🏆 Check /leaderboard to see top performers",
    "🧘 Try different personalities with /personality",
    "💪 Build habits with recurring reminders"
]

CATEGORIES = {
    'work': '💼', 'personal': '👤', 'health': '💊',
    'shopping': '🛒', 'fitness': '💪', 'family': '👨‍👩‍👧',
    'finance': '💰', 'education': '📚', 'other': '📌'
}

PRIORITIES = {
    'high': '🔴', 'medium': '🟡', 'low': '🟢'
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
    'first_reminder': {'name': '🎬 First Step', 'desc': 'Created first reminder', 'xp': 50},
    'streak_3': {'name': '🔥 On Fire', 'desc': '3-day streak', 'xp': 30},
    'streak_7': {'name': '⚡ Unstoppable', 'desc': '7-day streak', 'xp': 75},
    'streak_30': {'name': '🏆 Legend', 'desc': '30-day streak', 'xp': 300},
    'complete_10': {'name': '✨ Achiever', 'desc': 'Completed 10 reminders', 'xp': 100},
    'complete_50': {'name': '💎 Diamond', 'desc': 'Completed 50 reminders', 'xp': 500},
    'complete_100': {'name': '👑 Master', 'desc': 'Completed 100 reminders', 'xp': 1000},
    'early_bird': {'name': '🌅 Early Bird', 'desc': 'Set reminder before 7am', 'xp': 25},
    'night_owl': {'name': '🦉 Night Owl', 'desc': 'Set reminder after 10pm', 'xp': 25},
    'organized': {'name': '🗂️ Organizer', 'desc': 'Used all categories', 'xp': 150},
    'level_5': {'name': '⭐ Rising Star', 'desc': 'Reached Level 5', 'xp': 0},
    'level_10': {'name': '🌟 Superstar', 'desc': 'Reached Level 10', 'xp': 0},
    'perfect_week': {'name': '📅 Perfect Week', 'desc': '7 days 100% completion', 'xp': 200},
}

# ============================================================================
# FLASK KEEP-ALIVE SERVER
# ============================================================================

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "MemoryPing v4.0 - The Intelligent Companion 🧠✨ | Created by Achu Vijayakumar"

@flask_app.route('/health')
def health():
    return {"status": "alive", "version": "4.0", "bot": "MemoryPing"}

def run_flask():
    """Run Flask server in background thread"""
    flask_app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

def keep_alive():
    """Start Flask keep-alive server"""
    thread = Thread(target=run_flask, daemon=True)
    thread.start()

# ============================================================================
# DATA MANAGEMENT CLASS
# ============================================================================

class DataManager:
    """Thread-safe JSON data manager with debounced writes"""
    
    def __init__(self):
        self.reminders = self._load_file(REMINDERS_FILE, 'reminders')
        self.user_data = self._load_file(USER_DATA_FILE, 'user_data')
        self.stats = self._load_file(STATS_FILE, 'stats')
        self.habits = self._load_file(HABITS_FILE, 'habits')
        self.moods = self._load_file(MOODS_FILE, 'moods')
        self.message_count = 0
    
    def _load_file(self, filepath: str, lock_key: str) -> dict:
        """Safely load JSON file with lock"""
        if os.path.exists(filepath):
            try:
                with file_locks[lock_key]:
                    with open(filepath, 'r') as f:
                        return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading {filepath}: {e}")
                return {}
        return {}
    
    def _save_file(self, data: dict, filepath: str, lock_key: str):
        """Safely save JSON file with lock"""
        try:
            with file_locks[lock_key]:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving {filepath}: {e}")
    
    def save_reminders(self):
        self._save_file(self.reminders, REMINDERS_FILE, 'reminders')
    
    def save_user_data(self):
        self._save_file(self.user_data, USER_DATA_FILE, 'user_data')
    
    def save_stats(self):
        self._save_file(self.stats, STATS_FILE, 'stats')
    
    def save_habits(self):
        self._save_file(self.habits, HABITS_FILE, 'habits')
    
    def save_moods(self):
        self._save_file(self.moods, MOODS_FILE, 'moods')
        # Initialize global instances
data_manager = DataManager()
bot_engine = MemoryPingEngine(data_manager)

# ============================================================================
# CORE BOT ENGINE
# ============================================================================

class MemoryPingEngine:
    """Core bot logic with personality, XP, habits, and mood tracking"""
    
    def __init__(self, data_manager: DataManager):
        self.data = data_manager
    
    # ========================================================================
    # PERSONALITY SYSTEM
    # ========================================================================
    
    def get_user_personality(self, chat_id: int) -> str:
        """Get user selected personality"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.user_data:
            self.data.user_data[chat_id_str] = {'personality': 'bestie', 'timezone': 'Asia/Kolkata'}
        return self.data.user_data[chat_id_str].get('personality', 'bestie')
    
    def get_response_tone(self, chat_id: int, response_type: str = "confirmation") -> str:
        """Get personality-based response"""
        personality = self.get_user_personality(chat_id)
        messages = PERSONALITIES.get(personality, PERSONALITIES['bestie'])[response_type]
        return random.choice(messages)
    
    # ========================================================================
    # XP & LEVELING SYSTEM
    # ========================================================================
    
    def get_user_xp(self, chat_id: int) -> int:
        """Get user current XP"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.stats:
            self.data.stats[chat_id_str] = {'xp': 0, 'level': 1}
        return self.data.stats[chat_id_str].get('xp', 0)
    
    def get_user_level(self, chat_id: int) -> int:
        """Calculate level from XP"""
        xp = self.get_user_xp(chat_id)
        return max(1, xp // XP_PER_LEVEL + 1)
    
    def update_xp(self, chat_id: int, amount: int, reason: str = "") -> Tuple[Optional[str], int]:
        """Update XP and check for level up"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.stats:
            self.data.stats[chat_id_str] = {'xp': 0, 'level': 1}
        
        old_level = self.get_user_level(chat_id)
        self.data.stats[chat_id_str]['xp'] = max(0, self.data.stats[chat_id_str].get('xp', 0) + amount)
        new_level = self.get_user_level(chat_id)
        
        self.data.save_stats()
        
        # Check for level achievements
        if new_level > old_level:
            if new_level == 5:
                return 'level_5', new_level
            elif new_level == 10:
                return 'level_10', new_level
            return 'level_up', new_level
        
        return None, new_level
    
    def calculate_memory_score(self, chat_id: int) -> int:
        """Calculate Memory Score (max 1000)"""
        chat_id_str = str(chat_id)
        stats = self.data.stats.get(chat_id_str, {})
        
        xp = stats.get('xp', 0)
        created = stats.get('created', 0)
        completed = stats.get('completed', 0)
        streak = self.get_streak(chat_id)
        
        completion_rate = (completed / created * 100) if created > 0 else 0
        memory_score = (xp / 10) + (completion_rate * 2) + (streak * 5)
        
        return min(1000, int(memory_score))
    
    # ========================================================================
    # REMINDER OPERATIONS
    # ========================================================================
    
    def add_reminder(self, chat_id: int, message: str, remind_time: datetime, **kwargs) -> str:
        """Add new reminder and track pattern"""
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
        self._track_habit_pattern(chat_id, message, remind_time)
        
        return reminder_id
    
    def get_user_reminders(self, chat_id: int, category: str = None, priority: str = None) -> dict:
        """Get filtered user reminders"""
        reminders = {
            rid: reminder for rid, reminder in self.data.reminders.items()
            if (reminder['chat_id'] == chat_id or chat_id in reminder.get('shared_with', []))
            and not reminder.get('completed', False)
        }
        
        if category:
            reminders = {rid: r for rid, r in reminders.items() if r.get('category') == category}
        if priority:
            reminders = {rid: r for rid, r in reminders.items() if r.get('priority') == priority}
        
        return reminders
    
    def complete_reminder(self, reminder_id: str) -> Tuple[bool, Optional[dict], int]:
        """Complete reminder and award XP"""
        if reminder_id in self.data.reminders:
            self.data.reminders[reminder_id]['completed'] = True
            self.data.save_reminders()
            
            chat_id = self.data.reminders[reminder_id]['chat_id']
            self.update_stats(chat_id, 'completed')
            
            achievement_key, level = self.update_xp(chat_id, XP_PER_COMPLETION, "completed reminder")
            achievement = self.check_achievements(chat_id)
            
            return True, achievement, level
        return False, None, 0
    
    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete reminder"""
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
    
    # ========================================================================
    # STATS & ACHIEVEMENTS
    # ========================================================================
    
    def update_stats(self, chat_id: int, action: str):
        """Update user statistics"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.stats:
            self.data.stats[chat_id_str] = {'created': 0, 'completed': 0, 'snoozed': 0, 'xp': 0}
        
        self.data.stats[chat_id_str][action] = self.data.stats[chat_id_str].get(action, 0) + 1
        self.data.save_stats()
    
    def get_streak(self, chat_id: int) -> int:
        """Get current streak"""
        chat_id_str = str(chat_id)
        if chat_id_str in self.data.user_data:
            return self.data.user_data[chat_id_str].get('streak', 0)
        return 0
    
    def check_achievements(self, chat_id: int) -> Optional[dict]:
        """Check and award achievements"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.stats:
            return None
        
        stats = self.data.stats[chat_id_str]
        if chat_id_str not in self.data.user_data:
            self.data.user_data[chat_id_str] = {'achievements': []}
        
        user_achievements = self.data.user_data[chat_id_str].get('achievements', [])
        completed = stats.get('completed', 0)
        
        # Check milestone achievements
        achievement_checks = [
            (1, 'first_reminder'),
            (10, 'complete_10'),
            (50, 'complete_50'),
            (100, 'complete_100')
        ]
        
        for milestone, ach_key in achievement_checks:
            if completed == milestone and ach_key not in user_achievements:
                user_achievements.append(ach_key)
                self.data.user_data[chat_id_str]['achievements'] = user_achievements
                self.data.save_user_data()
                
                xp_reward = ACHIEVEMENTS[ach_key]['xp']
                if xp_reward > 0:
                    self.update_xp(chat_id, xp_reward, f"achievement: {ach_key}")
                
                return ACHIEVEMENTS[ach_key]
        
        return None
    
    def check_time_achievements(self, chat_id: int, remind_time: datetime) -> Optional[dict]:
        """Check early bird/night owl achievements"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.user_data:
            self.data.user_data[chat_id_str] = {'achievements': []}
        
        user_achievements = self.data.user_data[chat_id_str].get('achievements', [])
        hour = remind_time.hour
        
        achievement_key = None
        if hour < 7 and 'early_bird' not in user_achievements:
            achievement_key = 'early_bird'
        elif hour >= 22 and 'night_owl' not in user_achievements:
            achievement_key = 'night_owl'
        
        if achievement_key:
            user_achievements.append(achievement_key)
            self.data.user_data[chat_id_str]['achievements'] = user_achievements
            self.data.save_user_data()
            self.update_xp(chat_id, ACHIEVEMENTS[achievement_key]['xp'], achievement_key)
            return ACHIEVEMENTS[achievement_key]
        
        return None
    
    def check_category_achievement(self, chat_id: int) -> Optional[dict]:
        """Check if user used all categories"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.user_data:
            return None
        
        user_achievements = self.data.user_data[chat_id_str].get('achievements', [])
        if 'organized' in user_achievements:
            return None
        
        reminders = self.get_user_reminders(chat_id)
        categories_used = {r.get('category', 'other') for r in reminders.values()}
        
        if len(categories_used) >= len(CATEGORIES):
            user_achievements.append('organized')
            self.data.user_data[chat_id_str]['achievements'] = user_achievements
            self.data.save_user_data()
            self.update_xp(chat_id, ACHIEVEMENTS['organized']['xp'], "organized")
            return ACHIEVEMENTS['organized']
        
        return None
    
    # ========================================================================
    # HABIT DETECTION
    # ========================================================================
    
    def _track_habit_pattern(self, chat_id: int, message: str, remind_time: datetime):
        """Track patterns for habit detection"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.habits:
            self.data.habits[chat_id_str] = []
        
        self.data.habits[chat_id_str].append({
            'message': message.lower(),
            'hour': remind_time.hour,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep last 50 patterns
        self.data.habits[chat_id_str] = self.data.habits[chat_id_str][-50:]
        self.data.save_habits()
    
    def analyze_habits(self, chat_id: int) -> Optional[List[dict]]:
        """Analyze and suggest habits"""
        chat_id_str = str(chat_id)
        patterns = self.data.habits.get(chat_id_str, [])
        
        if len(patterns) < 5:
            return None
        
        task_times = defaultdict(list)
        for pattern in patterns:
            task_times[pattern['message']].append(pattern['hour'])
        
        suggestions = []
        for task, hours in task_times.items():
            if len(hours) >= 3:
                avg_hour = int(sum(hours) / len(hours))
                suggestions.append({
                    'type': 'recurring',
                    'task': task,
                    'time': f"{avg_hour:02d}:00",
                    'frequency': len(hours)
                })
        
        return suggestions if suggestions else None
    
    # ========================================================================
    # MOOD TRACKING
    # ========================================================================
    
    def save_mood(self, chat_id: int, mood: str, note: str = ""):
        """Save daily mood"""
        chat_id_str = str(chat_id)
        today = datetime.now().strftime("%Y-%m-%d")
        
        if chat_id_str not in self.data.moods:
            self.data.moods[chat_id_str] = {}
        
        self.data.moods[chat_id_str][today] = {
            'mood': mood,
            'note': note,
            'timestamp': datetime.now().isoformat()
        }
        
        self.data.save_moods()
    
    def get_recent_moods(self, chat_id: int, days: int = 7) -> List[dict]:
        """Get last N days of moods"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.moods:
            return []
        
        moods = self.data.moods[chat_id_str]
        recent = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in moods:
                recent.append({'date': date, **moods[date]})
        
        return recent
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    
    def get_user_timezone(self, chat_id: int) -> pytz.timezone:
        """Get user timezone"""
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data.user_data:
            self.data.user_data[chat_id_str] = {'timezone': 'Asia/Kolkata'}
        tz_name = self.data.user_data[chat_id_str].get('timezone', 'Asia/Kolkata')
        return pytz.timezone(tz_name)
    
    def get_current_time(self, chat_id: int) -> datetime:
        """Get current time in user timezone"""
        tz = self.get_user_timezone(chat_id)
        return datetime.now(tz)
    
    def get_footer(self, show_credit: bool = False) -> str:
        """Smart footer with rotating content"""
        self.data.message_count += 1
        
        if show_credit or self.data.message_count % 10 == 0:
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
    def split_long_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
        """Split message if too long"""
        if len(text) <= max_length:
            return [text]
        
        parts = []
        while text:
            if len(text) <= max_length:
                parts.append(text)
                break
            
            split_at = text.rfind('\n', 0, max_length)
            if split_at == -1:
                split_at = max_length
            
            parts.append(text[:split_at])
            text = text[split_at:].lstrip()
        
        return parts

# Initialize global instances
data