"""Dependency-light image operations used by both face and ANPR pipelines."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from ai.contracts import BoundingBox


def clip_bbox(box: BoundingBox, width: int, height: int) -> BoundingBox | None:
    x1 = min(max(int(box.x1), 0), width)
    y1 = min(max(int(box.y1), 0), height)
    x2 = min(max(int(box.x2), 0), width)
    y2 = min(max(int(box.y2), 0), height)
    if x2 <= x1 or y2 <= y1:
        return None
    return BoundingBox(x1, y1, x2, y2)


def crop_image(frame: np.ndarray, box: BoundingBox) -> tuple[np.ndarray, BoundingBox] | tuple[None, None]:
    height, width = frame.shape[:2]
    clipped = clip_bbox(box, width, height)
    if clipped is None:
        return None, None
    crop = frame[int(clipped.y1) : int(clipped.y2), int(clipped.x1) : int(clipped.x2)]
    if crop.size == 0:
        return None, None
    return crop, clipped


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image.astype(np.float32)
    if image.shape[2] < 3:
        return image[..., 0].astype(np.float32)
    # OpenCV frames are BGR. Luminance weights are applied in BGR order.
    b, g, r = image[..., 0], image[..., 1], image[..., 2]
    return (0.114 * b + 0.587 * g + 0.299 * r).astype(np.float32)


def variance_of_laplacian(image: np.ndarray) -> float:
    gray = to_gray(image)
    if min(gray.shape[:2]) < 3:
        return 0.0
    center = gray[1:-1, 1:-1]
    laplacian = (
        gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
        - 4.0 * center
    )
    return float(np.var(laplacian))


def image_statistics(image: np.ndarray) -> tuple[float, float, float]:
    gray = to_gray(image)
    brightness = float(np.mean(gray)) if gray.size else 0.0
    clipped = float(np.mean((gray <= 5) | (gray >= 250))) if gray.size else 1.0
    sharpness = variance_of_laplacian(image)
    return brightness, sharpness, clipped


def image_sha256(image: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(str(image.shape).encode("ascii"))
    digest.update(str(image.dtype).encode("ascii"))
    digest.update(np.ascontiguousarray(image).tobytes())
    return digest.hexdigest()


def normalize_vector(vector: np.ndarray | list[float] | tuple[float, ...]) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(array))
    if norm <= 1e-12:
        raise ValueError("Cannot normalize a zero-length embedding")
    return array / norm


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(normalize_vector(left), normalize_vector(right)))


def load_bgr_image(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"))
    return rgb[..., ::-1].copy()


def save_bgr_image(path: str | Path, image: np.ndarray) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if image.ndim == 3 and image.shape[2] >= 3:
        output = image[..., :3][..., ::-1]
    else:
        output = image
    Image.fromarray(np.asarray(output, dtype=np.uint8)).save(destination)
    return destination
