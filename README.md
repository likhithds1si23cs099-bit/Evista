# E-VISTA
### Educational Video Insight, Search, Translation & Abstraction

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Frontend-React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React"/>
  <img src="https://img.shields.io/badge/AI-Gemini%20%2B%20Whisper-8E75B2?style=for-the-badge" alt="AI stack"/>
</p>

**E-VISTA** is an educational video learning platform designed to help learners get more value from online lectures. It combines video discovery, speech transcription and AI-assisted learning tools in one workflow.

## ✨ What it does

- 🔎 Search for educational YouTube videos by topic.
- 🎙️ Transcribe video audio locally using OpenAI Whisper.
- 📝 Generate AI-assisted summaries with Gemini.
- 🌐 Translate learning content.
- 🧠 Create quizzes and flashcards for revision.
- 💬 Ask questions about learning content.
- 📈 Track learning progress through a dashboard.

## 🧱 Technology

| Layer | Technologies |
|---|---|
| Frontend | React, Tailwind CSS |
| Backend | Python, FastAPI |
| Speech transcription | Whisper |
| Generative AI | Google Gemini |
| Database | SQLite |

## ▶️ Run locally

The application source and full setup instructions are in the project folder:

**[Open the evista-2 project and setup guide](./evista-2/README.md)**

Quick start (macOS / Linux):

```bash
cd evista-2/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Gemini API key to `.env`, then start the backend:

```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 in your browser. See the [full README](./evista-2/README.md) for Windows instructions, configuration and troubleshooting.

## 📁 Repository structure

```text
Evista/
└── evista-2/
    ├── backend/
    ├── .vscode/
    └── README.md
```

## 🔐 Security

- Keep API keys in your local `.env` file.
- Never commit secrets or credentials.
- Use `.env.example` to document required environment variables without exposing values.

---

<p align="center">Built to make learning from educational videos more interactive and accessible.</p>
