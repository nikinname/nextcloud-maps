from dataclasses import dataclass
from typing import Any

import httpx
from cryptography.fernet import InvalidToken

from app.config import Settings, get_settings
from app.crypto import decrypt_secret, encrypt_secret
from app.database import get_conn


class CredentialsInvalidError(RuntimeError):
    pass


@dataclass(frozen=True)
class NextcloudAccount:
    user_id: int
    server_url: str
    login_name: str
    app_password: str
    base_path: str
    exclude_paths: tuple[str, ...]


def get_bootstrap_admin_username(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return settings.admin_nc_username.strip()


def promote_configured_admin(conn, settings: Settings | None = None) -> int | None:
    admin_username = get_bootstrap_admin_username(settings)
    if not admin_username:
        return None
    row = conn.execute(
        """
        UPDATE app_users
        SET role = 'admin', updated_at = now()
        WHERE nextcloud_login_name = %s
        RETURNING id
        """,
        (admin_username,),
    ).fetchone()
    return int(row["id"]) if row else None


def get_or_create_user_from_nextcloud(
    server_url: str,
    login_name: str,
    app_password: str,
    nextcloud_user_id: str | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    normalized_server_url = server_url.rstrip("/")
    encrypted_password = encrypt_secret(app_password)
    old_app_password = _get_existing_app_password(normalized_server_url, login_name)

    with get_conn() as conn:
        user_count = conn.execute("SELECT count(*) AS count FROM app_users").fetchone()["count"]
        settings = get_settings()
        role = "admin" if login_name == get_bootstrap_admin_username(settings) or user_count == 0 else "user"
        row = conn.execute(
            """
            INSERT INTO app_users (
                nextcloud_server_url, nextcloud_login_name, nextcloud_user_id,
                display_name, role, app_password_encrypted, base_path, last_login_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (nextcloud_server_url, nextcloud_login_name) DO UPDATE SET
                nextcloud_user_id = COALESCE(EXCLUDED.nextcloud_user_id, app_users.nextcloud_user_id),
                display_name = COALESCE(EXCLUDED.display_name, app_users.display_name),
                app_password_encrypted = EXCLUDED.app_password_encrypted,
                credentials_invalid = false,
                credentials_error = NULL,
                credentials_checked_at = now(),
                last_login_at = now(),
                updated_at = now()
            RETURNING id, nextcloud_server_url, nextcloud_login_name, nextcloud_user_id, display_name, role, base_path,
                      credentials_invalid, credentials_error
            """,
            (normalized_server_url, login_name, nextcloud_user_id, display_name, role, encrypted_password, settings.nextcloud_base_path),
        ).fetchone()
        if row["role"] == "admin":
            conn.execute("UPDATE photos SET user_id = %s WHERE user_id IS NULL", (row["id"],))
        conn.commit()
        if old_app_password and old_app_password != app_password:
            _delete_nextcloud_app_password(normalized_server_url, login_name, old_app_password)
        return row


def get_user(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, nextcloud_server_url, nextcloud_login_name, nextcloud_user_id,
                   display_name, role, base_path, exclude_paths, disabled,
                   credentials_invalid, credentials_error, credentials_checked_at
            FROM app_users
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()


def get_account(user_id: int) -> NextcloudAccount:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, nextcloud_server_url, nextcloud_login_name, app_password_encrypted,
                   base_path, exclude_paths, disabled
            FROM app_users
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
    if not row or row["disabled"]:
        raise ValueError("User not found or disabled")
    return _account_from_row(row)


def get_default_account() -> NextcloudAccount:
    settings = get_settings()
    with get_conn() as conn:
        user_id = promote_configured_admin(conn, settings)
        conn.commit()
    if user_id is None:
        raise ValueError("No default account available. Log in with the configured admin user first.")
    return get_account(user_id)


def _account_from_row(row: dict[str, Any]) -> NextcloudAccount:
    exclude_paths = row["exclude_paths"] or ""
    try:
        app_password = decrypt_secret(row["app_password_encrypted"])
    except InvalidToken as exc:
        mark_credentials_invalid(int(row["id"]), "Stored app password cannot be decrypted. Reconnect Nextcloud.")
        raise CredentialsInvalidError("Stored app password cannot be decrypted. Reconnect Nextcloud.") from exc
    return NextcloudAccount(
        user_id=int(row["id"]),
        server_url=row["nextcloud_server_url"].rstrip("/"),
        login_name=row["nextcloud_login_name"],
        app_password=app_password,
        base_path=row["base_path"] or "/Photos",
        exclude_paths=tuple(item.strip() for item in exclude_paths.split(",") if item.strip()),
    )


def mark_credentials_invalid(user_id: int, message: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE app_users
            SET credentials_invalid = true,
                credentials_error = %s,
                credentials_checked_at = now(),
                updated_at = now()
            WHERE id = %s
            """,
            (message, user_id),
        )
        conn.commit()


def validate_stored_credentials(user_id: int) -> None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, app_password_encrypted FROM app_users WHERE id = %s AND disabled = false",
            (user_id,),
        ).fetchone()
    if not row:
        return
    try:
        decrypt_secret(row["app_password_encrypted"])
    except InvalidToken:
        mark_credentials_invalid(user_id, "Stored app password cannot be decrypted. Reconnect Nextcloud.")


def _get_existing_app_password(server_url: str, login_name: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT app_password_encrypted
            FROM app_users
            WHERE nextcloud_server_url = %s AND nextcloud_login_name = %s
            """,
            (server_url, login_name),
        ).fetchone()
    if not row:
        return None
    try:
        return decrypt_secret(row["app_password_encrypted"])
    except InvalidToken:
        return None


def _delete_nextcloud_app_password(server_url: str, login_name: str, app_password: str) -> None:
    try:
        response = httpx.delete(
            f"{server_url}/ocs/v2.php/core/apppassword",
            auth=(login_name, app_password),
            headers={"OCS-APIREQUEST": "true", "User-Agent": "Nextcloud Maps Companion"},
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        # Best effort: the old token may have already been revoked by the user.
        return
