import re
import sqlite3
import sys
import tempfile
import unittest
import shutil
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.auth import login_user, register_user
from backend.dashboard import save_image_history, save_uploaded_file
from backend.payment import create_payment_order, verify_payment_and_update_transaction
from database.db_manager import init_db
from utilities.cartoon_engine import apply_classic_cartoon


class FakeOrderAPI:
    def create(self, data):
        return {
            "id": "order_test_001",
            "amount": data["amount"],
            "currency": data["currency"],
            "status": "created",
        }


class FakeUtilityAPI:
    def verify_payment_signature(self, payload):
        if payload["razorpay_signature"] != "valid_signature":
            raise ValueError("Invalid signature")


class FakeRazorpayClient:
    def __init__(self):
        self.order = FakeOrderAPI()
        self.utility = FakeUtilityAPI()


class TestAIStylizationPlatform(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_app.db"
        self.uploads_dir = self.temp_dir / "uploads"
        self.images_dir = self.temp_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        init_db(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_register_and_login_credentials(self):
        success, message = register_user(
            username="qa_user",
            email="qa.user@example.com",
            password="Strong@123",
            db_path=self.db_path,
        )
        self.assertTrue(success, message)

        login_success, login_result = login_user(
            email="qa.user@example.com",
            password="Strong@123",
            db_path=self.db_path,
        )
        self.assertTrue(login_success)
        self.assertIsInstance(login_result, dict)

        wrong_success, wrong_result = login_user(
            email="qa.user@example.com",
            password="Wrong@123",
            db_path=self.db_path,
        )
        self.assertFalse(wrong_success)
        self.assertIn("Invalid email or password", str(wrong_result))

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT password_hash FROM Users WHERE email = ?",
                ("qa.user@example.com",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertNotEqual(row[0], "Strong@123")

    def test_upload_generates_unique_uuid_filename(self):
        sample_bytes = b"sample-image-bytes"

        path1 = save_uploaded_file(sample_bytes, "input.jpg", uploads_dir=self.uploads_dir)
        path2 = save_uploaded_file(sample_bytes, "input.jpg", uploads_dir=self.uploads_dir)

        self.assertNotEqual(path1, path2)
        self.assertTrue(Path(path1).exists())
        self.assertTrue(Path(path2).exists())

        uuid_name_pattern = re.compile(r"^[0-9a-f]{32}\.jpg$")
        self.assertRegex(Path(path1).name, uuid_name_pattern)
        self.assertRegex(Path(path2).name, uuid_name_pattern)

    def test_cartoon_pipeline_output_exists_and_not_null(self):
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        cv2.rectangle(image, (30, 30), (270, 170), (10, 180, 230), -1)

        cartoon = apply_classic_cartoon(image, k=8)
        self.assertIsNotNone(cartoon)
        self.assertGreater(cartoon.size, 0)

        output_path = self.images_dir / "cartoon_output.png"
        write_ok = cv2.imwrite(str(output_path), cartoon)
        self.assertTrue(write_ok)
        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)

    @patch("backend.payment._get_razorpay_client", return_value=FakeRazorpayClient())
    def test_mocked_razorpay_updates_transactions_and_imagehistory(self, _mock_client):
        success, _ = register_user(
            username="pay_user",
            email="pay.user@example.com",
            password="Strong@123",
            db_path=self.db_path,
        )
        self.assertTrue(success)

        with sqlite3.connect(self.db_path) as conn:
            user_row = conn.execute(
                "SELECT id FROM Users WHERE email = ?",
                ("pay.user@example.com",),
            ).fetchone()
        user_id = user_row[0]

        original_path = str(self.images_dir / "orig.png")
        processed_path = str(self.images_dir / "proc.png")
        cv2.imwrite(original_path, np.zeros((100, 100, 3), dtype=np.uint8))
        cv2.imwrite(processed_path, np.zeros((100, 100, 3), dtype=np.uint8))

        _, image_history_id = save_image_history(
            user_id=user_id,
            original_path=original_path,
            processed_path=processed_path,
            style="classic",
            db_path=self.db_path,
        )

        order_success, order_result = create_payment_order(
            user_id=user_id,
            amount=49.0,
            image_history_id=int(image_history_id),
            db_path=self.db_path,
        )
        self.assertTrue(order_success, str(order_result))

        verify_success, verify_message = verify_payment_and_update_transaction(
            transaction_id=order_result["transaction_id"],
            razorpay_order_id=order_result["order"]["id"],
            razorpay_payment_id="pay_test_001",
            razorpay_signature="valid_signature",
            image_history_id=int(image_history_id),
            db_path=self.db_path,
        )
        self.assertTrue(verify_success, verify_message)

        with sqlite3.connect(self.db_path) as conn:
            txn_row = conn.execute(
                "SELECT status, image_history_id FROM Transactions WHERE id = ?",
                (order_result["transaction_id"],),
            ).fetchone()
            img_row = conn.execute(
                "SELECT is_paid FROM ImageHistory WHERE id = ?",
                (int(image_history_id),),
            ).fetchone()

        self.assertEqual(txn_row[0], "success")
        self.assertEqual(txn_row[1], int(image_history_id))
        self.assertEqual(img_row[0], 1)

    def test_ui_has_comparison_slider_and_download_gate(self):
        app_source = (PROJECT_ROOT / "frontend" / "app.py").read_text(encoding="utf-8")

        self.assertIn("IMAGE_COMPARISON_AVAILABLE", app_source)
        self.assertIn("image_comparison(", app_source)
        self.assertIn('if int(item.get("is_paid", 0)) == 1 and item.get("payment_status") == "success"', app_source)
        self.assertIn('st.download_button(', app_source)
        self.assertIn('st.button("Unlock"', app_source)


if __name__ == "__main__":
    unittest.main()
