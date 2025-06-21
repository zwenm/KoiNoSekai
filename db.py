import sqlite3

DB_PATH = "waifu.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS waifus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            name TEXT NOT NULL UNIQUE,
            age TEXT,
            personality TEXT,
            background TEXT,
            image_path TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_waifu(user_id, name, age, personality, background, image_path):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM waifus WHERE name = ?", (name,))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"Waifu dengan nama '{name}' sudah ada.")
    cursor.execute("""
        INSERT INTO waifus (telegram_user_id, name, age, personality, background, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, age, personality, background, image_path))
    conn.commit()
    conn.close()


def get_waifus_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM waifus WHERE telegram_user_id = ?", (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def delete_waifu_by_id(waifu_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM waifus WHERE id = ?", (waifu_id,))
    conn.commit()
    conn.close()

def get_waifu_by_id(waifu_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM waifus WHERE id = ?", (waifu_id,))
    result = cursor.fetchone()
    conn.close()
    return result