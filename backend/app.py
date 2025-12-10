from flask import Flask, redirect, url_for, session, request, jsonify
from authlib.integrations.flask_client import OAuth
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os
import json
import psycopg2
import psycopg2.extras
import smtplib
import random
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

# ------------------- PostgreSQL -------------------
DB = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

def get_db():
    return psycopg2.connect(**DB)


app = Flask(__name__)

# ------------------- Конфиг окружения -------------------
FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN",
    "https://asian-cafefrontend.vercel.app"
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
IS_PROD = os.getenv("FLASK_ENV") == "production"

# Разрешённые Origins
ALLOWED_ORIGINS = [
    FRONTEND_ORIGIN,
    "http://localhost:3000"
]

# ------------------- Ручной CORS (главная правка) -------------------
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"

    return response


# ------------------- Сессии -------------------
app.secret_key = os.getenv("SESSION_SECRET")

if IS_PROD:
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True
else:
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=20)

# ------------------- Google OAuth -------------------
app.config['GOOGLE_CLIENT_ID'] = os.getenv("GOOGLE_CLIENT_ID")
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv("GOOGLE_CLIENT_SECRET")
app.config['GOOGLE_DISCOVERY_URL'] = "https://accounts.google.com/.well-known/openid-configuration"

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
    client_kwargs={'scope': 'openid email profile'}
)


# ------------------- Таблицы -------------------
def init_pg():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT,
            verified BOOLEAN DEFAULT FALSE,
            google_id TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_codes (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            category TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            branch TEXT NOT NULL,
            date DATE NOT NULL,
            tables TEXT[] NOT NULL,
            guests INTEGER NOT NULL,
            notes TEXT,
            menu_items TEXT[],
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    conn.close()


# ------------------- Отправка email -------------------
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_email_code(to_email, code):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Код подтверждения регистрации"
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email
        msg.set_content(f"Ваш код подтверждения: {code}")

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Email error:", e)
        return False


def generate_email_code(email):
    code = str(random.randint(100000, 999999))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO email_codes (email, code) VALUES (%s, %s)", (email, code))
    conn.commit()
    conn.close()
    return code


# ------------------- Главная (для проверки что бэк жив) -------------------
@app.route("/")
def index():
    return f"""
    <h2>Главная страница</h2>
    <p>Тут работает сервер API.</p>
    <p>Фронтенд находится здесь: <a href="{FRONTEND_ORIGIN}">{FRONTEND_ORIGIN}</a></p>
    """


# ------------------- Регистрация -------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Нет данных"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "Заполните все поля"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    if cur.fetchone():
        conn.close()
        return jsonify({"error": "Пользователь уже существует"}), 409

    hashed_pw = generate_password_hash(password)
    code = generate_email_code(email)

    cur.execute("""
        INSERT INTO users (name, email, password, verified)
        VALUES (%s, %s, %s, %s)
    """, (name, email, hashed_pw, False))

    conn.commit()
    conn.close()

    send_email_code(email, code)
    return jsonify({"message": "Пользователь создан. Подтвердите email."})


# ------------------- Подтверждение email -------------------
@app.route("/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json()
    email = data.get("email")
    code = data.get("code")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT code FROM email_codes WHERE email=%s ORDER BY id DESC LIMIT 1", (email,))
    row = cur.fetchone()

    if not row or row[0] != code:
        return jsonify({"error": "Неверный код"}), 400

    cur.execute("UPDATE users SET verified=True WHERE email=%s", (email,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Email подтвержден"})


# ------------------- Логин по email -------------------
@app.route("/login/email", methods=["POST"])
def login_email():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    if not user["verified"]:
        return jsonify({"error": "Email не подтвержден"}), 403

    if not check_password_hash(user["password"], password):
        return jsonify({"error": "Неверный пароль"}), 401

    session["user"] = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"]
    }

    return jsonify({"message": "Вход выполнен", "user": session["user"]})


# ------------------- Проверка сессии -------------------
@app.route("/auth/user")
def auth_user():
    user = session.get("user")
    if not user:
        return jsonify({"authenticated": False})
    return jsonify({"authenticated": True, "user": user})


# ------------------- Меню -------------------
@app.route("/api/menu")
def menu():
    with open("menu.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


# ------------------- Запуск -------------------
if __name__ == "__main__":
    init_pg()

    print("Сервер запущен: http://127.0.0.1:5000")

    app.run(host="0.0.0.0", port=5000, debug=True)
