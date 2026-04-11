from __future__ import annotations

import cv2
import numpy as np

from backend.image_processing.common import resize_for_speed, restore_size


def apply(image: np.ndarray, intensity: int = 50) -> np.ndarray:
    resized, original_size, was_resized = resize_for_speed(image)

    size = max(3, 3 + intensity // 20)
    dyn_ratio = max(8, 10 + intensity // 8)

    if hasattr(cv2, "xphoto") and hasattr(cv2.xphoto, "oilPainting"):
        output = cv2.xphoto.oilPainting(resized, size=size, dynRatio=dyn_ratio)
    else:
        # Fallback when opencv-contrib is unavailable.
        output = cv2.bilateralFilter(resized, 9, 90, 90)

    return restore_size(output, original_size, was_resized)
