from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models.db_models import Answer, User

router = APIRouter(tags=["answers"])


class AnswerRequest(BaseModel):
    student_id: str
    reflection: str
    selected_option: str | None = None


def _get_or_create_user(session: Session, student_id: str) -> User:
    user = session.exec(select(User).where(User.student_id == student_id)).first()
    if user is None:
        user = User(student_id=student_id, display_name=student_id)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.post("/stories/{story_id:path}/answers", status_code=200)
def save_answer(story_id: str, body: AnswerRequest, session: Session = Depends(get_session)):
    if not body.student_id.strip():
        raise HTTPException(status_code=400, detail="student_id is required")
    if not body.reflection.strip():
        raise HTTPException(status_code=400, detail="reflection is required")

    user = _get_or_create_user(session, body.student_id.strip())

    # One answer per (student, story) — latest wins, matching the old one-file
    # -per-pair behavior.
    answer = session.exec(
        select(Answer).where(Answer.user_id == user.id, Answer.story_id == story_id)
    ).first()
    if answer is None:
        answer = Answer(user_id=user.id, story_id=story_id, kind="reflection")
    answer.selected_option = body.selected_option
    answer.response_text = body.reflection
    answer.submitted_at = datetime.now(timezone.utc)
    session.add(answer)
    session.commit()
    return {"status": "saved"}


@router.get("/stories/{story_id:path}/answers")
def list_answers(story_id: str, session: Session = Depends(get_session)):
    rows = session.exec(
        select(Answer, User).join(User, Answer.user_id == User.id).where(Answer.story_id == story_id)
    ).all()
    return [
        {
            "student_id": user.student_id,
            "story_id": answer.story_id,
            "selected_option": answer.selected_option,
            "reflection": answer.response_text,
            "submitted_at": answer.submitted_at.isoformat(),
        }
        for answer, user in rows
    ]
