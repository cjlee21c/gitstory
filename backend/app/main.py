from fastapi import FastAPI

app = FastAPI(title="GitStories API")


@app.get("/health")
def health():
    return {"status": "ok"}
