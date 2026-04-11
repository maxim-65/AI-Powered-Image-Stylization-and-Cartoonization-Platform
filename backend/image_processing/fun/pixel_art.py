from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 55) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    h, w = resized.shape[:2]
    factor = max(4, min(30, 4 + intensity // 4))
    small = cv2.resize(resized, (max(1, w // factor), max(1, h // factor)), interpolation=cv2.INTER_LINEAR)
    output = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    return restore_size(output, original_size, was_resized)
