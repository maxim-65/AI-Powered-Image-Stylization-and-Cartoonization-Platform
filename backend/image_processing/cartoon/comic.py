from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import quantize_kmeans, resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 60, k: int = 3) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    denoised = cv2.medianBlur(resized, 3)
    smooth = cv2.bilateralFilter(denoised, 7, 65, 65)

    # Aggressive comic color reduction to 2-4 bands.
    k = max(2, min(4, int(k)))
    quantized = quantize_kmeans(smooth, k=k, attempts=2, iterations=8)

    t1 = max(20, 100 - intensity)
    t2 = max(t1 + 50, 170 - intensity)
    edges = cv2.Canny(cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY), t1, t2)
    edges = cv2.dilate(edges, np.ones((3, 3), dtype=np.uint8), iterations=1)

    output = quantized.copy()
    output[edges > 0] = (0, 0, 0)
    return restore_size(output, original_size, was_resized)
