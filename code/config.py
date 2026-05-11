"""
config.py
---------
Single source of truth for paths, the cohort list, and tunable parameters.

Editing this file is the only place a non-author needs to touch when:
  - moving the input/output trees
  - adding a new cohort
  - retuning the classical segmentation thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ---- Paths ----------------------------------------------------------------
# Project root = the folder that contains `code/`, `doc/`, `results/` etc.
ROOT = Path(__file__).resolve().parent.parent

# Inputs (provided assessment data; never modified by this codebase)
INPUT_DIR = ROOT / "doc" / "Assessment"

# All generated artefacts go under here. Each segmentation method has its own
# subfolder so reviewers can compare like-for-like:
#   results/classical/overlays/<COHORT>_<image>_overlay.png
#   results/classical/masks/<COHORT>_<image>_mask.png
#   results/classical/per_image_stats.csv
#   results/stardist/...
#   results/cellpose/...
# Cross-method comparison artefacts and final figures live one level up:
#   results/per_cohort_summary.csv
#   results/method_agreement.csv
#   results/figures/...
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

# Cancer cohorts in the assessment (folder names under doc/Assessment/).
COHORTS: list[str] = ["BRC", "CRC", "HCC", "NSCLC_AD", "NSCLC_SCC"]


# ---- Classical-pipeline tunables -----------------------------------------
@dataclass(frozen=True)
class ClassicalParams:
    """
    Parameters controlling the classical (HED + watershed) segmenter.

    These were chosen by visual inspection on a few images per cohort and
    kept GLOBAL (no cohort-specific tuning) so the comparison across cancer
    types is fair.
    """

    # Gaussian smoothing on the H channel before thresholding. Removes
    # speckle without dissolving small lymphocytes.
    gaussian_sigma: float = 1.0

    # Reject regions outside this area window (pixels^2). Lower bound
    # discards noise/specks; upper bound discards merged blobs / artefacts.
    min_area: int = 30
    max_area: int = 4000

    # Convexity floor. Real nuclei are nearly convex (solidity ~0.9+).
    # Anything below 0.7 is usually a fragmented or artefact region.
    min_solidity: float = 0.70

    # Minimum spacing between watershed seeds (pixels). Smaller -> more
    # splits in dense clumps; larger -> more merging. 6 px works well at
    # the ~480x560 input resolution we have here.
    watershed_min_distance: int = 6

    # Percentile clip on the H channel before smoothing (robust contrast
    # stretch; reduces sensitivity to staining variability).
    h_percentile_lo: float = 1.0
    h_percentile_hi: float = 99.0


CLASSICAL = ClassicalParams()
