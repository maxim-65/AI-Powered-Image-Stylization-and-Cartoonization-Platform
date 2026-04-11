from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 60) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1.4 + intensity / 120), 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1.15 + intensity / 220), 0, 255)
    vibrant = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    output = cv2.convertScaleAbs(vibrant, alpha=1.1, beta=10)
    return restore_size(output, original_size, was_resized)
