from fastapi import FastAPI

from app.api import routes_repos, routes_stories

app = FastAPI(title="GitStories API")
app.include_router(routes_repos.router)
app.include_router(routes_stories.router)


@app.get("/health")
def health():
    return {"status": "ok"}
