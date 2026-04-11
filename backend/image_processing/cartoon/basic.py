from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import clamp_k, quantize_kmeans, resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 50, k: int = 10) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    blur_kernel = 5 if intensity >= 50 else 3
    denoised = cv2.medianBlur(resized, blur_kernel)
    smooth = cv2.bilateralFilter(denoised, 9, 75, 75)

    k = clamp_k(k)
    quantized = quantize_kmeans(smooth, k=k)

    edge_t1 = max(30, 130 - intensity)
    edge_t2 = max(edge_t1 + 40, 200 - intensity)
    edges = cv2.Canny(denoised, edge_t1, edge_t2)
    edges = cv2.dilate(edges, np.ones((2, 2), dtype=np.uint8), iterations=1)

    output = quantized.copy()
    output[edges > 0] = (0, 0, 0)
    return restore_size(output, original_size, was_resized)
