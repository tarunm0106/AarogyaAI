import sqlite3

DB_PATH = "aarogya.db"

def check_instructions():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT raw_text FROM prescriptions ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            print(f"Instructions: {row['raw_text']}")
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    check_instructions()
