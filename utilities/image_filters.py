from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def median_blur(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    if kernel_size < 3 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be an odd integer >= 3.")
    return cv2.medianBlur(image, kernel_size)


def canny_edge_detection(
    image: np.ndarray,
    threshold1: int = 100,
    threshold2: int = 200,
) -> np.ndarray:
    gray_image = image
    if len(image.shape) == 3:
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(gray_image, threshold1, threshold2)


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
    criteria_iterations: int = 20,
    attempts: int = 10,
) -> np.ndarray:
    if not 8 <= k <= 16:
        raise ValueError("k must be between 8 and 16.")

    pixel_values = image.reshape((-1, 3))
    pixel_values = np.float32(pixel_values)

    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        criteria_iterations,
        0.2,
    )

    _, labels, centers = cv2.kmeans(
        pixel_values,
        k,
        None,
        criteria,
        attempts,
        cv2.KMEANS_RANDOM_CENTERS,
    )

    centers = np.uint8(centers)
    quantized = centers[labels.flatten()]
    return quantized.reshape(image.shape)


def apply_classic_cartoon(
    image: np.ndarray,
    k: int = 8,
    canny_threshold1: int = 100,
    canny_threshold2: int = 200,
    line_thickness: int = 2,
) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("image must be a valid non-empty numpy array.")
    if not 8 <= k <= 16:
        raise ValueError("k must be between 8 and 16.")
    if line_thickness < 1:
        raise ValueError("line_thickness must be >= 1.")

    base_image = image
    if len(base_image.shape) == 2:
        base_image = cv2.cvtColor(base_image, cv2.COLOR_GRAY2BGR)

    denoised = median_blur(base_image, kernel_size=5)
    smooth_once = bilateral_filter(denoised, diameter=9, sigma_color=75, sigma_space=75)
    smooth_twice = bilateral_filter(smooth_once, diameter=9, sigma_color=75, sigma_space=75)

    quantized = color_quantization(
        smooth_twice,
        k=k,
        criteria_iterations=10,
        attempts=3,
    )

    edges = canny_edge_detection(denoised, threshold1=canny_threshold1, threshold2=canny_threshold2)
    if line_thickness > 1:
        kernel = np.ones((line_thickness, line_thickness), dtype=np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

    cartoon = quantized.copy()
    cartoon[edges > 0] = (0, 0, 0)
    return cartoon


def apply_pencil_sketch(
    image: np.ndarray,
    blur_kernel_size: int = 21,
    blur_sigma: float = 0,
) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("image must be a valid non-empty numpy array.")
    if blur_kernel_size < 3 or blur_kernel_size % 2 == 0:
        raise ValueError("blur_kernel_size must be an odd integer >= 3.")

    gray = image
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    inverted = cv2.bitwise_not(gray)
    blurred = cv2.GaussianBlur(inverted, (blur_kernel_size, blur_kernel_size), blur_sigma)
    sketch = cv2.divide(gray, 255 - blurred, scale=256)
    return sketch


def apply_pencil_color(
    image: np.ndarray,
    saturation_scale: float = 0.45,
    blur_kernel_size: int = 21,
) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("image must be a valid non-empty numpy array.")
    if not 0 <= saturation_scale <= 1:
        raise ValueError("saturation_scale must be between 0 and 1.")

    base_image = image
    if len(base_image.shape) == 2:
        base_image = cv2.cvtColor(base_image, cv2.COLOR_GRAY2BGR)

    sketch = apply_pencil_sketch(base_image, blur_kernel_size=blur_kernel_size)
    sketch_bgr = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

    hsv = cv2.cvtColor(base_image, cv2.COLOR_BGR2HSV)
    hsv = hsv.astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_scale, 0, 255)
    desaturated = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    colored_sketch = cv2.multiply(
        desaturated.astype(np.float32) / 255.0,
        sketch_bgr.astype(np.float32) / 255.0,
    )
    return (colored_sketch * 255).astype(np.uint8)


def generate_comparison_image(
    original_rgb: np.ndarray,
    processed_rgb: np.ndarray,
    label_height: int = 40,
) -> bytes:
    if original_rgb is None or processed_rgb is None:
        raise ValueError("Both original_rgb and processed_rgb are required.")

    original_image = Image.fromarray(original_rgb)
    processed_image = Image.fromarray(processed_rgb)

    if original_image.size != processed_image.size:
        processed_image = processed_image.resize(original_image.size, Image.Resampling.LANCZOS)

    width, height = original_image.size
    canvas = Image.new("RGB", (width * 2, height + label_height), color=(255, 255, 255))

    canvas.paste(original_image, (0, label_height))
    canvas.paste(processed_image, (width, label_height))

    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    original_text = "Original"
    processed_text = "Processed"

    original_text_bbox = draw.textbbox((0, 0), original_text, font=font)
    processed_text_bbox = draw.textbbox((0, 0), processed_text, font=font)

    original_text_width = original_text_bbox[2] - original_text_bbox[0]
    original_text_height = original_text_bbox[3] - original_text_bbox[1]
    processed_text_width = processed_text_bbox[2] - processed_text_bbox[0]
    processed_text_height = processed_text_bbox[3] - processed_text_bbox[1]

    original_text_x = (width - original_text_width) // 2
    original_text_y = (label_height - original_text_height) // 2
    processed_text_x = width + (width - processed_text_width) // 2
    processed_text_y = (label_height - processed_text_height) // 2

    draw.text((original_text_x, original_text_y), original_text, fill=(0, 0, 0), font=font)
    draw.text((processed_text_x, processed_text_y), processed_text, fill=(0, 0, 0), font=font)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()
