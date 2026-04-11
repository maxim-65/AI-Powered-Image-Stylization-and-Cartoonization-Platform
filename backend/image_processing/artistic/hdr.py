from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply_detail_enhance(image: np.ndarray, intensity: int = 50) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    sigma_s = max(10, min(200, 40 + intensity))
    sigma_r = max(0.1, min(0.9, 0.15 + intensity / 200))
    output = cv2.detailEnhance(resized, sigma_s=float(sigma_s), sigma_r=float(sigma_r))
    return restore_size(output, original_size, was_resized)


def apply_glow(image: np.ndarray, intensity: int = 50) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    blur = cv2.GaussianBlur(resized, (0, 0), sigmaX=max(2, intensity // 8))
    output = cv2.addWeighted(resized, 1.0, blur, min(0.8, 0.2 + intensity / 200), 0)
    return restore_size(output, original_size, was_resized)
