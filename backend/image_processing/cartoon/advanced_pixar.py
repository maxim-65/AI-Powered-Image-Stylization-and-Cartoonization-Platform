from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import clamp_k, quantize_kmeans, resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 55, k: int = 12) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    blur_kernel = 5 if intensity >= 50 else 3
    denoised = cv2.medianBlur(resized, blur_kernel)
    smooth = cv2.bilateralFilter(denoised, 9, 90, 90)

    k = clamp_k(k)
    color = quantize_kmeans(smooth, k=k)

    gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
    block_size = 9 + (intensity // 10) * 2
    if block_size % 2 == 0:
        block_size += 1
    adaptive = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        max(3, block_size),
        5,
    )
    edges = cv2.bitwise_not(adaptive)
    edges = cv2.dilate(edges, np.ones((2, 2), dtype=np.uint8), iterations=1)

    output = color.copy()
    output[edges > 0] = (0, 0, 0)
    return restore_size(output, original_size, was_resized)
