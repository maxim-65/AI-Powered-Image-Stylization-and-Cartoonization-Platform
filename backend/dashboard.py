import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from database.db_manager import DB_PATH, init_db


UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_file(
    file_bytes: bytes,
    original_filename: str,
    uploads_dir: Path = UPLOADS_DIR,
) -> str:
    uploads_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(original_filename).suffix or ".png"
    unique_filename = f"{uuid4().hex}{extension}"
    output_path = uploads_dir / unique_filename
    output_path.write_bytes(file_bytes)
    return str(output_path)


def save_image_history(
    user_id: int,
    original_path: str,
    processed_path: str,
    style: str,
    db_path: Path = DB_PATH,
) -> tuple[bool, int | str]:
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ImageHistory (user_id, original_path, processed_path, style, is_paid)
            VALUES (?, ?, ?, ?, 0)
            """,
            (user_id, original_path, processed_path, style),
        )
        history_id = cursor.lastrowid
        conn.commit()

    return True, history_id


def get_user_image_history(user_id: int, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                ih.id,
                ih.user_id,
                ih.original_path,
                ih.processed_path,
                ih.style,
                ih.is_paid,
                COALESCE(
                    (
                        SELECT t.status
                        FROM Transactions t
                        WHERE t.image_history_id = ih.id
                        ORDER BY t.id DESC
                        LIMIT 1
                    ),
                    'unpaid'
                ) AS payment_status
            FROM ImageHistory ih
            WHERE ih.user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()

    return [dict(row) for row in rows]


def get_user_profile(user_id: int, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                username,
                email,
                last_login,
                subscription_plan_code,
                subscription_plan_name,
                subscription_status,
                subscription_started_at,
                subscription_expires_at
            FROM Users
            WHERE id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()

    return dict(row) if row else None


def get_user_payment_history(user_id: int, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                amount,
                currency,
                status,
                transaction_type,
                plan_code,
                plan_name,
                plan_duration_days,
                image_history_id,
                razorpay_order_id,
                razorpay_payment_id,
                created_at,
                paid_at
            FROM Transactions
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()

    return [dict(row) for row in rows]


def delete_user_account(user_id: int, db_path: Path = DB_PATH) -> tuple[bool, str]:
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        cursor.execute("DELETE FROM ImageHistory WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM Transactions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))

        conn.commit()

        if cursor.rowcount == 0:
            return False, "User not found."

    return True, "Account deleted successfully."
