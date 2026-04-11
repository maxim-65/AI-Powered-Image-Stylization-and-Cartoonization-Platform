from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 50) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    sigma_s = max(20, min(200, 60 + intensity))
    sigma_r = max(0.1, min(0.9, 0.2 + intensity / 150))
    output = cv2.stylization(resized, sigma_s=float(sigma_s), sigma_r=float(sigma_r))
    return restore_size(output, original_size, was_resized)
