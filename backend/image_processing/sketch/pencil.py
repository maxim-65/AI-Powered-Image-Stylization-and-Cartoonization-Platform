from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 50) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    sigma_s = max(20, min(200, 40 + intensity))
    sigma_r = max(0.05, min(0.2, 0.06 + intensity / 1000))
    gray, _ = cv2.pencilSketch(resized, sigma_s=float(sigma_s), sigma_r=float(sigma_r), shade_factor=0.05)
    output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return restore_size(output, original_size, was_resized)


def apply_colored(image: np.ndarray, intensity: int = 50) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    sigma_s = max(20, min(200, 40 + intensity))
    sigma_r = max(0.05, min(0.2, 0.06 + intensity / 1000))
    _, color = cv2.pencilSketch(resized, sigma_s=float(sigma_s), sigma_r=float(sigma_r), shade_factor=0.06)
    return restore_size(color, original_size, was_resized)
