"""
E-VISTA: Educational Video Insight Search, Translation and Abstraction
FastAPI backend: auth, YouTube search, Whisper transcription, Gemini summary /
translation / quiz / flashcards / chat, SQLite storage.

Run:  uvicorn main:app --reload --port 8000
"""
import os
import json
import time
import secrets
import hashlib
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

BASE = Path(__file__).parent
DB_PATH = BASE / "evista.db"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny / base / small / medium
MAX_TRANSCRIPT_CHARS = 150_000

app = FastAPI(title="E-VISTA")

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
_db_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _db_lock, db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                pw_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions(
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS videos(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                video_id TEXT NOT NULL,
                title TEXT, channel TEXT, duration INTEGER, thumbnail TEXT,
                transcript TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                language TEXT DEFAULT 'English',
                quiz_json TEXT DEFAULT '',
                cards_json TEXT DEFAULT '',
                status TEXT DEFAULT 'queued',
                progress INTEGER DEFAULT 0,
                message TEXT DEFAULT '',
                created TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, video_id)
            );
            CREATE TABLE IF NOT EXISTS results(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                video_row INTEGER NOT NULL,
                score INTEGER, total INTEGER,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


init_db()


def q(sql, params=(), one=False, commit=False):
    with _db_lock:
        conn = db()
        try:
            cur = conn.execute(sql, params)
            if commit:
                conn.commit()
                return cur.lastrowid
            rows = cur.fetchall()
            return (rows[0] if rows else None) if one else rows
        finally:
            conn.close()


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
def hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()


class Credentials(BaseModel):
    username: str
    password: str


def current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization[7:]
    row = q(
        "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",
        (token,),
        one=True,
    )
    if not row:
        raise HTTPException(401, "Invalid session")
    return {"id": row["id"], "username": row["username"]}


@app.post("/api/register")
def register(c: Credentials):
    name = c.username.strip()
    if len(name) < 3 or len(c.password) < 6:
        raise HTTPException(400, "Username >= 3 chars and password >= 6 chars required")
    if q("SELECT id FROM users WHERE username=?", (name,), one=True):
        raise HTTPException(400, "Username already taken")
    salt = secrets.token_hex(8)
    uid = q(
        "INSERT INTO users(username,salt,pw_hash) VALUES(?,?,?)",
        (name, salt, hash_pw(c.password, salt)),
        commit=True,
    )
    token = secrets.token_urlsafe(32)
    q("INSERT INTO sessions(token,user_id) VALUES(?,?)", (token, uid), commit=True)
    return {"token": token, "username": name}


@app.post("/api/login")
def login(c: Credentials):
    row = q("SELECT * FROM users WHERE username=?", (c.username.strip(),), one=True)
    if not row or hash_pw(c.password, row["salt"]) != row["pw_hash"]:
        raise HTTPException(401, "Invalid username or password")
    token = secrets.token_urlsafe(32)
    q("INSERT INTO sessions(token,user_id) VALUES(?,?)", (token, row["id"]), commit=True)
    return {"token": token, "username": row["username"]}


@app.get("/api/health")
def health():
    return {"status": "ok", "gemini_configured": bool(GEMINI_API_KEY)}


# --------------------------------------------------------------------------
# Gemini helper (with retry / rate-limit handling)
# --------------------------------------------------------------------------
_client = None


def gemini(prompt: str, json_mode: bool = False) -> str:
    global _client
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY is not set. Add it to backend/.env")
    from google import genai
    from google.genai import types

    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    cfg = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    last = None
    for attempt in range(4):
        try:
            r = _client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=cfg)
            return (r.text or "").strip()
        except Exception as e:  # rate limit / transient errors
            last = e
            time.sleep(2 * (2 ** attempt))
    raise HTTPException(502, f"Gemini request failed: {last}")


def parse_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text)


# --------------------------------------------------------------------------
# YouTube search
# --------------------------------------------------------------------------
@app.get("/api/search")
def search(q: str = "", user=Depends(current_user)):
    query = q.strip()
    if not query:
        raise HTTPException(400, "Empty query")
    from yt_dlp import YoutubeDL

    # Bias towards educational content
    with YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as y:
        info = y.extract_info(f"ytsearch12:{query} lecture tutorial", download=False)
    out = []
    for e in info.get("entries", []):
        if not e or not e.get("id"):
            continue
        dur = e.get("duration") or 0
        if dur and dur < 60:  # skip Shorts
            continue
        out.append(
            {
                "video_id": e["id"],
                "title": e.get("title"),
                "channel": e.get("channel") or e.get("uploader"),
                "duration": int(dur),
                "thumbnail": f"https://i.ytimg.com/vi/{e['id']}/hqdefault.jpg",
                "description": (e.get("description") or "")[:200],
            }
        )
    return out


