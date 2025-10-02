from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey')
FLAG = os.environ.get('FLAG', 'practice{default_flag}')
BOT_URL = os.environ.get('BOT_URL', 'http://127.0.0.1:5001')

if SECRET_KEY == 'supersecretkey':
    print("WARNING: Using default SECRET_KEY. Set SECRET_KEY environment variable for production!")
if FLAG == 'practice{default_flag}':
    print("WARNING: Using default FLAG. Set FLAG environment variable for production!")

app.secret_key = SECRET_KEY

DATABASE_DIR = '/app/data'
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE = os.path.join(DATABASE_DIR, 'database.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')

    if admin_username == 'admin' and admin_password == 'adminpassword':
        print("WARNING: Using default admin credentials. Set ADMIN_USERNAME and ADMIN_PASSWORD environment variables for production!")
    
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin BOOLEAN NOT NULL DEFAULT 0
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS inboxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        cursor = db.execute('PRAGMA table_info(inboxes)')
        columns = [col['name'] for col in cursor.fetchall()]
        if 'timestamp' not in columns:
            db.execute('''
                ALTER TABLE inboxes ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            ''')
            print("App: Migrated inboxes table - added timestamp column")
        
        db.execute('DELETE FROM inboxes')

        admin = db.execute('SELECT * FROM users WHERE username = ?', (admin_username,)).fetchone()
        if not admin:
            hashed_pw = generate_password_hash(admin_password)
            db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                       (admin_username, hashed_pw, 1))
        user = db.execute('SELECT * FROM users WHERE username = ?', ('user',)).fetchone()
        if not user:
            hashed_pw = generate_password_hash('userpassword')
            db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                       ('user', hashed_pw, 0))
        attacker = db.execute('SELECT * FROM users WHERE username = ?', ('attacker',)).fetchone()
        if not attacker:
            hashed_pw = generate_password_hash('attackerpass')
            db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                       ('attacker', hashed_pw, 0))
        else:
            db.execute('DELETE FROM inboxes WHERE user_id = ?', (attacker['id'],))
            print(f"App: Cleared inbox for user 'attacker' (id: {attacker['id']}) on restart")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with get_db() as db:
            if db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone():
                flash('Username already exists')
                return redirect(url_for('register'))
            hashed_pw = generate_password_hash(password)
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_pw))
        flash('Registered successfully')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"App: Login attempt for user: {username}")
        with get_db() as db:
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                print(f"App: Successful login for {username}, admin: {user['is_admin']}")
                return redirect(url_for('dashboard'))
            print(f"App: Failed login for {username}")
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'unknown')
    session.clear()
    print(f"App: User {username} logged out")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with get_db() as db:
        messages = db.execute('SELECT message, timestamp FROM inboxes WHERE user_id = ? ORDER BY timestamp DESC', 
                             (session['user_id'],)).fetchall()
    print(f"App: {session['username']} checking inbox - {len(messages)} messages")
    return render_template('inbox.html', messages=messages)

@app.route('/send_flag', methods=['POST'])
def send_flag():
    print(f"App: send_flag called by {request.remote_addr}")
    print(f"App: Session info - user_id: {session.get('user_id')}, username: {session.get('username')}, is_admin: {session.get('is_admin')}")
    print(f"App: Request headers: {dict(request.headers)}")
    print(f"App: Form data: {request.form}")
    
    if 'user_id' not in session:
        print("App: CSRF attempt - no session")
        return 'Unauthorized - No session', 403
    
    if not session.get('is_admin'):
        print("App: Direct attempt non-admin user blocked")
        return 'Forbidden - non-admin user cannot send flags', 403
    
    recipient = request.form.get('recipient')
    if not recipient:
        print("App: Missing recipient")
        return 'Missing recipient', 400
    
    print(f"App: Admin {session['username']} sending flag to {recipient}")
    
    with get_db() as db:
        recip = db.execute('SELECT id FROM users WHERE username = ?', (recipient,)).fetchone()
        if not recip:
            print(f"App: Recipient {recipient} not found")
            return 'Recipient not found', 404
        
        db.execute('INSERT INTO inboxes (user_id, message) VALUES (?, ?)', (recip['id'], FLAG))
        print(f"App: Flag successfully sent to {recipient} (user_id: {recip['id']})")
    
    return 'Flag sent successfully'

@app.route('/submit_to_bot', methods=['GET', 'POST'])
def submit_to_bot():
    if request.method == 'POST':
        url = request.form['url']
        print(f"App: Submitting URL to bot: {url}")
        print(f"App: Bot URL configured as: {BOT_URL}")
        import requests
        try:
            response = requests.post(f'{BOT_URL}/visit', json={'url': url}, timeout=60)
            print(f"App: Bot response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                flash('URL submitted to bot successfully')
            else:
                flash(f'Bot returned error: {response.text}')
        except Exception as e:
            print(f"App: Error submitting to bot: {str(e)}")
            flash(f'Error submitting to bot: {str(e)}')
        return redirect(url_for('submit_to_bot'))
    return render_template('submit_to_bot.html')

@app.route('/send_flag_form')
def send_flag_form():
    if 'user_id' not in session:
        return render_template('send_flag_form.html'), 403
    return render_template('send_flag_form.html')

if __name__ == '__main__':
    print("App starting...")
    print(f"Flag: {FLAG}")
    print(f"Bot URL: {BOT_URL}")
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)