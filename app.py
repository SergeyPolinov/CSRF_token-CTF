import os
from flask import Flask, request, redirect, render_template, session

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Флаг загружается из переменной окружения
FLAG = os.getenv("FLAG", "practice{default_flag}")

# Фейковая база данных
users = {
    "admin": {"password": "admin123"}
}

def is_logged_in():
    print(f"[DEBUG] Проверяем, вошел ли пользователь: {session.get('username')}", flush=True)
    return session.get("username") in users

@app.route("/")
def index():
    return redirect("/login")
    
@app.route("/welcome")
def welcome():
    if not is_logged_in():
        return redirect("/login")
    
    #if session["username"] == "admin":

    return f"Welcome, {session['username']}! <a href='/change'>Change Password</a>"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username]["password"] == password:
            session["username"] = username
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
        # Проверяем, есть ли поле "password" в запросе
        if "password" not in request.form:
            return "Missing password field!", 400

        new_password = request.form["password"]
        users[session["username"]]["password"] = new_password
        print(f"Новый пароль пользователя {session['username']}: {new_password}", flush=True)

        if session["username"] == "admin":
            print(f"Новый пароль админа: {users['admin']['password']}", flush=True)
            session.clear()
            return f"Password changed! New password: {users['admin']['password']}"

        return "Password changed successfully!"

    return render_template("change.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
