import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_answers, routes_discover, routes_library, routes_repos, routes_stories
from app.db import create_db_and_tables
from app.storage.seed import seed_cache_if_needed

app = FastAPI(title="GitStories API")


@app.on_event("startup")
def _on_startup() -> None:
    create_db_and_tables()
    seed_cache_if_needed()


# Allowed browser origins come from CORS_ORIGINS (comma-separated) in deploy;
# defaults to the local Vite dev servers so nothing breaks when running locally.
_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:5174"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
# routes_answers stays before routes_stories: both mount under /stories, and
# registering the narrower paths first means a greedy /{story_id:path} route
# added to routes_stories later can't swallow them.
app.include_router(routes_repos.router)
app.include_router(routes_answers.router)
app.include_router(routes_stories.router)
app.include_router(routes_discover.router)
app.include_router(routes_library.router)


@app.get("/health")
def health():
    return {"status": "ok"}
