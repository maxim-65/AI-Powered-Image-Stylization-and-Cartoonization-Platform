from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "BMP"}
FORMAT_LABELS = {"JPEG": "JPG", "PNG": "PNG", "BMP": "BMP"}
FORMAT_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "BMP": ".bmp"}
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class UploadResult:
    file_path: str
    width: int
    height: int
    file_size_bytes: int
    file_size_display: str
    image_format: str


def _format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    if size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.2f} KB"
    return f"{size_in_bytes / (1024 * 1024):.2f} MB"


def upload_image(
    file_bytes: bytes,
    uploads_dir: Path = UPLOADS_DIR,
) -> UploadResult:
    if not file_bytes:
        raise ValueError("Upload failed: no file data received.")

    file_size_bytes = len(file_bytes)
    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        raise ValueError("Upload failed: file size exceeds 10MB. Please upload a file <= 10MB.")

    try:
        with Image.open(BytesIO(file_bytes)) as image:
            image_format = image.format or ""
            if image_format not in ALLOWED_FORMATS:
                raise ValueError("Upload failed: only JPG, PNG, and BMP formats are allowed.")
            width, height = image.size
    except UnidentifiedImageError as error:
        raise ValueError("Upload failed: invalid image file.") from error

    uploads_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid4().hex}{FORMAT_EXTENSIONS[image_format]}"
    file_path = uploads_dir / unique_name
    file_path.write_bytes(file_bytes)

    return UploadResult(
        file_path=str(file_path),
        width=width,
        height=height,
        file_size_bytes=file_size_bytes,
        file_size_display=_format_file_size(file_size_bytes),
        image_format=FORMAT_LABELS[image_format],
    )


def cleanup_temp_files_older_than_24h(
    directory: Path = UPLOADS_DIR,
    now: datetime | None = None,
) -> int:
    reference_time = now or datetime.now(timezone.utc)
    cutoff = reference_time - timedelta(hours=24)
    deleted_count = 0

    if not directory.exists():
        return deleted_count

    for file_path in directory.glob("**/*"):
        if not file_path.is_file():
            continue

        modified_at = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        if modified_at < cutoff:
            file_path.unlink(missing_ok=True)
            deleted_count += 1

    return deleted_count
