from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import json

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)

# ------------------- Настройка Google OAuth -------------------
app.config['GOOGLE_CLIENT_ID'] = "80158679069-i13kcgdfpalkmr9gvjjpsk7vli24lkre.apps.googleusercontent.com"
app.config['GOOGLE_CLIENT_SECRET'] = "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"
app.config['GOOGLE_DISCOVERY_URL'] = "https://accounts.google.com/.well-known/openid-configuration"

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
    client_kwargs={'scope': 'openid email profile'}
)

# ------------------- Инициализация базы пользователей -------------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

# ------------------- Главная -------------------
@app.route("/")
def index():
    user = session.get("user")
    if user:
        return f"""
        <h2>Главная страница</h2>
        <p>Вы вошли как: <b>{user['name']}</b> ({user['email']})</p>
        <p><a href="/menu">📋 Меню</a></p>
        <p><a href="/bookings">📅 Посмотреть брони</a></p>
        <p><a href="/logout">🚪 Выйти</a></p>
        """
    return """
    <h2>Главная страница</h2>
    <p><a href="/login/google">🔐 Войти через Google</a></p>

    <h3>Или войти по email:</h3>
    <form action="/login/email" method="post">
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Пароль" required><br>
        <button type="submit">Войти</button>
    </form>

    <h3>Регистрация:</h3>
    <form action="/register" method="post">
        <input type="text" name="name" placeholder="Имя" required><br>
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Пароль" required><br>
        <button type="submit">Зарегистрироваться</button>
    </form>
    """

# ------------------- Регистрация -------------------
@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    hashed_pw = generate_password_hash(password)

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_pw))
        conn.commit()
    except sqlite3.IntegrityError:
        return "<h3 style='color:red;'>Пользователь с таким email уже существует!</h3><a href='/'>Назад</a>"
    conn.close()

    return f"<h3 style='color:green;'>Регистрация успешна, {name}!</h3><a href='/'>На главную</a>"

# ------------------- Вход по email -------------------
@app.route("/login/email", methods=["POST"])
def login_email():
    email = request.form.get("email")
    password = request.form.get("password")

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[3], password):
        session["user"] = {"id": user[0], "name": user[1], "email": user[2]}
        return redirect("/")
    else:
        return "<h3 style='color:red;'>Неверный email или пароль!</h3><a href='/'>Назад</a>"

# ------------------- Вход через Google -------------------
@app.route("/login/google")
def login_google():
    redirect_uri = url_for("authorize", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/authorize")
def authorize():
    token = google.authorize_access_token()
    user_info = google.get("https://openidconnect.googleapis.com/v1/userinfo").json()
    session["user"] = user_info
    return redirect("/")

# ------------------- Выход -------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# ------------------- Меню -------------------
@app.route("/menu", methods=["GET"])
def get_menu():
    with open("menu.json", "r", encoding="utf-8") as f:
        menu = json.load(f)
    return jsonify(menu)

# ------------------- Создание брони -------------------
@app.route("/book", methods=["POST"])
def create_booking():
    data = request.get_json()
    if os.path.exists("bookings.json"):
        with open("bookings.json", "r", encoding="utf-8") as f:
            bookings = json.load(f)
    else:
        bookings = []

    bookings.append(data)
    with open("bookings.json", "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=4)
    return jsonify({"message": "Бронь успешно добавлена"}), 201

# ------------------- Просмотр броней -------------------
@app.route("/bookings", methods=["GET"])
def view_bookings():
    if not os.path.exists("bookings.json"):
        return jsonify([])
    with open("bookings.json", "r", encoding="utf-8") as f:
        bookings = json.load(f)
    return jsonify(bookings)

# ------------------- Поиск брони -------------------
@app.route("/search_booking", methods=["GET"])
def search_booking():
    phone = request.args.get("phone")
    if not os.path.exists("bookings.json"):
        return jsonify({"message": "Файл с бронями не найден"}), 404
    with open("bookings.json", "r", encoding="utf-8") as f:
        bookings = json.load(f)
    results = [b for b in bookings if phone.replace("+", "") in b.get("phone", "").replace("+", "")]
    if not results:
        return jsonify({"message": "Бронь не найдена"}), 404
    return jsonify(results)

# ------------------- Очистка -------------------
@app.route("/clear_bookings", methods=["DELETE"])
def clear_bookings():
    with open("bookings.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)
    return jsonify({"message": "Все брони удалены"}), 200

# ------------------- Запуск -------------------
if __name__ == "__main__":
    init_db()

    if not os.path.exists("bookings.json"):
        with open("bookings.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)

    if not os.path.exists("menu.json"):
        with open("menu.json", "w", encoding="utf-8") as f:
            json.dump([
                {"id": 1, "name": "Пицца Маргарита", "price": 3500},
                {"id": 2, "name": "Паста Карбонара", "price": 4200}
            ], f, ensure_ascii=False, indent=4)

    print("Сервер запущен: http://127.0.0.1:5000")
    app.run(debug=True)
