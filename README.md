# 🧠 MemoryPing v4.0 - The Intelligent Companion

A smart, emotional, and gamified productivity bot for Telegram that learns from you, celebrates with you, and helps you build better habits.

![Version](https://img.shields.io/badge/version-4.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-purple)

## ✨ Features

### 🎭 **Personality Engine**
Choose from 4 unique bot personalities:
- 🧘 **Zen Monk** - Calm and mindful
- 🏋️ **Coach** - Motivational and energetic
- 💖 **Bestie** - Playful and supportive
- 🤓 **Tech Bro** - Nerdy and technical

### 📈 **XP & Leveling System**
- Earn XP for completing reminders
- Level up and unlock achievements
- Track your Memory Score (max 1000)
- Visual progress bars

### 🧠 **Smart Habit Detection**
- Analyzes your reminder patterns
- Suggests recurring reminders
- Learns your common times
- Intelligent habit recommendations

### 😊 **Mood Tracking**
- Daily mood journal
- Optional reflection notes
- 7-day mood history
- Emotional well-being insights

### 🏆 **Achievement System**
13 unlockable achievements including:
- 🎬 First Step
- 🔥 On Fire (3-day streak)
- ⚡ Unstoppable (7-day streak)
- 👑 Master (100 completions)

### 💬 **Enhanced Natural Language**
Understands phrases like:
- "Remind me after lunch"
- "Meeting in 2h 30m"
- "Every weekday at 9am"
- "Tomorrow evening"

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Render account (for 24/7 hosting) or local environment

### Local Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/MemoryPingBot.git
cd MemoryPingBot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set environment variable**
```bash
export BOT_TOKEN="your_telegram_bot_token_here"
```

4. **Run the bot**
```bash
python reminder_bot.py
```

### Deploy to Render

1. **Fork this repository** to your GitHub account

2. **Create a new Web Service** on [Render](https://render.com)

3. **Configure the service:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python reminder_bot.py`

4. **Add environment variable:**
   - Key: `BOT_TOKEN`
   - Value: Your Telegram bot token

5. **Deploy!** Render will automatically deploy your bot

## 📖 Commands

### Core Commands
- `/start` - Welcome & main menu
- `/help` - Complete guide
- `/personality` - Choose your bot's vibe

### Productivity
- `/quick` - Quick reminder templates
- `/list` - View all reminders
- `/today` - Today's schedule
- `/digest` - Daily summary

### Gamification
- `/stats` - XP, level & memory score
- `/achievements` - Badge collection
- `/leaderboard` - Top users by XP

### Wellness
- `/reflect` - Mood journal
- `/focus` - 25-min Pomodoro timer
- `/quote` - Motivational quote

### Advanced
- `/missed` - Overdue reminders
- `/search <keyword>` - Find reminders
- `/export` - Backup your data

## 🎯 Usage Examples
```
# Basic reminder
Remind me to call mom at 5pm

# With tags
Meeting in 2 hours #work !high

# Recurring
Take medicine every day at 9am #health

# With notes
Dentist at 2pm tomorrow -- Bring insurance

# Natural language
Workout after lunch
Study before bed
Team standup every weekday at 10am
```

## 🛠️ Architecture
```
MemoryPingBot/
├── reminder_bot.py          # Main bot logic
├── requirements.txt         # Python dependencies
├── runtime.txt             # Python version
├── .gitignore              # Git ignore rules
├── README.md               # This file
└── data/ (auto-created)
    ├── reminders.json      # Active reminders
    ├── user_data.json      # User preferences
    ├── stats.json          # XP & completion data
    ├── habits.json         # Pattern analysis
    └── moods.json          # Mood tracking
```

## 🔧 Configuration

### Environment Variables
- `BOT_TOKEN` - Your Telegram bot token (required)
- `PORT` - Flask server port (default: 8080)

### Customization
Edit constants in `reminder_bot.py`:
- `DEFAULT_TIMEZONE` - Default timezone
- `XP_PER_COMPLETION` - XP awarded per task
- `XP_PER_LEVEL` - XP needed per level
- Add new personalities in `PERSONALITIES`
- Add new achievements in `ACHIEVEMENTS`

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

MIT License - feel free to use and modify!

## 👨‍💻 Author

**Achu Vijayakumar**
- Created with ❤️ for productivity enthusiasts
Linkedin : https://www.linkedin.com/in/achuvijayakumar/
- Version 4.0 - The Intelligent Companion Update

## 🙏 Acknowledgments

- Python Telegram Bot library
- Flask for keep-alive functionality
- Render for hosting
- All users who provided feedback!

## 📊 Changelog

### v4.0 - The Intelligent Companion Update
- 🎭 Added Personality Engine (4 vibes)
- 📈 Implemented XP & Level system
- 🧠 Smart Habit Detection
- 😊 Mood Tracking & Reflection
- 🏆 Enhanced Achievement System (13 badges)
- 💬 Better Natural Language Processing
- 🎮 Gamification with Leaderboards
- 📊 Memory Score metric
- ⚡ Focus Mode (Pomodoro)
- 🎨 Visual progress bars

### v3.0
- Recurring reminders
- Snooze functionality
- Categories & priorities
- Quick templates

### v2.0
- Natural language parsing
- Timezone support
- Statistics tracking

### v1.0
- Basic reminder functionality
- Telegram bot integration

## 🐛 Known Issues

None currently! Report bugs via GitHub Issues.

## 🔮 Roadmap

- [ ] Voice message support
- [ ] Image attachments
- [ ] Google Calendar sync
- [ ] Web dashboard
- [ ] Mobile app
- [ ] AI-powered suggestions
- [ ] Team collaboration features

---

**Made with ❤️ by Achu Vijayakumar**

Star ⭐ this repo if you find it useful!
```

---

### **6. Procfile** (For Heroku deployment - alternative to Render)
```
web: python reminder_bot.py