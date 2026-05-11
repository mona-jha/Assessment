"""
04_make_fpfn_figures.py
=======================
Generate false-positive / false-negative analysis figures using cross-method
disagreement as a proxy (no ground truth available).

For each image:
  - Binary mask per method (1 = any nucleus, 0 = background)
  - "Consensus" = pixel is nucleus in ≥2 of 3 methods
  - FP-like: method says YES but consensus says NO  (red)
  - FN-like: method says NO but consensus says YES  (blue)
  - True positive: both agree YES                   (green)

Produces:
  results/figures/07_fpfn_grid.png           — 5 cohorts × 3 methods grid
  results/figures/08_fpfn_counts_bar.png     — bar chart of FP/FN counts per method

    python code/04_make_fpfn_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from config import RESULTS_DIR, FIGURES_DIR, COHORTS

METHODS = ["classical", "cellpose", "stardist"]
METHOD_LABELS = {"classical": "Classical", "cellpose": "Cellpose", "stardist": "StarDist"}

# Colours for the overlay
COL_TP = np.array([0.18, 0.80, 0.44, 0.55])   # green
COL_FP = np.array([0.91, 0.20, 0.20, 0.65])   # red
COL_FN = np.array([0.20, 0.40, 0.91, 0.55])   # blue


def _load_binary(method: str, stem: str) -> np.ndarray:
    """Load a mask and return a binary (bool) array."""
    p = RESULTS_DIR / method / "masks" / f"{stem}_mask.png"
    if not p.exists():
        return None
    m = np.array(Image.open(p))
    return m > 0


def _consensus(masks: dict[str, np.ndarray]) -> np.ndarray:
    """Majority vote: pixel is 'nucleus' if ≥2 of 3 methods agree."""
    stack = np.stack(list(masks.values()), axis=0).astype(np.uint8)
    return stack.sum(axis=0) >= 2


def _overlay(rgb: np.ndarray, tp: np.ndarray, fp: np.ndarray,
             fn: np.ndarray) -> np.ndarray:
    """Blend TP/FP/FN colours onto the original RGB image."""
    out = rgb.astype(np.float32) / 255.0
    h, w = out.shape[:2]

    for mask, col in [(tp, COL_TP), (fp, COL_FP), (fn, COL_FN)]:
        if mask is None or mask.shape != (h, w):
            continue
        alpha = col[3]
        for c in range(3):
            out[:, :, c] = np.where(mask, out[:, :, c] * (1 - alpha) + col[c] * alpha,
                                    out[:, :, c])
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def _find_images() -> list[str]:
    """Return sorted list of image stems (e.g. 'BRC_Image1')."""
    stems = set()
    for p in (RESULTS_DIR / "classical" / "masks").glob("*_mask.png"):
        stems.add(p.stem.replace("_mask", ""))
    return sorted(stems)


def build_fpfn_grid():
    """5-cohort × 3-method grid showing TP (green) / FP (red) / FN (blue)."""
    all_stems = _find_images()

    # Pick one representative image per cohort (first one)
    cohort_stems = {}
    for cohort in COHORTS:
        for stem in all_stems:
            if stem.startswith(cohort + "_"):
                cohort_stems[cohort] = stem
                break

    fig, axes = plt.subplots(len(COHORTS), 3, figsize=(15, 5 * len(COHORTS)),
                             constrained_layout=True)

    for row, cohort in enumerate(COHORTS):
        stem = cohort_stems.get(cohort)
        if stem is None:
            continue

        # Load original image
        img_path = RESULTS_DIR / "classical" / "overlays" / f"{stem}_overlay.png"
        # Use the original from doc/Assessment instead
        for ext in [".png", ".jpg", ".tif"]:
            orig_path = Path(f"doc/Assessment/{cohort}/{stem.split('_', 1)[1]}{ext}")
            if orig_path.exists():
                break
        if orig_path.exists():
            rgb = np.array(Image.open(orig_path).convert("RGB"))
        else:
            # fallback: use overlay but strip contours
            rgb = np.array(Image.open(img_path).convert("RGB")) if img_path.exists() else None
            if rgb is None:
                continue

        # Load masks for all 3 methods
        masks = {}
        for method in METHODS:
            m = _load_binary(method, stem)
            if m is not None:
                masks[method] = m

        if len(masks) < 2:
            continue

        cons = _consensus(masks)

        for col_idx, method in enumerate(METHODS):
            ax = axes[row, col_idx]
            if method not in masks:
                ax.axis("off")
                continue

            bmask = masks[method]
            tp = bmask & cons
            fp = bmask & ~cons
            fn = ~bmask & cons

            overlay = _overlay(rgb, tp, fp, fn)
            ax.imshow(overlay)
            ax.set_xticks([]); ax.set_yticks([])

            n_tp = tp.sum()
            n_fp = fp.sum()
            n_fn = fn.sum()
            ax.set_title(f"{METHOD_LABELS[method]}\n"
                         f"TP {n_tp:,}  FP {n_fp:,}  FN {n_fn:,}",
                         fontsize=11, fontweight="bold")

            if col_idx == 0:
                ax.set_ylabel(cohort, fontsize=14, fontweight="bold", rotation=0,
                              labelpad=50, va="center")

    # Legend at the bottom
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=(0.18, 0.80, 0.44, 0.7), label="Agreed nucleus (TP-like)"),
        Patch(facecolor=(0.91, 0.20, 0.20, 0.8), label="Only this method (FP-like)"),
        Patch(facecolor=(0.20, 0.40, 0.91, 0.7), label="Missed by this method (FN-like)"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=3,
               fontsize=12, frameon=True, edgecolor="#ccc",
               bbox_to_anchor=(0.5, -0.01))

    fig.suptitle("False Positive / False Negative Analysis (Cross-Method Consensus)",
                 fontsize=18, fontweight="bold", y=1.01)

    out = FIGURES_DIR / "07_fpfn_grid.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


def build_fpfn_bar():
    """Bar chart: total FP-like and FN-like pixel counts per method."""
    all_stems = _find_images()

    totals = {m: {"tp": 0, "fp": 0, "fn": 0} for m in METHODS}

    for stem in all_stems:
        masks = {}
        for method in METHODS:
            m = _load_binary(method, stem)
            if m is not None:
                masks[method] = m

        if len(masks) < 2:
            continue

        cons = _consensus(masks)

        for method in METHODS:
            if method not in masks:
                continue
            bmask = masks[method]
            totals[method]["tp"] += (bmask & cons).sum()
            totals[method]["fp"] += (bmask & ~cons).sum()
            totals[method]["fn"] += (~bmask & cons).sum()

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)

    colors = {"tp": "#2ECC71", "fp": "#E74C3C", "fn": "#3498DB"}
    labels_map = {"tp": "Agreed (TP-like)", "fp": "Unique to method (FP-like)",
                  "fn": "Missed (FN-like)"}

    for i, method in enumerate(METHODS):
        ax = axes[i]
        vals = totals[method]
        total_px = vals["tp"] + vals["fp"] + vals["fn"]
        if total_px == 0:
            total_px = 1

        bars = ax.bar(
            ["TP-like", "FP-like", "FN-like"],
            [vals["tp"], vals["fp"], vals["fn"]],
            color=[colors["tp"], colors["fp"], colors["fn"]],
            edgecolor="white", linewidth=1.5
        )

        # Percentage labels on bars
        for bar, key in zip(bars, ["tp", "fp", "fn"]):
            pct = vals[key] / total_px * 100
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f"{vals[key]:,}\n({pct:.1f}%)",
                    ha="center", va="bottom", fontsize=10, fontweight="bold")

        ax.set_title(METHOD_LABELS[method], fontsize=14, fontweight="bold")
        ax.set_ylabel("Pixels" if i == 0 else "")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))

    fig.suptitle("Pixel-Level FP / FN Analysis (vs. 2-of-3 Consensus)",
                 fontsize=16, fontweight="bold")

    out = FIGURES_DIR / "08_fpfn_counts_bar.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


def build_fpfn_cohort_bar():
    """Per-cohort breakdown of FP/FN rates for each method."""
    all_stems = _find_images()

    data = {m: {c: {"tp": 0, "fp": 0, "fn": 0} for c in COHORTS} for m in METHODS}

    for stem in all_stems:
        cohort = None
        for c in COHORTS:
            if stem.startswith(c + "_"):
                cohort = c
                break
        if cohort is None:
            continue

        masks = {}
        for method in METHODS:
            m = _load_binary(method, stem)
            if m is not None:
                masks[method] = m

        if len(masks) < 2:
            continue

        cons = _consensus(masks)

        for method in METHODS:
            if method not in masks:
                continue
            bmask = masks[method]
            data[method][cohort]["tp"] += (bmask & cons).sum()
            data[method][cohort]["fp"] += (bmask & ~cons).sum()
            data[method][cohort]["fn"] += (~bmask & cons).sum()

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True,
                             sharey=False)
    x = np.arange(len(COHORTS))
    width = 0.35

    for i, method in enumerate(METHODS):
        ax = axes[i]
        fp_rates = []
        fn_rates = []
        for cohort in COHORTS:
            d = data[method][cohort]
            total = d["tp"] + d["fp"] + d["fn"]
            if total == 0:
                total = 1
            fp_rates.append(d["fp"] / total * 100)
            fn_rates.append(d["fn"] / total * 100)

        b1 = ax.bar(x - width/2, fp_rates, width, label="FP-like %",
                     color="#E74C3C", alpha=0.85, edgecolor="white")
        b2 = ax.bar(x + width/2, fn_rates, width, label="FN-like %",
                     color="#3498DB", alpha=0.85, edgecolor="white")

        ax.set_xticks(x)
        ax.set_xticklabels(COHORTS, fontsize=10, rotation=30, ha="right")
        ax.set_title(METHOD_LABELS[method], fontsize=14, fontweight="bold")
        ax.set_ylabel("% of nuclear pixels" if i == 0 else "")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if i == 0:
            ax.legend(fontsize=10, frameon=True, edgecolor="#ccc")

    fig.suptitle("Per-Cohort FP / FN Rates by Method (vs. 2-of-3 Consensus)",
                 fontsize=16, fontweight="bold")

    out = FIGURES_DIR / "09_fpfn_cohort_bar.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    build_fpfn_grid()
    build_fpfn_bar()
    build_fpfn_cohort_bar()
    print("Done — 3 FP/FN figures generated.")
