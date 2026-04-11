from __future__ import annotations

import time

import cv2
import numpy as np

from utilities.image_filters import (
    apply_pencil_color,
    apply_pencil_sketch,
    canny_edge_detection,
    generate_comparison_image,
)


MAX_PROCESS_PIXELS = 1920 * 1080


def _resize_for_performance(image: np.ndarray) -> tuple[np.ndarray, tuple[int, int], bool]:
    original_height, original_width = image.shape[:2]
    original_size = (original_width, original_height)
    total_pixels = original_width * original_height

    if total_pixels <= MAX_PROCESS_PIXELS:
        return image, original_size, False

    scale = (MAX_PROCESS_PIXELS / total_pixels) ** 0.5
    new_width = max(1, int(original_width * scale))
    new_height = max(1, int(original_height * scale))

    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    return resized, original_size, True


def median_blur(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    if kernel_size not in (3, 5):
        raise ValueError("kernel_size must be 3 or 5.")
    return cv2.medianBlur(image, kernel_size)


def bilateral_filter(
    image: np.ndarray,
    diameter: int = 9,
    sigma_color: float = 75,
    sigma_space: float = 75,
) -> np.ndarray:
    if diameter <= 0:
        raise ValueError("diameter must be greater than 0.")
    return cv2.bilateralFilter(image, diameter, sigma_color, sigma_space)


def color_quantization(
    image: np.ndarray,
    k: int = 8,
    criteria_iterations: int = 10,
    attempts: int = 3,
) -> np.ndarray:
    if not 8 <= k <= 16:
        raise ValueError("k must be between 8 and 16.")

    pixels = np.float32(image.reshape((-1, 3)))
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        criteria_iterations,
        0.2,
    )

    _, labels, centers = cv2.kmeans(
        pixels,
        k,
        None,
        criteria,
        attempts,
        cv2.KMEANS_PP_CENTERS,
    )

    centers = np.uint8(centers)
    quantized = centers[labels.flatten()]
    return quantized.reshape(image.shape)


def apply_classic_cartoon(
    image: np.ndarray,
    k: int = 8,
    median_kernel_size: int = 5,
    canny_threshold1: int = 70,
    canny_threshold2: int = 170,
    line_thickness: int = 2,
) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("image must be a valid non-empty numpy array.")
    if line_thickness < 1:
        raise ValueError("line_thickness must be >= 1.")

    base_image = image
    if len(base_image.shape) == 2:
        base_image = cv2.cvtColor(base_image, cv2.COLOR_GRAY2BGR)

    resized_image, original_size, was_resized = _resize_for_performance(base_image)

    denoised = median_blur(resized_image, kernel_size=median_kernel_size)
    smoothed = bilateral_filter(denoised, diameter=9, sigma_color=75, sigma_space=75)
    quantized = color_quantization(smoothed, k=k)

    edges = canny_edge_detection(denoised, threshold1=canny_threshold1, threshold2=canny_threshold2)
    if line_thickness > 1:
        kernel = np.ones((line_thickness, line_thickness), dtype=np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

    cartoon = quantized.copy()
    cartoon[edges > 0] = (0, 0, 0)

    if was_resized:
        cartoon = cv2.resize(cartoon, original_size, interpolation=cv2.INTER_LINEAR)

    return cartoon


def apply_classic_cartoon_timed(
    image: np.ndarray,
    k: int = 8,
    median_kernel_size: int = 5,
    canny_threshold1: int = 70,
    canny_threshold2: int = 170,
    line_thickness: int = 2,
) -> tuple[np.ndarray, float]:
    start_time = time.perf_counter()
    result = apply_classic_cartoon(
        image=image,
        k=k,
        median_kernel_size=median_kernel_size,
        canny_threshold1=canny_threshold1,
        canny_threshold2=canny_threshold2,
        line_thickness=line_thickness,
    )
    elapsed_seconds = time.perf_counter() - start_time
    return result, elapsed_seconds


__all__ = [
    "apply_classic_cartoon",
    "apply_classic_cartoon_timed",
    "apply_pencil_color",
    "apply_pencil_sketch",
    "bilateral_filter",
    "canny_edge_detection",
    "color_quantization",
    "generate_comparison_image",
    "median_blur",
]
