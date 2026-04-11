from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 50) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    levels = max(2, min(16, 2 + intensity // 8))
    step = max(1, 256 // levels)
    output = ((resized // step) * step).astype(np.uint8)

    return restore_size(output, original_size, was_resized)
