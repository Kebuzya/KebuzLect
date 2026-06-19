from __future__ import annotations

from pathlib import Path

import imagehash
import numpy as np
from PIL import Image

from app.models import Photo


def is_blurry(image_path: Path, threshold: float) -> bool:
    with Image.open(image_path) as image:
        pixels = np.asarray(image.convert("L"), dtype=np.float64)
    return _laplacian_variance(pixels) < threshold


def find_duplicates(photos: list[Photo], threshold: int) -> list[tuple[Photo, Photo]]:
    fingerprints: list[tuple[Photo, imagehash.ImageHash]] = []
    for photo in photos:
        if photo.local_thumb is None:
            continue
        try:
            with Image.open(photo.local_thumb) as image:
                fingerprints.append((photo, imagehash.phash(image)))
        except (OSError, ValueError):
            continue

    duplicates: list[tuple[Photo, Photo]] = []
    for left_index in range(len(fingerprints)):
        for right_index in range(left_index + 1, len(fingerprints)):
            left_photo, left_hash = fingerprints[left_index]
            right_photo, right_hash = fingerprints[right_index]
            if left_hash - right_hash <= threshold:
                duplicates.append((left_photo, right_photo))
    return duplicates


def _laplacian_variance(pixels: np.ndarray) -> float:
    if pixels.ndim != 2 or pixels.shape[0] < 3 or pixels.shape[1] < 3:
        return 0.0
    center = pixels[1:-1, 1:-1]
    up = pixels[:-2, 1:-1]
    down = pixels[2:, 1:-1]
    left = pixels[1:-1, :-2]
    right = pixels[1:-1, 2:]
    laplacian = up + down + left + right - 4.0 * center
    return float(laplacian.var())
