import os, sqlite3, threading, time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import telebot

app = FastAPI()

# --- КОНФИГУРАЦИЯ ---
# Твой токен уже здесь. Бот нужен для авторизации, чтобы в базу не писали боты.
BOT_TOKEN = "8785249686:AAFFXtYp1NKFwI7jzLExljnFBX7_bFDpDFE"
bot = telebot.TeleBot(BOT_TOKEN)
DB_NAME = "starmusic.db"
auth_sessions = {}

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Таблица для пользователей (синхронизация профилей)
    cursor.execute('CREATE TABLE IF NOT EXISTS users (phone TEXT PRIMARY KEY, name TEXT)')
    # Таблица для песен (общая для всех устройств)
    cursor.execute('''CREATE TABLE IF NOT EXISTS tracks 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       title TEXT, artist TEXT, url TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- МОДЕЛИ ДАННЫХ ---
class TrackData(BaseModel):
    title: str
    artist: str
    url: str

class UserRequest(BaseModel):
    phone: str
    name: str = None

# --- ЭНДПОИНТЫ ДЛЯ РАБОТЫ С ПЕСНЯМИ ---

@app.get("/api/tracks")
async def get_tracks():
    """Отдает список всех песен из базы данных для всех устройств"""
    conn = sqlite3.connect(DB_NAME)
    # Сортируем: новые песни будут сверху
    tracks = conn.execute("SELECT title, artist, url FROM tracks ORDER BY id DESC").fetchall()
    conn.close()
    return [{"title": t[0], "artist": t[1], "url": t[2]} for t in tracks]

@app.post("/api/add-track")
async def add_track(data: TrackData):
    """Принимает новую песню от пользователя и сохраняет её в общую базу"""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT INTO tracks (title, artist, url) VALUES (?, ?, ?)", 
                     (data.title, data.artist, data.url))
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# --- ЭНДПОИНТЫ АВТОРИЗАЦИИ ---

@app.post("/api/init-auth")
async def init_auth(data: UserRequest):
    phone = data.phone.replace("+", "").strip()
    auth_sessions[phone] = False
    return {"bot_user": bot.get_me().username}

@app.get("/api/status/{phone}")
async def check_status(phone: str):
    clean_phone = phone.replace("+", "").strip()
    if auth_sessions.get(clean_phone):
        conn = sqlite3.connect(DB_NAME)
        user = conn.execute("SELECT name FROM users WHERE phone=?", (clean_phone,)).fetchone()
        conn.close()
        return {"ready": True, "exists": bool(user), "name": user[0] if user else None}
    return {"ready": False}

@app.post("/api/register")
async def register(data: UserRequest):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (data.phone, data.name))
    conn.commit()
    conn.close()
    return {"ok": True}

# --- ЛОГИКА ТЕЛЕГРАМ-БОТА ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("🚀 Подтвердить вход в StarMusic", request_contact=True))
    bot.send_message(message.chat.id, "Для доступа к сайту нажми на кнопку:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number.replace("+", "").strip()
    auth_sessions[phone] = True
    bot.send_message(message.chat.id, "✅ Доступ разрешен! Можешь добавлять музыку.")

def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot, daemon=True).start()

# --- ВЫДАЧА HTML (без изменений) ---
@app.get("/", response_class=HTMLResponse)
async def home():
    # Здесь твой текущий HTML код
    return """...твой существующий HTML..."""

if __name__ == "__main__":
    import uvicorn
    # Запуск сервера
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
