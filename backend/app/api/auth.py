from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import AnyHttpUrl, BaseModel

from app.auth import clear_session_cookie, current_user, set_session_cookie
from app.config import get_settings
from app.users import get_or_create_user_from_nextcloud, get_user, validate_stored_credentials


router = APIRouter(prefix="/api/auth", tags=["auth"])
PENDING_FLOWS: dict[str, dict[str, Any]] = {}
FLOW_TTL_MINUTES = 10
NEXTCLOUD_LOGIN_HEADERS = {"User-Agent": "Nextcloud Maps Companion"}


class LoginStartRequest(BaseModel):
    nextcloud_url: AnyHttpUrl | None = None


class LoginPollRequest(BaseModel):
    flow_id: str


@router.get("/me")
def me(user: dict[str, Any] = Depends(current_user)):
    validate_stored_credentials(int(user["id"]))
    user = get_user(int(user["id"])) or user
    return {
        "id": user["id"],
        "loginName": user["nextcloud_login_name"],
        "displayName": user["display_name"],
        "role": user["role"],
        "basePath": user["base_path"],
        "credentialsInvalid": user["credentials_invalid"],
        "credentialsError": user["credentials_error"],
    }


@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"status": "ok"}


@router.post("/nextcloud/start")
def start_nextcloud_login(payload: LoginStartRequest):
    settings = get_settings()
    server_url = str(payload.nextcloud_url or settings.nextcloud_url).rstrip("/")
    try:
        response = httpx.post(f"{server_url}/index.php/login/v2", headers=NEXTCLOUD_LOGIN_HEADERS, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Nextcloud login flow failed: {exc}") from exc

    data = response.json()
    flow_id = uuid4().hex
    PENDING_FLOWS[flow_id] = {
        "server_url": server_url,
        "poll": data["poll"],
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=FLOW_TTL_MINUTES),
    }
    _cleanup_expired_flows()
    return {
        "flowId": flow_id,
        "loginUrl": data["login"],
        "expiresIn": FLOW_TTL_MINUTES * 60,
    }


@router.post("/nextcloud/poll")
def poll_nextcloud_login(payload: LoginPollRequest, response: Response):
    flow = PENDING_FLOWS.get(payload.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Login flow not found")
    if flow["expires_at"] < datetime.now(timezone.utc):
        PENDING_FLOWS.pop(payload.flow_id, None)
        raise HTTPException(status_code=410, detail="Login flow expired")

    poll = flow["poll"]
    try:
        nc_response = httpx.post(
            poll["endpoint"],
            data={"token": poll["token"]},
            headers=NEXTCLOUD_LOGIN_HEADERS,
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Nextcloud login poll failed: {exc}") from exc

    if nc_response.status_code in (400, 401, 404):
        return {"status": "pending"}
    if nc_response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Nextcloud login poll failed: {nc_response.status_code}")

    data = nc_response.json()
    user = get_or_create_user_from_nextcloud(
        server_url=data.get("server", flow["server_url"]),
        login_name=data["loginName"],
        app_password=data["appPassword"],
        nextcloud_user_id=data.get("loginName"),
    )
    PENDING_FLOWS.pop(payload.flow_id, None)
    set_session_cookie(response, int(user["id"]))
    return {
        "status": "authenticated",
        "user": {
            "id": user["id"],
            "loginName": user["nextcloud_login_name"],
            "displayName": user["display_name"],
            "role": user["role"],
            "basePath": user["base_path"],
            "credentialsInvalid": user["credentials_invalid"],
            "credentialsError": user["credentials_error"],
        },
    }


def _cleanup_expired_flows() -> None:
    now = datetime.now(timezone.utc)
    for flow_id, flow in list(PENDING_FLOWS.items()):
        if flow["expires_at"] < now:
            PENDING_FLOWS.pop(flow_id, None)
