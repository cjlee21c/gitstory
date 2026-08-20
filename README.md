# GitStories

**Learn real engineering decisions by stepping into open-source debates.**

GitStories mines real pull requests and issues from open-source GitHub repositories and
turns them into short, interactive decision "stories." You read the context of an actual
engineering dilemma, decide what *you* would do at the key checkpoint, and then see what the
maintainers actually chose and why. Stories are generated with Anthropic's Claude models.

The app has two parts: a **FastAPI backend** (`backend/`) and a **React + Vite frontend**
(`frontend/`). To run it locally you start both.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20.19+** (or 22.12+) and npm — required by Vite 8
- **Git**
- A **GitHub personal access token** — used to read public repositories
- An **Anthropic API key** — used to generate stories (**this key is billed for usage**)

> Each person runs their own instance with their own keys. See
> [Getting the keys](#getting-the-keys) below.

---

## 1. Clone

```bash
git clone https://github.com/cjlee21c/gitstory.git
cd gitstory
```

## 2. Backend (FastAPI)

```bash
cd backend

# create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt
```

Create a file `backend/.env` with these two variables:

```env
GITHUB_TOKEN=ghp_your_token_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

- `GITHUB_TOKEN` and `ANTHROPIC_API_KEY` — your own keys.

> Both are required — the server won't start if either is missing.

Run the backend:

```bash
uvicorn app.main:app --reload
```

It serves at **http://localhost:8000**. On first start it automatically seeds a starter
library of stories (from `backend/seed_cache/`) and creates its SQLite database
(`backend/gitstory.db`) — no extra setup needed.

## 3. Frontend (React + Vite)

In a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

It serves at **http://localhost:5173** and talks to the backend at `http://localhost:8000`
by default. If your backend runs somewhere else, set `VITE_API_BASE_URL` (e.g. in a
`frontend/.env` file) to that URL.

## 4. Use it

1. Open **http://localhost:5173**.
2. **Browse Library** for ready-made stories, or **Find Repositories** to discover and mine
   new ones by domain and popularity.

---

## Getting the keys

- **GitHub token** — GitHub → *Settings → Developer settings → Personal access tokens*.
  A token with read access to public repositories is enough.
- **Anthropic API key** — create one at [console.anthropic.com](https://console.anthropic.com).
  Generating stories consumes API credits, so keep an eye on your usage.

## Deploying online

To host GitStories on the internet (instead of running it locally), see
[`docs/DEPLOY.md`](docs/DEPLOY.md).
