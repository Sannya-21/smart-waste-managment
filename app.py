from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import random

app = Flask(__name__)
app.secret_key = "zero2hero_secret_key_2024"

# -------- LOGIN MANAGER --------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# -------- DATABASE HELPER --------
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# -------- USER CLASS --------
class User(UserMixin):
    def __init__(self, id, username, points=0):
        self.id = id
        self.username = username
        self.points = points

@login_manager.user_loader
def load_user(user_id):
    print(f"DEBUG: Loading user with ID {user_id}")
    conn = get_db_connection()
    u = conn.execute("SELECT id, username, points FROM users WHERE id = ?", (int(user_id),)).fetchone()
    conn.close()
    if u:
        return User(str(u['id']), u['username'], u['points'])
    return None

# -------- DATABASE INITIALIZATION --------
def init_db():
    print("DEBUG: Initializing database...")
    conn = get_db_connection()
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            points INTEGER DEFAULT 0
        )
    ''')

    # Bins table
    c.execute('''
        CREATE TABLE IF NOT EXISTS bins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            fill INTEGER DEFAULT 0
        )
    ''')

    # Reports table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            waste_type TEXT NOT NULL,
            quantity TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Collections table
    c.execute('''
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bin_id INTEGER,
            image_path TEXT,
            status TEXT DEFAULT 'Completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Seed data if empty
    user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        c.execute("INSERT INTO users (username, password, points) VALUES (?, ?, ?)",
                  ("admin", generate_password_hash("admin123"), 100))
        c.execute("INSERT INTO users (username, password, points) VALUES (?, ?, ?)",
                  ("eco_warrior", generate_password_hash("green123"), 250))

    bin_count = c.execute("SELECT COUNT(*) FROM bins").fetchone()[0]
    if bin_count == 0:
        bins_data = [
            ("Central Park North", 40.7967, -73.9548, 45),
            ("Times Square Hub", 40.7580, -73.9855, 85),
            ("Brooklyn Bridge Entry", 40.7061, -73.9969, 20),
            ("Wall Street Bin 1", 40.7060, -74.0088, 92),
            ("Greenwich Village Bin", 40.7335, -74.0030, 15)
        ]
        c.executemany("INSERT INTO bins (name, lat, lng, fill) VALUES (?, ?, ?, ?)", bins_data)

    conn.commit()
    conn.close()

# -------- AUTH ROUTES --------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user_row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user_row and check_password_hash(user_row['password'], password):
            user = User(user_row['id'], user_row['username'], user_row['points'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", "error")
            
    return render_template("login.html")

@app.route('/forgot-password')
def forgot_password():
    return render_template("forgot_password.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("Please fill all fields", "error")
            return render_template("signup.html")
            
        hashed_pw = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
            flash("Account created! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists", "error")
        finally:
            conn.close()
            
    return render_template("signup.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# -------- APP ROUTES --------

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    bins = [dict(b) for b in conn.execute("SELECT * FROM bins").fetchall()]
    
    # Calculate stats
    total_waste = sum([b['fill'] for b in bins]) * 10  # Arbitrary kg calculation
    avg_fill = int(sum([b['fill'] for b in bins]) / len(bins)) if bins else 0
    active_bins = len(bins)
    
    conn.close()
    return render_template(
        "dashboard.html",
        bins=bins,
        total_waste=total_waste,
        avg_fill=avg_fill,
        active_bins=active_bins
    )

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == "POST":
        location = request.form.get('location')
        waste_type = request.form.get('type')
        quantity = request.form.get('quantity')
        
        conn = get_db_connection()
        conn.execute("INSERT INTO reports (user_id, location, waste_type, quantity) VALUES (?, ?, ?, ?)",
                     (current_user.id, location, waste_type, quantity))
        conn.execute("UPDATE users SET points = points + 10 WHERE id = ?", (current_user.id,))
        conn.commit()
        conn.close()
        
        flash("Report submitted! You earned +10 points.", "success")
        return redirect(url_for('dashboard'))
        
    return render_template("report.html")

@app.route('/collect', methods=['GET', 'POST'])
@login_required
def collect():
    conn = get_db_connection()
    full_bins = conn.execute("SELECT * FROM bins WHERE fill > 80").fetchall()
    conn.close()
    
    if request.method == "POST":
        bin_id = request.form.get('bin_id')
        
        conn = get_db_connection()
        conn.execute("UPDATE bins SET fill = 0 WHERE id = ?", (bin_id,))
        conn.execute("UPDATE users SET points = points + 50 WHERE id = ?", (current_user.id,))
        conn.execute("INSERT INTO collections (user_id, bin_id) VALUES (?, ?)", (current_user.id, bin_id))
        conn.commit()
        conn.close()
        
        flash("Bin collected! You earned +50 points.", "success")
        return redirect(url_for('dashboard'))
        
    return render_template("collect.html", bins=full_bins)

@app.route('/leaderboard')
def leaderboard():
    conn = get_db_connection()
    users = conn.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10").fetchall()
    conn.close()
    return render_template("leaderboard.html", users=users)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == "POST":
        action = request.form.get('action')
        
        if action == "update_profile":
            new_username = request.form.get('username')
            if not new_username:
                flash("Username cannot be empty", "error")
            else:
                conn = get_db_connection()
                try:
                    conn.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, current_user.id))
                    conn.commit()
                    current_user.username = new_username
                    flash("Profile updated successfully!", "success")
                except sqlite3.IntegrityError:
                    flash("Username already taken", "error")
                conn.close()
        
        elif action == "change_password":
            old_pass = request.form.get('old_password')
            new_pass = request.form.get('new_password')
            
            conn = get_db_connection()
            user_row = conn.execute("SELECT password FROM users WHERE id = ?", (current_user.id,)).fetchone()
            
            if check_password_hash(user_row['password'], old_pass):
                hashed_new = generate_password_hash(new_pass)
                conn.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_new, current_user.id))
                conn.commit()
                flash("Password changed successfully!", "success")
            else:
                flash("Incorrect current password", "error")
            conn.close()
            
        return redirect(url_for('settings'))

    return render_template("settings.html")

