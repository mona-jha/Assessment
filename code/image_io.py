"""
image_io.py
-----------
Tiny helpers for loading images and writing the per-image artefacts every
segmentation method produces (overlays + instance masks).

Why this exists:
  Every method (classical, StarDist, Cellpose) needs to read PNGs and write
  results in the SAME directory layout. Centralising it here means the three
  methods stay short and only contain segmentation logic.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from skimage import io


def load_rgb(path: Path) -> np.ndarray:
    """Read an image and return it as an HxWx3 uint8 RGB array."""
    img = io.imread(path)
    if img.ndim == 2:
        # Grayscale -> stack to 3 channels so downstream colour code works.
        img = np.stack([img] * 3, axis=-1)
    if img.shape[-1] == 4:
        # Drop alpha channel if present.
        img = img[..., :3]
    return img


def save_mask(labels: np.ndarray, out_path: Path) -> None:
    """
    Persist an instance-label image as a 16-bit PNG.

    uint16 lets us store up to 65,535 distinct nuclei per image, which is
    well above what we ever see (max observed ~1000). Reviewers can re-load
    these with cv2.imread(..., cv2.IMREAD_UNCHANGED) for downstream analysis.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), labels.astype(np.uint16))


def save_overlay(overlay_rgb: np.ndarray, out_path: Path) -> None:
    """Save an HxWx3 uint8 overlay PNG (created by visualisation.make_overlay)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    io.imsave(out_path, overlay_rgb, check_contrast=False)


def gather_inputs(input_dir: Path, cohorts: list[str]) -> list[tuple[str, Path]]:
    """
    Walk INPUT_DIR/<cohort>/Image*.png and return [(cohort, path), ...]
    sorted by cohort then by the numeric suffix in the filename
    (so Image2 comes before Image10).
    """
    items: list[tuple[str, Path]] = []
    for cohort in cohorts:
        cohort_dir = input_dir / cohort
        if not cohort_dir.exists():
            raise FileNotFoundError(f"Missing cohort folder: {cohort_dir}")
        paths = sorted(
            cohort_dir.glob("Image*.png"),
            key=lambda p: int("".join(c for c in p.stem if c.isdigit())),
        )
        for p in paths:
            items.append((cohort, p))
    return items


def output_paths(method: str, cohort: str, image_stem: str, results_dir: Path
                 ) -> tuple[Path, Path]:
    """
    Return (overlay_path, mask_path) for a given (method, cohort, image).

    Filename convention is self-describing so individual files still make
    sense if copied out of the tree:
        results/<method>/overlays/<COHORT>_<Image>_overlay.png
        results/<method>/masks/<COHORT>_<Image>_mask.png
    """
    base = results_dir / method
    overlay_p = base / "overlays" / f"{cohort}_{image_stem}_overlay.png"
    mask_p = base / "masks" / f"{cohort}_{image_stem}_mask.png"
    return overlay_p, mask_p
