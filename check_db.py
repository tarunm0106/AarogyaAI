import sqlite3
import json

DB_PATH = "aarogya.db"

def check_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM prescriptions ORDER BY id DESC LIMIT 5").fetchall()
        for r in rows:
            print(f"ID: {r['id']}, Patient: {r['patient']}, Meds: {r['medicines']}")
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    check_db()
