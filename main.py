import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="StarMusic Backend")

# Настройка CORS, чтобы твой HTML мог общаться с этим сервером
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели данных
class User(BaseModel):
    phone: str
    name: Optional[str] = None

class Song(BaseModel):
    id: int
    title: str
    artist: str
    url: str

# Работа с БД
DB_PATH = "star_music.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (phone TEXT PRIMARY KEY, name TEXT)''')
    # Таблица песен
    cursor.execute('''CREATE TABLE IF NOT EXISTS songs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       title TEXT, artist TEXT, url TEXT)''')
    
    # Добавим стартовые песни, если таблица пуста
    cursor.execute("SELECT COUNT(*) FROM songs")
    if cursor.fetchone()[0] == 0:
        sample_songs = [
            ("Lofi Hip Hop", "Star Artist", "https://example.com/song1.mp3"),
            ("Night Drive", "Moonlight", "https://example.com/song2.mp3")
        ]
        cursor.executemany("INSERT INTO songs (title, artist, url) VALUES (?, ?, ?)", sample_songs)
    
    conn.commit()
    conn.close()

init_db()

@app.post("/auth/send-code")
async def send_code(user: User):
    # Имитация отправки кода. В реальности здесь вызывается API SMS-сервиса.
    return {"status": "success", "message": f"Code sent to {user.phone}"}

@app.post("/auth/verify")
async def verify(user: User):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE phone = ?", (user.phone,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {"status": "exists", "name": result[0]}
    return {"status": "new_user"}

@app.post("/auth/register")
async def register(user: User):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (phone, name) VALUES (?, ?)", (user.phone, user.name))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User already exists")

@app.get("/songs", response_model=List[Song])
async def get_songs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, artist, url FROM songs")
    rows = cursor.fetchall()
    conn.close()
    return [Song(id=r[0], title=r[1], artist=r[2], url=r[3]) for r in rows]

if __name__ == "__main__":
    import uvicorn
    # Render передает порт через переменную окружения
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)