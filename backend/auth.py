import re
import sqlite3
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import secrets
from typing import Any

import bcrypt

from database.db_manager import DB_PATH, init_db


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^\w\s]).{8,}$")
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


def _is_strong_password(password: str) -> bool:
    return bool(PASSWORD_REGEX.match(password))


def _parse_lock_until(lock_until_value: str | None) -> datetime | None:
    if not lock_until_value:
        return None
    try:
        return datetime.fromisoformat(lock_until_value)
    except ValueError:
        return None


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session(
    user_id: int,
    expires_hours: int = 24,
    db_path: Path = DB_PATH,
) -> str:
    init_db(db_path)

    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_session_token(raw_token)
    expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO UserSessions (user_id, token_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (user_id, token_hash, expires_at),
        )
        conn.commit()

    return raw_token


def get_user_by_session_token(
    session_token: str,
    db_path: Path = DB_PATH,
) -> tuple[bool, dict[str, Any] | str]:
    if not session_token:
        return False, "Missing session token."

    init_db(db_path)
    token_hash = _hash_session_token(session_token)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.id, u.username, u.email, u.last_login, s.expires_at
            FROM UserSessions s
            JOIN Users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_hash,),
        )
        row = cursor.fetchone()

        if not row:
            return False, "Invalid session token."

        user_id, username, user_email, last_login, expires_at_value = row
        expires_at = _parse_lock_until(expires_at_value)

        if not expires_at or expires_at <= datetime.utcnow():
            cursor.execute("DELETE FROM UserSessions WHERE token_hash = ?", (token_hash,))
            conn.commit()
            return False, "Session expired."

    return True, {"id": user_id, "username": username, "email": user_email, "last_login": last_login}


def revoke_user_session(
    session_token: str,
    db_path: Path = DB_PATH,
) -> None:
    if not session_token:
        return

    init_db(db_path)
    token_hash = _hash_session_token(session_token)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM UserSessions WHERE token_hash = ?", (token_hash,))
        conn.commit()


def register_user(
    username: str,
    email: str,
    password: str,
    db_path: Path = DB_PATH,
) -> tuple[bool, str]:
    username = username.strip()
    email = email.strip().lower()

    if not username:
        return False, "Username is required."

    if not _is_valid_email(email):
        return False, "Invalid email format."

    if not _is_strong_password(password):
        return (
            False,
            "Weak password. Use at least 8 characters with uppercase, lowercase, number, and special character.",
        )

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    init_db(db_path)

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Users (username, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (username, email, password_hash),
            )
            conn.commit()
        return True, "User registered successfully."
    except sqlite3.IntegrityError:
        return False, "Email already registered."


def login_user(
    email: str,
    password: str,
    db_path: Path = DB_PATH,
) -> tuple[bool, str | dict[str, Any]]:
    email = email.strip().lower()

    if not _is_valid_email(email):
        return False, "Invalid email format."

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, email, password_hash, failed_login_attempts, account_locked, lock_until
            FROM Users
            WHERE email = ?
            """,
            (email,),
        )
        row = cursor.fetchone()

        if not row:
            return False, "Invalid email or password."

        user_id, username, user_email, stored_hash, failed_attempts, account_locked, lock_until_value = row

        lock_until = _parse_lock_until(lock_until_value)
        now = datetime.utcnow()

        if account_locked and lock_until and lock_until > now:
            remaining_minutes = int((lock_until - now).total_seconds() // 60) + 1
            return False, f"Account is locked. Try again in {remaining_minutes} minute(s)."

        if account_locked and (lock_until is None or lock_until <= now):
            cursor.execute(
                """
                UPDATE Users
                SET failed_login_attempts = 0,
                    account_locked = 0,
                    lock_until = NULL
                WHERE id = ?
                """,
                (user_id,),
            )
            conn.commit()
            failed_attempts = 0

        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            failed_attempts += 1

            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                lock_until_time = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
                cursor.execute(
                    """
                    UPDATE Users
                    SET failed_login_attempts = ?,
                        account_locked = 1,
                        lock_until = ?
                    WHERE id = ?
                    """,
                    (failed_attempts, lock_until_time, user_id),
                )
                conn.commit()
                return False, "Account is locked for 15 minutes due to multiple failed login attempts."

            cursor.execute(
                """
                UPDATE Users
                SET failed_login_attempts = ?
                WHERE id = ?
                """,
                (failed_attempts, user_id),
            )
            conn.commit()
            return False, "Invalid email or password."

        cursor.execute(
            """
            UPDATE Users
            SET failed_login_attempts = 0,
                account_locked = 0,
                lock_until = NULL,
                last_login = ?
            WHERE id = ?
            """,
            (now.isoformat(), user_id),
        )
        conn.commit()

    return True, {"id": user_id, "username": username, "email": user_email, "last_login": now.isoformat()}