# --------------------------------------------------------------------------
# Processing pipeline: download audio -> Whisper -> Gemini summary
# --------------------------------------------------------------------------
_whisper = None
_whisper_lock = threading.Lock()


def get_whisper():
    global _whisper
    with _whisper_lock:
        if _whisper is None:
            from faster_whisper import WhisperModel

            try:
                import torch  # optional

                use_gpu = torch.cuda.is_available()
            except Exception:
                use_gpu = False
            device, ctype = ("cuda", "float16") if use_gpu else ("cpu", "int8")
            _whisper = WhisperModel(WHISPER_MODEL, device=device, compute_type=ctype)
        return _whisper


def fmt_ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def update(row_id, **fields):
    keys = ", ".join(f"{k}=?" for k in fields)
    q(f"UPDATE videos SET {keys} WHERE id=?", (*fields.values(), row_id), commit=True)


def summarize(transcript: str, language: str) -> str:
    text = transcript[:MAX_TRANSCRIPT_CHARS]
    prompt = f"""You are an expert teaching assistant. Below is the timestamped transcript of an educational video.
Write a well-structured study summary in {language} using Markdown:
- A one-paragraph overview
- Sections with ## headings for each major topic
- Bullet points for key concepts, definitions and formulas
- A final "## Key Takeaways" list
Aim for roughly 500+ words for long videos. Remove filler and repetition. Do not invent facts.

TRANSCRIPT:
{text}"""
    return gemini(prompt)


def run_pipeline(row_id: int, video_id: str, language: str):
    try:
        from yt_dlp import YoutubeDL

        update(row_id, status="downloading", progress=5, message="Downloading audio...")
        with tempfile.TemporaryDirectory() as tmp:
            opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{tmp}/audio.%(ext)s",
                "quiet": True,
                "noplaylist": True,
            }
            with YoutubeDL(opts) as y:
                info = y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                path = y.prepare_filename(info)
            update(
                row_id,
                title=info.get("title"),
                channel=info.get("channel") or info.get("uploader"),
                duration=int(info.get("duration") or 0),
                thumbnail=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                status="transcribing",
                progress=15,
                message="Loading Whisper model...",
            )

            model = get_whisper()
            segments, tinfo = model.transcribe(path, vad_filter=True, beam_size=1)
            total = tinfo.duration or 1
            lines = []
            last_pct = 0
            for seg in segments:
                lines.append(f"[{fmt_ts(seg.start)}] {seg.text.strip()}")
                pct = 15 + int(60 * min(seg.end / total, 1.0))
                if pct != last_pct:
                    last_pct = pct
                    update(row_id, progress=pct, message=f"Transcribing... {fmt_ts(seg.end)} / {fmt_ts(total)}")
            transcript = "\n".join(lines)
            if not transcript.strip():
                raise RuntimeError("No speech detected in this video")
            update(row_id, transcript=transcript, status="summarizing", progress=80, message="Generating summary with Gemini...")

        summary = summarize(transcript, language)
        update(row_id, summary=summary, language=language, status="done", progress=100, message="Done")
    except Exception as e:
        update(row_id, status="error", message=str(e)[:500])


class ProcessReq(BaseModel):
    video_id: str
    title: Optional[str] = None
    channel: Optional[str] = None
    duration: Optional[int] = 0
    thumbnail: Optional[str] = None
    language: str = "English"


@app.post("/api/process")
def process(req: ProcessReq, user=Depends(current_user)):
    existing = q("SELECT * FROM videos WHERE user_id=? AND video_id=?", (user["id"], req.video_id), one=True)
    if existing and existing["status"] in ("done", "downloading", "transcribing", "summarizing", "queued"):
        return {"id": existing["id"]}
    if existing:  # previous error -> retry
        row_id = existing["id"]
        update(row_id, status="queued", progress=0, message="Queued")
    else:
        row_id = q(
            "INSERT INTO videos(user_id,video_id,title,channel,duration,thumbnail,status,message) VALUES(?,?,?,?,?,?,?,?)",
            (user["id"], req.video_id, req.title, req.channel, req.duration, req.thumbnail, "queued", "Queued"),
            commit=True,
        )
    threading.Thread(target=run_pipeline, args=(row_id, req.video_id, req.language), daemon=True).start()
    return {"id": row_id}


def own_video(row_id: int, user) -> sqlite3.Row:
    row = q("SELECT * FROM videos WHERE id=? AND user_id=?", (row_id, user["id"]), one=True)
    if not row:
        raise HTTPException(404, "Video not found")
    return row


@app.get("/api/videos/{row_id}")
def get_video(row_id: int, user=Depends(current_user)):
    r = own_video(row_id, user)
    d = dict(r)
    d["quiz"] = json.loads(r["quiz_json"]) if r["quiz_json"] else None
    d["cards"] = json.loads(r["cards_json"]) if r["cards_json"] else None
    d.pop("quiz_json"), d.pop("cards_json")
    return d


