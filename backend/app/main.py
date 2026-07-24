import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_answers, routes_auth, routes_discover, routes_library, routes_repos, routes_stories
from app.api.deps import require_access_code
from app.db import create_db_and_tables

# App-wide access-code gate: every route requires the X-Access-Code header
# except the open paths listed in deps._OPEN_PATHS (health check, docs).
app = FastAPI(title="GitStories API", dependencies=[Depends(require_access_code)])


@app.on_event("startup")
def _on_startup() -> None:
    create_db_and_tables()


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
# routes_answers before routes_stories: the answers routes live under
# /stories/{id}/answers, and routes_stories' greedy /{story_id:path} catch-all
# would otherwise swallow them.
app.include_router(routes_repos.router)
app.include_router(routes_answers.router)
app.include_router(routes_stories.router)
app.include_router(routes_discover.router)
app.include_router(routes_library.router)
app.include_router(routes_auth.router)


@app.get("/health")
def health():
    return {"status": "ok"}
