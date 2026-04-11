import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "app.db"


def init_db(db_path: Path = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                account_locked INTEGER NOT NULL DEFAULT 0,
                lock_until TIMESTAMP,
                last_login TIMESTAMP,
                subscription_plan_code TEXT,
                subscription_plan_name TEXT,
                subscription_status TEXT NOT NULL DEFAULT 'inactive',
                subscription_started_at TIMESTAMP,
                subscription_expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',
                status TEXT NOT NULL,
                transaction_type TEXT NOT NULL DEFAULT 'image_unlock',
                plan_code TEXT,
                plan_name TEXT,
                plan_duration_days INTEGER,
                image_history_id INTEGER,
                razorpay_order_id TEXT,
                razorpay_payment_id TEXT,
                razorpay_signature TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (image_history_id) REFERENCES ImageHistory(id)
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ImageHistory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_path TEXT NOT NULL,
                processed_path TEXT NOT NULL,
                style TEXT NOT NULL,
                is_paid INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES Users(id)
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS UserSessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id)
            );
            """
        )

        cursor.execute("PRAGMA table_info(ImageHistory);")
        image_history_columns = {row[1] for row in cursor.fetchall()}
        if "is_paid" not in image_history_columns:
            cursor.execute("ALTER TABLE ImageHistory ADD COLUMN is_paid INTEGER NOT NULL DEFAULT 0;")

        cursor.execute("PRAGMA table_info(Users);")
        user_columns = {row[1] for row in cursor.fetchall()}
        if "failed_login_attempts" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0;")
        if "account_locked" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN account_locked INTEGER NOT NULL DEFAULT 0;")
        if "lock_until" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN lock_until TIMESTAMP;")
        if "last_login" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN last_login TIMESTAMP;")
        if "subscription_plan_code" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN subscription_plan_code TEXT;")
        if "subscription_plan_name" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN subscription_plan_name TEXT;")
        if "subscription_status" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN subscription_status TEXT NOT NULL DEFAULT 'inactive';")
        if "subscription_started_at" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN subscription_started_at TIMESTAMP;")
        if "subscription_expires_at" not in user_columns:
            cursor.execute("ALTER TABLE Users ADD COLUMN subscription_expires_at TIMESTAMP;")

        cursor.execute("PRAGMA table_info(Transactions);")
        transaction_columns = {row[1] for row in cursor.fetchall()}
        if "image_history_id" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN image_history_id INTEGER;")
        if "currency" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN currency TEXT NOT NULL DEFAULT 'INR';")
        if "transaction_type" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN transaction_type TEXT NOT NULL DEFAULT 'image_unlock';")
        if "plan_code" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN plan_code TEXT;")
        if "plan_name" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN plan_name TEXT;")
        if "plan_duration_days" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN plan_duration_days INTEGER;")
        if "razorpay_order_id" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN razorpay_order_id TEXT;")
        if "razorpay_payment_id" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN razorpay_payment_id TEXT;")
        if "razorpay_signature" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN razorpay_signature TEXT;")
        if "created_at" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        if "paid_at" not in transaction_columns:
            cursor.execute("ALTER TABLE Transactions ADD COLUMN paid_at TIMESTAMP;")

        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")
