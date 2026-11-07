# E-VISTA
<p align="center"><img src="./assets/project-banner.svg" alt="E-VISTA — AI-powered educational video learning" width="100%"/></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-Frontend-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React"/>
  <img src="https://img.shields.io/badge/AI-Gemini%20%2B%20Whisper-8E75B2?style=for-the-badge" alt="AI stack"/>
</p>

<p align="center"><b>Discover. Understand. Revise.</b><br/>An AI-assisted learning workspace that turns educational videos into useful study material.</p>

## ✨ Project overview
E-VISTA (Educational Video Insight, Search, Translation & Abstraction) helps learners move from watching a lecture to actively understanding and revising its content. It brings video discovery, transcription and AI-powered study tools into one workflow.

## 🚀 Key features
| Feature | What it helps you do |
|---|---|
| 🔎 Video discovery | Find educational YouTube videos by topic |
| 🎙️ Speech transcription | Convert video audio into text with Whisper |
| 🧠 AI summaries | Get concise learning summaries with Gemini |
| 🌐 Translation | Make learning content easier to access |
| 📝 Quiz & flashcards | Practise and revise important concepts |
| 💬 Content Q&A | Ask questions about the learning material |
| 📊 Learning dashboard | Review learning activity and progress |

## 🧩 How it works
```mermaid
flowchart LR
    A[Search educational topic] --> B[Select video]
    B --> C[Audio transcription]
    C --> D[AI processing]
    D --> E[Summary]
    D --> F[Translation]
    D --> G[Quiz and flashcards]
    D --> H[Ask questions]
    E --> I[Learning workspace]
    F --> I
    G --> I
    H --> I
```

## 🛠️ Technology stack
| Layer | Tools |
|---|---|
| Frontend | React, Tailwind CSS |
| Backend | Python, FastAPI |
| Speech-to-text | OpenAI Whisper |
| Generative AI | Google Gemini |
| Database | SQLite |

## ⚡ Run locally
See the detailed setup guide in **[evista-2/README.md](./evista-2/README.md)**.

```bash
git clone https://github.com/likhithds1si23cs099-bit/Evista.git
cd Evista/evista-2/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Gemini API key to the local `.env` file, then start the backend:

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000**. Refer to the detailed guide for configuration, frontend startup and troubleshooting.

## 📂 Repository layout
```text
Evista/
├── evista-2/
│   ├── backend/
│   ├── .vscode/
│   └── README.md
└── README.md
```

## 🔐 Security
- Store API keys in your local `.env` file.
- Never commit secrets, credentials or private tokens.
- Keep `.env.example` limited to variable names and safe placeholders.

---
<p align="center"><b>Built to make learning from educational videos more interactive and accessible.</b></p>
