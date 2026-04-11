from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 50) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    sepia = np.array(
        [
            [0.272, 0.534, 0.131],
            [0.349, 0.686, 0.168],
            [0.393, 0.769, 0.189],
        ]
    )
    sepia_img = cv2.transform(resized, sepia)
    sepia_img = np.clip(sepia_img, 0, 255).astype(np.uint8)

    alpha = min(1.0, max(0.1, intensity / 100))
    output = cv2.addWeighted(resized, 1 - alpha, sepia_img, alpha, 0)
    return restore_size(output, original_size, was_resized)
