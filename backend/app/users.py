from dataclasses import dataclass
from typing import Any

from app.config import Settings, get_settings
from app.crypto import decrypt_secret, encrypt_secret
from app.database import get_conn


@dataclass(frozen=True)
class NextcloudAccount:
    user_id: int
    server_url: str
    login_name: str
    app_password: str
    base_path: str
    exclude_paths: tuple[str, ...]


def bootstrap_env_user(conn, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    existing = conn.execute("SELECT id FROM app_users ORDER BY id LIMIT 1").fetchone()
    if existing:
        return int(existing["id"])

    role = "admin"
    row = conn.execute(
        """
        INSERT INTO app_users (
            nextcloud_server_url, nextcloud_login_name, role,
            app_password_encrypted, base_path, exclude_paths
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            str(settings.nextcloud_url).rstrip("/"),
            settings.nextcloud_username,
            role,
            encrypt_secret(settings.nextcloud_app_password),
            settings.nextcloud_base_path,
            settings.nextcloud_exclude_paths,
        ),
    ).fetchone()
    return int(row["id"])


def get_or_create_user_from_nextcloud(
    server_url: str,
    login_name: str,
    app_password: str,
    nextcloud_user_id: str | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    normalized_server_url = server_url.rstrip("/")
    encrypted_password = encrypt_secret(app_password)

    with get_conn() as conn:
        user_count = conn.execute("SELECT count(*) AS count FROM app_users").fetchone()["count"]
        role = "admin" if user_count == 0 else "user"
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
                last_login_at = now(),
                updated_at = now()
            RETURNING id, nextcloud_server_url, nextcloud_login_name, nextcloud_user_id, display_name, role, base_path
            """,
            (normalized_server_url, login_name, nextcloud_user_id, display_name, role, encrypted_password, "/Photos"),
        ).fetchone()
        conn.commit()
        return row


def get_user(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, nextcloud_server_url, nextcloud_login_name, nextcloud_user_id,
                   display_name, role, base_path, exclude_paths, disabled
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
        user_id = bootstrap_env_user(conn, settings)
        conn.execute("UPDATE photos SET user_id = %s WHERE user_id IS NULL", (user_id,))
        conn.commit()
    return get_account(user_id)


def _account_from_row(row: dict[str, Any]) -> NextcloudAccount:
    exclude_paths = row["exclude_paths"] or ""
    return NextcloudAccount(
        user_id=int(row["id"]),
        server_url=row["nextcloud_server_url"].rstrip("/"),
        login_name=row["nextcloud_login_name"],
        app_password=decrypt_secret(row["app_password_encrypted"]),
        base_path=row["base_path"] or "/Photos",
        exclude_paths=tuple(item.strip() for item in exclude_paths.split(",") if item.strip()),
    )
