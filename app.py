import os
from flask import Flask, request, redirect, render_template, session
import secrets

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Флаг загружается из переменной окружения
FLAG = os.getenv("FLAG", "practice{default_flag}")

# Фейковая база данных
users = {
    "admin": {"password": "admin123", "csrf_token": None, "flag_visible": False},
    "user": {"password": "user123", "csrf_token": None, "flag_visible": False},
}

def is_logged_in():
    print(f"[DEBUG] Проверяем, вошел ли пользователь: {session.get('username')}", flush=True)
    return session.get("username") in users

def generate_csrf_token():
    return secrets.token_hex(16)

@app.route("/")
def index():
    return redirect("/login")
    
@app.route("/welcome")
def welcome():
    if not is_logged_in():
        return redirect("/login")

    username = session["username"]
    flag = FLAG if username == "admin" and users[username]["flag_visible"] else None

    return f"Welcome, {session['username']}! <a href='/change'>Change Password</a><br>{flag if flag else ''}"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username]["password"] == password:
            session["username"] = username
            # Генерируем CSRF-токен при входе
            users[username]["csrf_token"] = generate_csrf_token()
            session["csrf_token"] = users[username]["csrf_token"]
            print(f"[DEBUG] Пользователь {username} вошел в систему, пароль {password}", flush=True)
            return redirect("/welcome")
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/change", methods=["GET", "POST"])
def change():
    if not is_logged_in():
        print("[DEBUG] Пользователь не вошел в систему", flush=True)
        return redirect("/login")

    if request.method == "POST":
        print(f"[DEBUG] Получен запрос на смену пароля: {request.form}", flush=True)
        
        # Проверяем CSRF-токен
        if "csrf_token" not in request.form or request.form["csrf_token"] != session.get("csrf_token"):
            return "Invalid CSRF token!", 403
        
        # Проверяем, есть ли поле "password" в запросе
        if "password" not in request.form:
            return "Missing password field!", 400

        # Проверяем, что запрос пришел с домена злоумышленника (CSRF-атака)
        if request.referrer and "evil:5005" in request.referrer:
            print("[DEBUG] Запрос на изменение пароля через CSRF-атаку", flush=True)
            new_password = request.form["password"]
            users[session["username"]]["password"] = new_password
            print(f"Новый пароль пользователя {session['username']}: {new_password}", flush=True)

            if session["username"] == "admin":
                print(f"Новый пароль админа: {users['admin']['password']}", flush=True)
                # Делаем флаг видимым только после CSRF-атаки
                users["admin"]["flag_visible"] = True
                session.clear()
                return f"Password changed! New password: {users['admin']['password']}"

            return "Password changed successfully!"
        else:
            return "Password change allowed only via CSRF attack!", 403

    return render_template("change.html", csrf_token=session.get("csrf_token"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
