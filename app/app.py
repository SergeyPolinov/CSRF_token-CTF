from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

DATABASE_DIR = '/app/data'
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE = os.path.join(DATABASE_DIR, 'database.db')
FLAG = os.environ.get('FLAG', 'practice{default_flag}')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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
        db.execute('DELETE FROM inboxes')
        admin = db.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not admin:
            hashed_pw = generate_password_hash('adminpassword')
            db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                       ('admin', hashed_pw, 1))
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
        with get_db() as db:
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                return redirect(url_for('dashboard'))
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
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
        messages = db.execute('SELECT message FROM inboxes WHERE user_id = ?', (session['user_id'],)).fetchall()
    return render_template('inbox.html', messages=messages)

@app.route('/send_flag', methods=['POST'])
def send_flag():
    if 'user_id' not in session or not session['is_admin']:
        return 'Unauthorized', 403
    recipient = request.form.get('recipient')
    if not recipient:
        return 'Missing recipient', 400
    with get_db() as db:
        recip = db.execute('SELECT id FROM users WHERE username = ?', (recipient,)).fetchone()
        if not recip:
            return 'Recipient not found', 404
        db.execute('INSERT INTO inboxes (user_id, message) VALUES (?, ?)', (recip['id'], FLAG))
    return 'Flag sent'

@app.route('/submit_to_bot', methods=['GET', 'POST'])
def submit_to_bot():
    if request.method == 'POST':
        url = request.form['url']
        import requests
        try:
            requests.post('http://bot:5001/visit', json={'url': url})
            flash('URL submitted to bot')
        except:
            flash('Error submitting to bot')
        return redirect(url_for('submit_to_bot'))
    return render_template('submit_to_bot.html')

@app.route('/send_flag_form')
def send_flag_form():
    if 'user_id' not in session or not session['is_admin']:
        return 'Unauthorized', 403
    return render_template('send_flag_form.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)