@app.get("/api/history")
def history(user=Depends(current_user)):
    rows = q(
        "SELECT id,video_id,title,channel,duration,thumbnail,status,created FROM videos WHERE user_id=? ORDER BY id DESC",
        (user["id"],),
    )
    res = q("SELECT * FROM results WHERE user_id=? ORDER BY id DESC", (user["id"],))
    total_q = len(res)
    acc = round(100 * sum(r["score"] for r in res) / max(1, sum(r["total"] for r in res)), 1) if res else 0
    done = sum(1 for r in rows if r["status"] == "done")
    badges = []
    if done >= 1:
        badges.append("First Video")
    if done >= 5:
        badges.append("Knowledge Seeker")
    if total_q >= 3:
        badges.append("Quiz Taker")
    if res and acc >= 80:
        badges.append("High Scorer")
    return {
        "videos": [dict(r) for r in rows],
        "stats": {"videos_done": done, "quizzes_taken": total_q, "accuracy": acc, "badges": badges},
    }


# --------------------------------------------------------------------------
# Translation, quiz, flashcards, chat
# --------------------------------------------------------------------------
class TranslateReq(BaseModel):
    language: str
    target: str = "summary"  # summary | transcript


@app.post("/api/videos/{row_id}/translate")
def translate(row_id: int, req: TranslateReq, user=Depends(current_user)):
    r = own_video(row_id, user)
    src = r["summary"] if req.target == "summary" else r["transcript"][:MAX_TRANSCRIPT_CHARS]
    if not src:
        raise HTTPException(400, "Nothing to translate yet")
    out = gemini(
        f"Translate the following text into {req.language}. Preserve Markdown formatting and "
        f"timestamps like [00:01:23]. Return only the translation.\n\n{src}"
    )
    return {"text": out}


@app.post("/api/videos/{row_id}/quiz")
def make_quiz(row_id: int, user=Depends(current_user)):
    r = own_video(row_id, user)
    if not r["summary"]:
        raise HTTPException(400, "Summary not ready")
    if r["quiz_json"]:
        return {"quiz": json.loads(r["quiz_json"])}
    prompt = f"""Create 6 multiple-choice questions in {r['language']} from this study summary.
Return a JSON array. Each item: {{"question": str, "options": [4 strings], "answer_index": 0-3, "explanation": str}}.
Randomise the position of the correct answer. Questions must be answerable from the text.

SUMMARY:
{r['summary']}"""
    try:
        quiz = parse_json(gemini(prompt, json_mode=True))
    except Exception:
        raise HTTPException(502, "Could not parse quiz from model output; try again")
    update(row_id, quiz_json=json.dumps(quiz))
    return {"quiz": quiz}


class ResultReq(BaseModel):
    score: int
    total: int


@app.post("/api/videos/{row_id}/quiz/result")
def save_result(row_id: int, req: ResultReq, user=Depends(current_user)):
    own_video(row_id, user)
    q(
        "INSERT INTO results(user_id,video_row,score,total) VALUES(?,?,?,?)",
        (user["id"], row_id, req.score, req.total),
        commit=True,
    )
    return {"ok": True}


@app.post("/api/videos/{row_id}/flashcards")
def make_cards(row_id: int, user=Depends(current_user)):
    r = own_video(row_id, user)
    if not r["summary"]:
        raise HTTPException(400, "Summary not ready")
    if r["cards_json"]:
        return {"cards": json.loads(r["cards_json"])}
    prompt = f"""Create 10 concise revision flashcards in {r['language']} from this summary.
Return a JSON array of {{"front": "term or question", "back": "short definition or answer"}}.

SUMMARY:
{r['summary']}"""
    try:
        cards = parse_json(gemini(prompt, json_mode=True))
    except Exception:
        raise HTTPException(502, "Could not parse flashcards from model output; try again")
    update(row_id, cards_json=json.dumps(cards))
    return {"cards": cards}


class ChatMsg(BaseModel):
    role: str
    text: str


class ChatReq(BaseModel):
    message: str
    history: List[ChatMsg] = []


@app.post("/api/videos/{row_id}/chat")
def chat(row_id: int, req: ChatReq, user=Depends(current_user)):
    r = own_video(row_id, user)
    ctx = (r["transcript"] or "")[:MAX_TRANSCRIPT_CHARS]
    convo = "\n".join(f"{m.role}: {m.text}" for m in req.history[-8:])
    prompt = f"""You are a helpful tutor. Answer the student's question using ONLY the video transcript below.
If the answer is not in the transcript, say so briefly. Mention timestamps when useful. Reply in the student's language.

TRANSCRIPT:
{ctx}

CONVERSATION SO FAR:
{convo}

student: {req.message}
tutor:"""
    return {"reply": gemini(prompt)}


# --------------------------------------------------------------------------
# Frontend (single-page React app served statically)
# --------------------------------------------------------------------------
STATIC = BASE / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
