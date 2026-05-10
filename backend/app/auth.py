import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Cookie, Depends, HTTPException, Response, status

from app.config import get_settings
from app.users import get_user


def create_session_token(user_id: int) -> str:
    settings = get_settings()
    payload = {
        "uid": user_id,
        "exp": int(time.time()) + settings.session_max_age_seconds,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")
    signature = _sign(payload_b64)
    return f"{payload_b64}.{signature}"


def set_session_cookie(response: Response, user_id: int) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        create_session_token(user_id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.session_max_age_seconds,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(get_settings().session_cookie_name)


def current_user(companion_session: str | None = Cookie(default=None, alias="companion_session")) -> dict[str, Any]:
    if not companion_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = verify_session_token(companion_session)
    user = get_user(user_id)
    if not user or user["disabled"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user


def current_admin(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def verify_session_token(token: str) -> int:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    payload_json = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4))
    payload = json.loads(payload_json)
    if int(payload["exp"]) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return int(payload["uid"])


def _sign(payload_b64: str) -> str:
    digest = hmac.new(
        get_settings().app_secret_key.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