# -------- API ROUTES --------

@app.route('/api/bins')
def api_bins():
    conn = get_db_connection()
    bins = conn.execute("SELECT * FROM bins").fetchall()
    conn.close()
    return jsonify([dict(b) for b in bins])

@app.route('/api/alerts')
def api_alerts():
    conn = get_db_connection()
    alerts = conn.execute("SELECT * FROM bins WHERE fill > 80").fetchall()
    conn.close()
    return jsonify([dict(a) for a in alerts])

# -------- AI CHATBOT ENGINE --------

KNOWLEDGE_BASE = {
    "greetings": {
        "keywords": ["hello", "hi", "hey", "greetings", "morning", "evening"],
        "reply": "Hello! I'm your EcoGuide AI. I can help you with recycling tips, tracking your points, or finding the nearest bins. What's on your mind?"
    },
    "recycling_plastic": {
        "keywords": ["plastic", "bottle", "container", "jug", "pvc"],
        "reply": "Most rigid plastics (Types 1, 2, and 5) like water bottles and milk jugs are highly recyclable! Remember to rinse them first and check for the recycling symbol."
    },
    "recycling_paper": {
        "keywords": ["paper", "cardboard", "box", "newspaper", "magazine"],
        "reply": "Clean paper and flattened cardboard boxes are great for recycling. Avoid recycling paper that is soiled with food (like pizza boxes) or has a waxy coating."
    },
    "recycling_glass": {
        "keywords": ["glass", "jar", "wine", "beer", "cup"],
        "reply": "Glass is 100% recyclable! Just make sure to rinse out any food residue. Most colors (clear, green, brown) are accepted at our hubs."
    },
    "ewaste": {
        "keywords": ["electronic", "phone", "battery", "laptop", "computer", "wire", "cable"],
        "reply": "E-waste contains hazardous materials and should NEVER go in the regular trash. You can drop off electronics at our 'Central Hub' for safe disposal and extra points!"
    },
    "points": {
        "keywords": ["points", "earn", "reward", "score", "pts", "rank"],
        "reply": "You earn 10 points for every waste report and 50 points for every full bin you collect! Check the Leaderboard to see how you rank against other Eco-Heroes."
    },
    "reporting": {
        "keywords": ["report", "trash", "found", "dirty", "spot", "cleanup"],
        "reply": "Notice a messy spot? Go to the 'Report Waste' page, fill in the location, and our collection team will be notified. Plus, you'll earn points!"
    },
    "collecting": {
        "keywords": ["collect", "pickup", "truck", "empty", "bin"],
        "reply": "Want to be more active? Go to 'Collect Waste' to see a list of bins that are currently over 80% full and ready for pickup."
    },
    "map": {
        "keywords": ["map", "location", "find", "where", "near", "tracker"],
        "reply": "The Interactive Map on your Dashboard shows all active bins. Red markers indicate bins that need urgent collection."
    },
    "leaderboard": {
        "keywords": ["leaderboard", "rank", "winner", "top", "competition"],
        "reply": "The Leaderboard showcases our top community contributors. Can you make it to the Top 3 this month?"
    },
    "settings": {
        "keywords": ["settings", "profile", "password", "username", "account"],
        "reply": "You can update your profile, change your password, or toggle Dark Mode in the Settings section of the sidebar."
    },
    "who_are_you": {
        "keywords": ["who", "what", "identity", "creator", "purpose"],
        "reply": "I am the Zero2Hero AI Assistant, designed to help our community manage waste more efficiently and save the planet together!"
    }
}

@app.route('/chat')
def chat():
    msg = request.args.get('msg', '').lower()
    if not msg:
        return jsonify({"reply": "I'm listening! Ask me anything about waste management or how to use the app."})
        
    best_match = None
    max_score = 0
    
    # Simple scoring algorithm: count matching keywords
    for intent, data in KNOWLEDGE_BASE.items():
        score = sum(1 for keyword in data['keywords'] if keyword in msg)
        if score > max_score:
            max_score = score
            best_match = data['reply']
            
    if max_score > 0:
        reply = best_match
    else:
        reply = "I'm not exactly sure about that, but I can help you with recycling, earning points, or using the map! Try asking 'How do I earn points?' or 'Can I recycle plastic?'"
            
    return jsonify({"reply": reply})

# -------- RUN --------
if __name__ == '__main__':
    print("DEBUG: Application starting...")
    if not os.path.exists('database.db'):
        init_db()
    else:
        # Check if users table exists, if not init
        conn = get_db_connection()
        table_check = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        conn.close()
        if not table_check:
            init_db()
            
    print("DEBUG: Server running on http://127.0.0.1:5050")
    # Production settings for background stability
    app.run(debug=False, host='127.0.0.1', port=5050)