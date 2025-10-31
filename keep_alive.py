"""
MemoryPing v4.0 - Keep Alive Server
Created by Achu Vijayakumar

Flask web server to keep the bot alive on Render free tier.
Provides health check endpoints for UptimeRobot monitoring.
"""

from flask import Flask, jsonify, render_template_string
from threading import Thread
import datetime
import os

app = Flask(__name__)

# Store bot start time for uptime tracking
start_time = datetime.datetime.now()

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def home():
    """Main page - Bot status"""
    uptime = datetime.datetime.now() - start_time
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MemoryPing v4.0 - Status</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
                width: 100%;
                text-align: center;
            }
            .logo {
                font-size: 64px;
                margin-bottom: 20px;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
            h1 {
                color: #667eea;
                font-size: 32px;
                margin-bottom: 10px;
            }
            .version {
                color: #764ba2;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 30px;
            }
            .status {
                background: #10b981;
                color: white;
                padding: 15px 30px;
                border-radius: 50px;
                font-size: 18px;
                font-weight: 600;
                display: inline-block;
                margin-bottom: 30px;
                animation: glow 2s infinite;
            }
            @keyframes glow {
                0%, 100% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.5); }
                50% { box-shadow: 0 0 30px rgba(16, 185, 129, 0.8); }
            }
            .stats {
                background: #f3f4f6;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .stat-item {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #e5e7eb;
            }
            .stat-item:last-child {
                border-bottom: none;
            }
            .stat-label {
                color: #6b7280;
                font-weight: 500;
            }
            .stat-value {
                color: #111827;
                font-weight: 600;
            }
            .features {
                text-align: left;
                margin-top: 20px;
            }
            .feature {
                padding: 8px 0;
                color: #4b5563;
            }
            .feature::before {
                content: "✨ ";
            }
            .footer {
                margin-top: 30px;
                color: #9ca3af;
                font-size: 14px;
            }
            .link {
                color: #667eea;
                text-decoration: none;
                font-weight: 600;
            }
            .link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🧠</div>
            <h1>MemoryPing</h1>
            <div class="version">v4.0 - The Intelligent Companion</div>
            
            <div class="status">
                ✅ Bot is Running
            </div>
            
            <div class="stats">
                <div class="stat-item">
                    <span class="stat-label">⏱️ Uptime</span>
                    <span class="stat-value">{{ uptime }}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">🚀 Status</span>
                    <span class="stat-value">Active</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">🌐 Server</span>
                    <span class="stat-value">Render Free Tier</span>
                </div>
            </div>
            
            <div class="features">
                <div class="feature">4 Personalities</div>
                <div class="feature">XP & Leveling</div>
                <div class="feature">Smart Habits</div>
                <div class="feature">Mood Tracking</div>
                <div class="feature">Daily Digest</div>
                <div class="feature">9 Achievements</div>
            </div>
            
            <div class="footer">
                Created with ❤️ by <span class="link">Achu Vijayakumar</span>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html, uptime=f"{hours}h {minutes}m")

@app.route('/health')
def health():
    """Health check endpoint for UptimeRobot"""
    uptime = datetime.datetime.now() - start_time
    
    return jsonify({
        'status': 'alive',
        'bot': 'MemoryPing v4.0',
        'version': '4.0',
        'uptime_seconds': int(uptime.total_seconds()),
        'uptime_formatted': str(uptime).split('.')[0],
        'timestamp': datetime.datetime.now().isoformat(),
        'features': {
            'personalities': 4,
            'achievements': 9,
            'gamification': True,
            'habit_detection': True,
            'mood_tracking': True
        }
    }), 200

@app.route('/status')
def status():
    """Detailed status endpoint"""
    uptime = datetime.datetime.now() - start_time
    
    return jsonify({
        'bot_name': 'MemoryPing',
        'version': '4.0',
        'status': 'running',
        'uptime': {
            'seconds': int(uptime.total_seconds()),
            'formatted': str(uptime).split('.')[0],
            'start_time': start_time.isoformat()
        },
        'system': {
            'personalities': ['zen', 'coach', 'bestie', 'techbro'],
            'xp_per_completion': 10,
            'xp_per_level': 100,
            'max_memory_score': 1000
        },
        'deployment': {
            'platform': 'Render',
            'tier': 'Free',
            'keep_alive': 'UptimeRobot',
            'port': int(os.getenv('PORT', 8080))
        }
    }), 200

@app.route('/ping')
def ping():
    """Simple ping endpoint"""
    return 'pong', 200

# ============================================================================
# KEEP ALIVE FUNCTION
# ============================================================================

def run():
    """Run Flask app on specified port"""
    port = int(os.getenv('PORT', 8080))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )

def keep_alive():
    """Start Flask server in background thread"""
    t = Thread(target=run, daemon=True)
    t.start()
    print(f"🌐 Keep-alive server started on port {os.getenv('PORT', 8080)}")
    print("📡 Configure UptimeRobot to ping: https://your-app.onrender.com/health")
    print("⏱️  Recommended interval: 5 minutes")

# ============================================================================
# MAIN - For standalone testing
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🧠 MemoryPing v4.0 - Keep Alive Server")
    print("=" * 60)
    print("✨ Created by Achu Vijayakumar")
    print("")
    print("🌐 Starting Flask server...")
    print(f"📡 Port: {os.getenv('PORT', 8080)}")
    print("")
    print("Available endpoints:")
    print("  • /          - Status page")
    print("  • /health    - Health check (for UptimeRobot)")
    print("  • /status    - Detailed status JSON")
    print("  • /ping      - Simple ping/pong")
    print("=" * 60)
    run()