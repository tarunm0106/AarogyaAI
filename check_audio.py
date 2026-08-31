import sqlite3

DB_PATH = "aarogya.db"

def check_audio_filename():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT audio FROM prescriptions WHERE id=19").fetchone()
        if row:
            print(f"Audio Filename: {row['audio']}")
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    check_audio_filename()
