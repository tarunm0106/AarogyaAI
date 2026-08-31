import os
import json
import base64
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from PIL import Image
import google.generativeai as genai
from gtts import gTTS
import io

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# --- API Configuration ---
GEMINI_API_KEY = "AIzaSyDTJ5jZEm3kexoWLH9BZlJfmDqykrGdLd8"
genai.configure(api_key=GEMINI_API_KEY)

DB_PATH = "aarogya.db"
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            patient   TEXT,
            phone     TEXT,
            date      TEXT,
            medicines TEXT,
            notes     TEXT,
            audio     TEXT,
            raw_text  TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            med_name TEXT,
            dose     TEXT,
            timing   TEXT,
            meal     TEXT,
            active   INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

LANG_CODES = {
    "english":  "en",
    "hindi":    "hi",
    "kannada":  "kn",
    "telugu":   "te",
    "tamil":    "ta",
    "marathi":  "mr",
}

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index_route():
    return send_from_directory(".", "index.html")

# ── 1. Analyze prescription image ─────────────────────────────────────────────
@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    language  = request.form.get("language", "english").lower()
    patient   = request.form.get("patient", "Patient")
    phone     = request.form.get("phone", "")

    file = request.files["image"]
    img_bytes = file.read()
    
    # Process image for Gemini
    image = Image.open(io.BytesIO(img_bytes))

    model = genai.GenerativeModel('gemini-flash-latest')

    # Step 1 – Extract medicines as JSON
    extract_prompt = """Extract all medicines from this prescription image.
Return ONLY a valid JSON object with this exact structure:
{
  "medicines": [
    {
      "name": "medicine name",
      "dosage": "e.g. 500mg",
      "frequency": "e.g. twice daily",
      "duration": "e.g. 5 days",
      "instructions": "e.g. after food"
    }
  ],
  "doctor_notes": "any additional notes or empty string"
}
If you cannot read the prescription clearly, make a best-effort extraction.
Return ONLY the JSON, nothing else. Do not use markdown code blocks."""

    try:
        response = model.generate_content([extract_prompt, image])
        raw = response.text.strip()
        
        # Cleanup response
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        data = json.loads(raw)
    except Exception as e:
        print(f"Extraction Error: {e}")
        data = {"medicines": [], "doctor_notes": "Could not extract data clearly."}

    medicines   = data.get("medicines", [])
    doctor_notes = data.get("doctor_notes", "")

    # Step 2 – Simplified instructions in chosen language
    simplify_prompt = f"""You are a healthcare assistant helping rural patients in India.
Given this prescription data:
{json.dumps(data, indent=2)}

Write simple, clear instructions that a farmer with no medical education can understand.
Translate the instructions to {language}.
Use simple words. Format as a numbered list.
For each medicine include:
  - Its name (phonetic if non-English)
  - How many tablets / ml
  - When to take (morning/afternoon/night using meal references like "after breakfast")
  - For how many days
  - Any warnings (empty stomach, avoid driving, etc.)
End with any doctor's notes simplified.
Return plain text only, no JSON."""

    try:
        response = model.generate_content(simplify_prompt)
        instructions = response.text.strip()
    except Exception as e:
        print(f"Simplification Error: {e}")
        instructions = "Sorry, I could not simplify the instructions at this time."

    # Step 3 – Text-to-speech
    lang_code = LANG_CODES.get(language, "en")
    audio_filename = f"rx_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    try:
        tts = gTTS(text=instructions, lang=lang_code, slow=False)
        tts.save(audio_path)
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_filename = None

    # Step 4 – Save to DB
    conn = get_db()
    conn.execute(
        "INSERT INTO prescriptions (patient, phone, date, medicines, notes, audio, raw_text) VALUES (?,?,?,?,?,?,?)",
        (patient, phone, datetime.now().strftime("%Y-%m-%d %H:%M"),
         json.dumps(medicines), doctor_notes, audio_filename, instructions)
    )
    conn.commit()
    rx_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    return jsonify({
        "id":           rx_id,
        "medicines":    medicines,
        "doctor_notes": doctor_notes,
        "instructions": instructions,
        "audio_url":    f"/api/audio/{audio_filename}" if audio_filename else None,
        "language":     language,
    })

# ── 2. Serve audio files ───────────────────────────────────────────────────────
@app.route("/api/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

# ── 3. Prescription history ────────────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def history():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, patient, phone, date, medicines, notes, audio FROM prescriptions ORDER BY id DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id":       r["id"],
            "patient":  r["patient"],
            "phone":    r["phone"],
            "date":     r["date"],
            "medicines": json.loads(r["medicines"]) if r["medicines"] else [],
            "notes":    r["notes"],
            "audio_url": f"/api/audio/{r['audio']}" if r["audio"] else None,
        })
    return jsonify(result)

@app.route("/api/history/<int:rx_id>", methods=["DELETE"])
def delete_rx(rx_id):
    conn = get_db()
    conn.execute("DELETE FROM prescriptions WHERE id=?", (rx_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/history", methods=["DELETE"])
def clear_history():
    conn = get_db()
    conn.execute("DELETE FROM prescriptions")
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# ── 4. Reminders ───────────────────────────────────────────────────────────────
@app.route("/api/reminders", methods=["GET"])
def get_reminders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM reminders WHERE active=1 ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/reminders", methods=["POST"])
def add_reminder():
    body = request.get_json()
    conn = get_db()
    conn.execute(
        "INSERT INTO reminders (med_name, dose, timing, meal) VALUES (?,?,?,?)",
        (body.get("med_name",""), body.get("dose",""),
         body.get("timing",""), body.get("meal","After food"))
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({"id": rid, "ok": True})

@app.route("/api/reminders/<int:rid>", methods=["DELETE"])
def delete_reminder(rid):
    conn = get_db()
    conn.execute("DELETE FROM reminders WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# ── 5. Voice assistant chat ────────────────────────────────────────────────────
@app.route("/api/voice-query", methods=["POST"])
def voice_query():
    body = request.get_json()
    question = body.get("question", "")
    language  = body.get("language", "english").lower()
    context   = body.get("context", "")   # recent medicines JSON string

    model = genai.GenerativeModel('gemini-flash-latest')
    prompt = f"""You are AarogyaAI, a helpful healthcare assistant for rural patients in India.
Current prescription context: {context if context else 'No prescription uploaded yet.'}

User question: {question}

Answer in simple, clear {language}. Keep the answer concise (2–4 sentences).
If the question is unrelated to health/medicines, politely redirect.
Return plain text only."""

    try:
        response = model.generate_content(prompt)
        answer = response.text.strip()
    except Exception as e:
        print(f"Voice Query Error: {e}")
        answer = "I'm sorry, I'm having trouble processing that right now."

    # TTS for the answer
    lang_code = LANG_CODES.get(language, "en")
    audio_filename = f"voice_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    try:
        tts = gTTS(text=answer, lang=lang_code, slow=False)
        tts.save(audio_path)
    except Exception as e:
        print(f"Voice TTS Error: {e}")
        audio_filename = None

    return jsonify({
        "answer":    answer,
        "audio_url": f"/api/audio/{audio_filename}" if audio_filename else None
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
