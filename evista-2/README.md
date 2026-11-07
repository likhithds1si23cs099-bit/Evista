# E-VISTA – Educational Video Insight Search, Translation and Abstraction

Search YouTube lectures → transcribe locally with Whisper → Gemini summary, translation,
quiz, flashcards, chat → progress dashboard. Backend: FastAPI + SQLite. Frontend: React (served by FastAPI, no Node needed).

## 1. Prerequisites
- Python 3.10+ (check: `python --version`)
- A free Gemini API key: https://aistudio.google.com/apikey
- Internet connection (first run downloads the Whisper model, ~150 MB for `base`)

## 2. Setup in VS Code
Open the `evista` folder in VS Code (File → Open Folder), then open the terminal (Ctrl + `) and run:

**Windows (PowerShell)**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
**macOS / Linux**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `backend/.env` and paste your key: `GEMINI_API_KEY=...`

In VS Code press Ctrl+Shift+P → "Python: Select Interpreter" → choose the `.venv` one.

## 3. Run
```bash
uvicorn main:app --reload --port 8000
```
Open http://localhost:8000 → Register → Search a topic → **Analyse video**.

API docs: http://localhost:8000/docs

## Tips
- Use videos under ~30 min for quick results on CPU. Set `WHISPER_MODEL=tiny` in `.env` for speed.
- With an NVIDIA GPU + CUDA, Whisper auto-uses it.
- The first video is slower because the Whisper model downloads once.
- If you hit Gemini rate limits, the backend retries automatically; the free tier has per-minute limits.
- If YouTube download breaks, update yt-dlp: `pip install -U yt-dlp`.

## Project layout
```
evista/
  backend/
    main.py            FastAPI app (all endpoints + pipeline)
    requirements.txt
    .env.example
    static/index.html  React UI (Tailwind + React via CDN)
```
