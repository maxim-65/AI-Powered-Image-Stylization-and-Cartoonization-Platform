from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 55) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    inv = cv2.bitwise_not(gray)
    blur_ks = 9 + (intensity // 20) * 2
    if blur_ks % 2 == 0:
        blur_ks += 1
    blur = cv2.GaussianBlur(inv, (blur_ks, blur_ks), 0)
    sketch = cv2.divide(gray, 255 - blur, scale=256)

    edges = cv2.Canny(gray, 60, 150)
    edges = cv2.dilate(edges, np.ones((2, 2), dtype=np.uint8), iterations=1)
    sketch[edges > 0] = 0

    output = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
    return restore_size(output, original_size, was_resized)
