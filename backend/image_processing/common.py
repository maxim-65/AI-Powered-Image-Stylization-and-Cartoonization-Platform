from __future__ import annotations

import cv2
import numpy as np

MAX_PIXELS_1080P = 1920 * 1080


def ensure_bgr(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("image must be a valid non-empty numpy array")
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image


def resize_for_speed(image: np.ndarray, max_pixels: int = MAX_PIXELS_1080P) -> tuple[np.ndarray, tuple[int, int], bool]:
    image = ensure_bgr(image)
    height, width = image.shape[:2]
    original_size = (width, height)
    pixels = width * height
    if pixels <= max_pixels:
        return image, original_size, False

    scale = (max_pixels / pixels) ** 0.5
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    return resized, original_size, True


def restore_size(image: np.ndarray, original_size: tuple[int, int], was_resized: bool) -> np.ndarray:
    if not was_resized:
        return image
    return cv2.resize(image, original_size, interpolation=cv2.INTER_LINEAR)


def clamp_k(k: int, minimum: int = 8, maximum: int = 16) -> int:
    return max(minimum, min(maximum, int(k)))


def quantize_kmeans(image: np.ndarray, k: int, attempts: int = 3, iterations: int = 10) -> np.ndarray:
    pixels = image.reshape((-1, 3)).astype("float32")
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, iterations, 0.2)
    _, labels, centers = cv2.kmeans(
        pixels,
        int(k),
        None,
        criteria,
        attempts,
        cv2.KMEANS_PP_CENTERS,
    )
    centers = centers.astype("uint8")
    return centers[labels.flatten()].reshape(image.shape)
