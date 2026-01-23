import sqlite3
import os

DB_NAME = "alarms.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                days TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                label TEXT DEFAULT 'Alarm'
            )
        """)
    conn.close()

def add_alarm(time_str, days_str):
    conn = get_connection()
    with conn:
        conn.execute("INSERT INTO alarms (time, days, active) VALUES (?, ?, 1)", 
                     (time_str, days_str))
    conn.close()

def update_alarm(alarm_id, time_str, days_str):
    """Updates an existing alarm."""
    conn = get_connection()
    with conn:
        conn.execute("UPDATE alarms SET time = ?, days = ? WHERE id = ?", 
                     (time_str, days_str, alarm_id))
    conn.close()

def toggle_alarm(alarm_id, active_state):
    """Toggles alarm on (1) or off (0)."""
    conn = get_connection()
    with conn:
        conn.execute("UPDATE alarms SET active = ? WHERE id = ?", 
                     (1 if active_state else 0, alarm_id))
    conn.close()

def get_active_alarms():
    conn = get_connection()
    alarms = conn.execute("SELECT * FROM alarms WHERE active = 1").fetchall()
    conn.close()
    return alarms

def get_all_alarms():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM alarms ORDER BY time ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]