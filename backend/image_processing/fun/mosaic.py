from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 55) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    h, w = resized.shape[:2]
    block = max(6, min(60, 6 + intensity // 2))
    small = cv2.resize(resized, (max(1, w // block), max(1, h // block)), interpolation=cv2.INTER_AREA)
    output = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    return restore_size(output, original_size, was_resized)
