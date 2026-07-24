from fastapi import APIRouter

router = APIRouter(tags=["auth"])


@router.get("/auth/check")
def auth_check():
    """Lightweight endpoint the frontend hits after the user enters the access
    code. It carries no logic of its own — reaching it means the app-wide gate
    (deps.require_access_code) already validated the X-Access-Code header, so a
    200 confirms the code is good and a 401 means it isn't."""
    return {"ok": True}
