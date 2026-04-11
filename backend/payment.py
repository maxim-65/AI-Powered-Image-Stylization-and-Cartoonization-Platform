import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import razorpay

from database.db_manager import DB_PATH, init_db
from backend.payment_config import get_razorpay_credentials


SUBSCRIPTION_PLANS: dict[str, dict[str, Any]] = {
    "basic_monthly": {
        "name": "Basic Monthly",
        "amount": 99.0,
        "duration_days": 30,
    },
    "pro_quarterly": {
        "name": "Pro Quarterly",
        "amount": 249.0,
        "duration_days": 90,
    },
    "elite_yearly": {
        "name": "Elite Yearly",
        "amount": 799.0,
        "duration_days": 365,
    },
}


def get_subscription_plans() -> dict[str, dict[str, Any]]:
    return SUBSCRIPTION_PLANS.copy()


def _get_razorpay_client() -> razorpay.Client:
    key_id, key_secret = get_razorpay_credentials()
    return razorpay.Client(auth=(key_id, key_secret))


def create_payment_order(
    user_id: int,
    amount: float,
    image_history_id: int | None = None,
    currency: str = "INR",
    receipt: str | None = None,
    notes: dict[str, Any] | None = None,
    transaction_type: str = "image_unlock",
    plan_code: str | None = None,
    db_path: Path = DB_PATH,
) -> tuple[bool, dict[str, Any] | str]:
    plan_name = None
    plan_duration_days = None

    if transaction_type == "subscription":
        if not plan_code:
            return False, "Plan code is required for subscription payments."
        plan = SUBSCRIPTION_PLANS.get(plan_code)
        if not plan:
            return False, "Invalid subscription plan selected."
        amount = float(plan["amount"])
        plan_name = str(plan["name"])
        plan_duration_days = int(plan["duration_days"])

    if amount <= 0:
        return False, "Amount must be greater than 0."

    init_db(db_path)

    try:
        client = _get_razorpay_client()
    except (ValueError, RuntimeError) as error:
        return False, str(error)

    amount_paise = int(round(amount * 100))
    order_payload: dict[str, Any] = {
        "amount": amount_paise,
        "currency": currency,
        "payment_capture": 1,
    }

    if receipt:
        order_payload["receipt"] = receipt
    if notes:
        order_payload["notes"] = notes

    try:
        order = client.order.create(data=order_payload)
    except Exception as error:
        return False, f"Failed to create Razorpay order: {error}"

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Transactions (
                user_id,
                amount,
                currency,
                status,
                transaction_type,
                plan_code,
                plan_name,
                plan_duration_days,
                image_history_id,
                razorpay_order_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                amount,
                currency,
                "created",
                transaction_type,
                plan_code,
                plan_name,
                plan_duration_days,
                image_history_id,
                order.get("id"),
            ),
        )
        transaction_id = cursor.lastrowid
        conn.commit()

    return True, {
        "transaction_id": transaction_id,
        "order": order,
    }


def verify_payment_and_update_transaction(
    transaction_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    image_history_id: int | None = None,
    db_path: Path = DB_PATH,
) -> tuple[bool, str]:
    init_db(db_path)

    try:
        client = _get_razorpay_client()
    except (ValueError, RuntimeError) as error:
        return False, str(error)

    verification_payload = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    }

    status = "failed"

    try:
        client.utility.verify_payment_signature(verification_payload)
        status = "success"
    except Exception:
        status = "failed"

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, image_history_id, transaction_type, plan_code, plan_name, plan_duration_days
            FROM Transactions
            WHERE id = ?
            """,
            (transaction_id,),
        )
        transaction_row = cursor.fetchone()
        if not transaction_row:
            return False, "Transaction not found."

        user_id = int(transaction_row[0])
        linked_image_history_id = transaction_row[1]
        transaction_type = transaction_row[2]
        plan_code = transaction_row[3]
        plan_name = transaction_row[4]
        plan_duration_days = transaction_row[5]
        target_image_history_id = image_history_id if image_history_id is not None else linked_image_history_id

        cursor.execute(
            """
            UPDATE Transactions
            SET
                status = ?,
                razorpay_order_id = ?,
                razorpay_payment_id = ?,
                razorpay_signature = ?,
                paid_at = CASE WHEN ? = 'success' THEN CURRENT_TIMESTAMP ELSE paid_at END
            WHERE id = ?
            """,
            (status, razorpay_order_id, razorpay_payment_id, razorpay_signature, status, transaction_id),
        )

        if status == "success" and target_image_history_id is not None:
            cursor.execute(
                """
                UPDATE ImageHistory
                SET is_paid = 1
                WHERE id = ?
                """,
                (target_image_history_id,),
            )

        if status == "success" and transaction_type == "subscription":
            now = datetime.utcnow()
            duration_days = int(plan_duration_days or 30)
            expires_at = now + timedelta(days=duration_days)
            cursor.execute(
                """
                UPDATE Users
                SET
                    subscription_plan_code = ?,
                    subscription_plan_name = ?,
                    subscription_status = 'active',
                    subscription_started_at = ?,
                    subscription_expires_at = ?
                WHERE id = ?
                """,
                (
                    plan_code,
                    plan_name,
                    now.isoformat(timespec="seconds"),
                    expires_at.isoformat(timespec="seconds"),
                    user_id,
                ),
            )
        conn.commit()

    if status == "success":
        return True, "Payment verified and transaction updated successfully."

    return False, "Payment signature verification failed. Transaction marked as failed."
