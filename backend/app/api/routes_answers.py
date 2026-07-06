import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["answers"])

ANSWERS_DIR = Path(__file__).resolve().parent.parent.parent / "answers"


def _safe(value: str) -> str:
    return re.sub(r"[^\w\-]", "_", value)


def _path_for(story_id: str, student_id: str) -> Path:
    return ANSWERS_DIR / f"{_safe(story_id)}__{_safe(student_id)}.json"


class AnswerRequest(BaseModel):
    student_id: str
    reflection: str
    selected_option: str | None = None


@router.post("/stories/{story_id:path}/answers", status_code=200)
def save_answer(story_id: str, body: AnswerRequest):
    if not body.student_id.strip():
        raise HTTPException(status_code=400, detail="student_id is required")
    if not body.reflection.strip():
        raise HTTPException(status_code=400, detail="reflection is required")

    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    path = _path_for(story_id, body.student_id)
    payload = {
        "student_id": body.student_id,
        "story_id": story_id,
        "selected_option": body.selected_option,
        "reflection": body.reflection,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "saved"}


@router.get("/stories/{story_id:path}/answers")
def list_answers(story_id: str):
    if not ANSWERS_DIR.exists():
        return []
    prefix = _safe(story_id) + "__"
    results = []
    for path in sorted(ANSWERS_DIR.glob(f"{prefix}*.json")):
        try:
            results.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return results
