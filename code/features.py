"""
features.py
-----------
Per-image morphometric summary computed from an instance-label mask.

The same function is called for every method (classical / StarDist / Cellpose)
so the resulting CSV columns are identical and directly comparable.
"""

from __future__ import annotations

import numpy as np
from skimage import measure


def extract_features(labels: np.ndarray, image_shape: tuple) -> dict:
    """
    Aggregate per-nucleus regionprops into a flat dict of image-level stats.

    Returned keys:
        nucleus_count          : number of detected nuclei
        mean_area_px           : mean nucleus area (pixels^2)
        median_area_px         : median nucleus area
        std_area_px            : std-dev of nucleus area
        mean_eccentricity      : 0 = circular, ~1 = elongated
        mean_solidity          : area / convex-hull-area (1 = convex)
        density_per_megapixel  : nuclei per million pixels of tissue
                                 (lets us compare images of different sizes)

    If the image has zero detections we return NaNs for the morphometrics
    and 0 for count/density so the resulting CSV rows are still well-formed.
    """
    props = measure.regionprops(labels)
    h, w = image_shape[:2]
    megapixels = (h * w) / 1e6

    if not props:
        return {
            "nucleus_count": 0,
            "mean_area_px": np.nan,
            "median_area_px": np.nan,
            "std_area_px": np.nan,
            "mean_eccentricity": np.nan,
            "mean_solidity": np.nan,
            "density_per_megapixel": 0.0,
        }

    areas = np.array([p.area for p in props], dtype=float)
    ecc = np.array([p.eccentricity for p in props], dtype=float)
    sol = np.array([p.solidity for p in props], dtype=float)

    return {
        "nucleus_count": int(len(props)),
        "mean_area_px": float(areas.mean()),
        "median_area_px": float(np.median(areas)),
        "std_area_px": float(areas.std(ddof=0)),
        "mean_eccentricity": float(ecc.mean()),
        "mean_solidity": float(sol.mean()),
        "density_per_megapixel": float(len(props) / megapixels),
    }
