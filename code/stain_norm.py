"""
stain_norm.py
-------------
Macenko stain normalisation for H&E images — pure numpy/scipy implementation.

Every input image is normalised to match a fixed reference image so that
colour variability across slides / scanners does not bias the segmentation.

Reference: Macenko et al., "A Method for Normalizing Histology Slides for
Quantitative Analysis", ISBI 2009.

No external stain-normalisation library needed — only numpy and scipy (already
in the base requirements). This avoids the OpenMP conflict between spams-bin
and PyTorch that causes deadlocks on macOS.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from skimage import io

from config import INPUT_DIR

# Fixed reference image — BRC/Image1.png was chosen because it has clean,
# well-balanced H&E staining with good tissue coverage.
_REFERENCE_PATH = INPUT_DIR / "BRC" / "Image1.png"

# Cached reference stain matrix and 99th-percentile concentrations.
_ref_stain_matrix: np.ndarray | None = None
_ref_max_conc: np.ndarray | None = None


def _rgb_to_od(rgb: np.ndarray) -> np.ndarray:
    """Convert RGB uint8 image to optical density (OD). Clip to avoid log(0)."""
    rgb = rgb.astype(np.float64)
    rgb = np.clip(rgb, 1, 255)
    return -np.log(rgb / 255.0)


def _od_to_rgb(od: np.ndarray) -> np.ndarray:
    """Convert optical density back to RGB uint8."""
    rgb = 255.0 * np.exp(-od)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _get_stain_matrix(od_flat: np.ndarray, *, angular_percentile: float = 99.0) -> np.ndarray:
    """
    Extract 2×3 stain matrix from OD values using SVD + angular projection
    (Macenko's method).

    Parameters
    ----------
    od_flat : (N, 3)  Optical-density vectors for tissue pixels.
    angular_percentile : percentile for the min/max angle projections
                         onto the SVD plane.

    Returns
    -------
    stain_matrix : (2, 3)  Row 0 = H stain vector, Row 1 = E stain vector.
    """
    # SVD of OD matrix → first 2 right singular vectors span the stain plane.
    _, _, Vt = np.linalg.svd(od_flat, full_matrices=False)
    plane = Vt[:2, :]  # (2, 3)

    # Project OD vectors onto the plane.
    proj = od_flat @ plane.T  # (N, 2)

    # Convert to angles and find percentile extremes.
    angles = np.arctan2(proj[:, 1], proj[:, 0])
    min_angle = np.percentile(angles, 100 - angular_percentile)
    max_angle = np.percentile(angles, angular_percentile)

    # Recover the two stain vectors from those extreme angles.
    v1 = np.array([np.cos(min_angle), np.sin(min_angle)]) @ plane
    v2 = np.array([np.cos(max_angle), np.sin(max_angle)]) @ plane

    # Ensure H (hematoxylin) is the first row — it's the one with the
    # larger first OD component (blue-purple absorbs more at λ ~red).
    if v1[0] < v2[0]:
        stain_matrix = np.vstack([v2, v1])
    else:
        stain_matrix = np.vstack([v1, v2])

    # Normalise each row to unit length.
    stain_matrix /= np.linalg.norm(stain_matrix, axis=1, keepdims=True)
    return stain_matrix


def _get_concentrations(od_flat: np.ndarray, stain_matrix: np.ndarray) -> np.ndarray:
    """Solve for stain concentrations: OD ≈ C × S  →  C = OD × pinv(S)^T.
    stain_matrix is (2,3), od_flat is (N,3). Result is (N,2)."""
    return od_flat @ np.linalg.pinv(stain_matrix)  # (N,3) @ (3,2) -> (N,2)


def _tissue_mask(rgb: np.ndarray, luminosity_threshold: float = 0.8) -> np.ndarray:
    """Boolean mask: True where there is tissue (not background white)."""
    luminosity = rgb.astype(np.float64).mean(axis=-1) / 255.0
    return luminosity < luminosity_threshold


def _fit(rgb: np.ndarray):
    """Compute stain matrix and 99th-pct concentrations for a reference image."""
    mask = _tissue_mask(rgb)
    od = _rgb_to_od(rgb)
    od_flat = od[mask]

    # Remove near-zero OD rows (background leaking through the mask).
    od_flat = od_flat[np.all(od_flat > 0.15, axis=1)]

    stain_matrix = _get_stain_matrix(od_flat)
    concentrations = _get_concentrations(od_flat, stain_matrix)
    max_conc = np.percentile(concentrations, 99, axis=0)
    return stain_matrix, max_conc


def _init_reference():
    """Load the reference image and cache its stain parameters."""
    global _ref_stain_matrix, _ref_max_conc
    if _ref_stain_matrix is not None:
        return

    ref = io.imread(_REFERENCE_PATH)
    if ref.ndim == 2:
        ref = np.stack([ref] * 3, axis=-1)
    if ref.shape[-1] == 4:
        ref = ref[..., :3]

    _ref_stain_matrix, _ref_max_conc = _fit(ref)


def macenko_normalize(rgb: np.ndarray) -> np.ndarray:
    """
    Normalise an H×W×3 uint8 RGB image to the reference stain profile.

    If normalisation fails for a particular image (e.g. near-blank tissue),
    the original image is returned unchanged with a warning.
    """
    _init_reference()

    try:
        h, w = rgb.shape[:2]
        mask = _tissue_mask(rgb)
        od = _rgb_to_od(rgb)
        od_flat = od[mask]

        # Need enough tissue pixels.
        od_tissue = od_flat[np.all(od_flat > 0.15, axis=1)]
        if len(od_tissue) < 100:
            return rgb

        src_stain = _get_stain_matrix(od_tissue)
        src_conc = _get_concentrations(od.reshape(-1, 3), src_stain)

        # Scale concentrations to match reference range.
        src_max = np.percentile(src_conc[mask.ravel()], 99, axis=0)
        src_max = np.where(src_max > 1e-6, src_max, 1.0)
        norm_conc = src_conc * (_ref_max_conc / src_max)

        # Reconstruct using the reference stain matrix.
        od_norm = norm_conc @ _ref_stain_matrix
        result = _od_to_rgb(od_norm).reshape(h, w, 3)
        return result

    except Exception as exc:
        import warnings
        warnings.warn(f"Macenko normalisation failed ({exc}); using original image.")
        return rgb
