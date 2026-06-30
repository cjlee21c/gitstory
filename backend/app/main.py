from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_answers, routes_discover, routes_library, routes_repos, routes_stories

app = FastAPI(title="GitStories API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(routes_repos.router)
app.include_router(routes_stories.router)
app.include_router(routes_discover.router)
app.include_router(routes_library.router)
app.include_router(routes_answers.router)


@app.get("/health")
def health():
    return {"status": "ok"}
