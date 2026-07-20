from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_answers, routes_discover, routes_library, routes_repos, routes_stories
from app.db import create_db_and_tables

app = FastAPI(title="GitStories API")


@app.on_event("startup")
def _on_startup() -> None:
    create_db_and_tables()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# routes_answers before routes_stories: the answers routes live under
# /stories/{id}/answers, and routes_stories' greedy /{story_id:path} catch-all
# would otherwise swallow them.
app.include_router(routes_repos.router)
app.include_router(routes_answers.router)
app.include_router(routes_stories.router)
app.include_router(routes_discover.router)
app.include_router(routes_library.router)


@app.get("/health")
def health():
    return {"status": "ok"}
