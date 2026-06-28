# Manipal Chatbot 🤖

An AI-powered campus assistant chatbot for Manipal University — built to answer student queries about placements, faculty, events, academics, and more.

---

## Project Structure
Manipal-Chatbot/
├── frontend/          # Next.js web application (UI)
├── backend/           # FastAPI server (API gateway)
├── ai-engine/         # LangChain RAG pipeline + LLM logic
├── data-engineering/  # Data ingestion, vectorization scripts
├── devops/            # Dockerfiles, CI/CD configs
├── .env.example       # Environment variable template
├── .gitignore
└── README.md
---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, Tailwind CSS |
| Backend | Python, FastAPI |
| AI / RAG | LangChain, Llama 3 / OpenAI |
| Vector DB | Pinecone |
| Database | PostgreSQL, MongoDB |
| Deployment | Vercel (frontend), Render/AWS (backend) |
| CI/CD | GitHub Actions |

---

## Team

| Domain | Members |
|---|---|
| Frontend & UI/UX | Shivansh, Aadil, Ruhani |
| AI Engineering | Ruhani, Aditya, Akshat |
| Backend & API | Subhan |
| Data Engineering | Aadil |
| DevOps | Arindam , Anish , Sanjayram|

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/Arindam-katoch/Manipal-Chatbot.git
cd Manipal-Chatbot
```

### 2. Set up environment variables
```bash
cp .env.example .env
```
Open `.env` and fill in your API keys. **Never commit the `.env` file.**

### 3. Go to your team folder
```bash
cd frontend          # frontend team
cd backend           # backend team
cd ai-engine         # AI team
cd data-engineering  # data team
cd devops            # devops team
```

---

## How to Contribute — Read This

### Step 1 — Pull latest main before starting
```bash
git checkout main
git pull origin main
```

### Step 2 — Create your own branch
```bash
git checkout -b yourname/what-you-are-building
```
Examples:
- `shivansh/navbar-component`
- `aditya/rag-pipeline-setup`
- `akshat/embedding-script`

### Step 3 — Commit your work
```bash
git add .
git commit -m "feat: describe what you built"
```

Good commit messages:
- `feat: add chat bubble UI component`
- `fix: resolve CORS error on /api/chat`
- `data: ingest placement records for 2023`

### Step 4 — Push your branch
```bash
git push origin yourname/what-you-are-building
```

### Step 5 — Open a Pull Request
- Go to `github.com/Arindam-katoch/Manipal-Chatbot`
- Click **Compare & pull request**
- Add a clear title and description
- Submit — DevOps will review and merge

---

## Branch Rules

- Nobody pushes directly to main — ever
- All code goes through a Pull Request
- At least 1 approval required before merging
- Keep your branch updated with main regularly

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.
Never share your `.env` or commit it to the repo.
If you need a new variable added, tell the DevOps team to update `.env.example`.

---

## Deployment

| Service | Platform | Trigger |
|---|---|---|
| Frontend | Vercel | Auto-deploys on merge to main |
| Backend | Render / AWS | Auto-deploys on merge to main |

Every open PR gets a Vercel preview link automatically — check the bot comment inside your PR.

---

## Need Help?

- Repo issues → open a GitHub Issue
- Urgent → contact Arindam (DevOps) on WhatsApp
EOF
