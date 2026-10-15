import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "wednesday_memory.db"
MAX_HISTORY_EXCHANGES = 10


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, timeout=10)


def initialize_memory():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_exchange(user_message, assistant_message):
    if not user_message or not assistant_message:
        return
    
    initialize_memory()
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO conversations (user_message, assistant_message) VALUES (?, ?)",
            (user_message, assistant_message),
        )


def load_history():
    initialize_memory()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT user_message, assistant_message FROM conversations ORDER BY id DESC LIMIT ?",
            (MAX_HISTORY_EXCHANGES,),
        ).fetchall()

    history = []
    for user_message, assistant_message in reversed(rows):
        history.append(HumanMessage(content=user_message))
        history.append(AIMessage(content=assistant_message))
    return history


def clear_history():
    initialize_memory()
    with get_connection() as connection:
        connection.execute("DELETE FROM conversations")

