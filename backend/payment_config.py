from __future__ import annotations

import os


def get_razorpay_credentials() -> tuple[str, str]:
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

    if not key_id or not key_secret:
        raise RuntimeError(
            "Razorpay credentials are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in your environment."
        )

    return key_id, key_secret
