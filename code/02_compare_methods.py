"""
02_compare_methods.py
=====================

Cross-method analysis. Without ground truth we cannot compute precision /
recall, so the strongest validation we have is **agreement** between three
independent methods (classical, Cellpose, StarDist). This script:

  1. Loads each method's per_image_stats.csv.
  2. Builds a long-form table with one row per (image, method).
  3. Computes per-image pairwise count differences and a mask-based IoU
     (Intersection-over-Union of the foreground binary masks).
  4. Saves:
        results/per_image_all_methods.csv
        results/method_agreement.csv
        results/figures/05_method_count_scatter.png
        results/figures/06_method_qualitative_grid.png  (5 cohorts x 4 cols:
            Original | classical | cellpose | stardist)

Why pairwise-IoU on the BINARY foreground (not instance IoU):
  Different methods assign different instance-IDs, so direct label-matching
  is non-trivial without Hungarian matching. Comparing the binary masks
  ("is this pixel inside any nucleus?") is a fair proxy for spatial
  agreement and is much simpler.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import COHORTS, INPUT_DIR, RESULTS_DIR, FIGURES_DIR
from image_io import load_rgb

METHODS = ["classical", "cellpose", "stardist"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_mask(method: str, cohort: str, image_stem: str) -> np.ndarray | None:
    """Read a uint16 instance mask written by 01_run_segmentation.py."""
    p = RESULTS_DIR / method / "masks" / f"{cohort}_{image_stem}_mask.png"
    if not p.exists():
        return None
    return cv2.imread(str(p), cv2.IMREAD_UNCHANGED)


def binary_iou(a: np.ndarray, b: np.ndarray) -> float:
    """Intersection-over-Union of two label images treated as foreground masks."""
    fa = a > 0
    fb = b > 0
    union = np.logical_or(fa, fb).sum()
    if union == 0:
        return 1.0  # both empty -> trivially perfect agreement
    inter = np.logical_and(fa, fb).sum()
    return float(inter / union)


def overlay_boundaries(rgb: np.ndarray, labels: np.ndarray, colour=(255, 255, 0)
                       ) -> np.ndarray:
    """Lightweight version of make_overlay (no count caption) for the grid."""
    from skimage.segmentation import find_boundaries
    out = rgb.copy().astype(np.uint8)
    if labels is None:
        return out
    bnd = find_boundaries(labels, mode="outer")
    out[bnd] = colour
    return out


# ---------------------------------------------------------------------------
# Step 1: long-form table
# ---------------------------------------------------------------------------
def build_long_table() -> pd.DataFrame:
    """Stack per_image_stats.csv from each method, tagged with method name."""
    frames = []
    for m in METHODS:
        p = RESULTS_DIR / m / "per_image_stats.csv"
        if not p.exists():
            print(f"  [skip] missing {p}")
            continue
        df = pd.read_csv(p)
        df["method"] = m
        frames.append(df)
    if not frames:
        raise SystemExit("No per_image_stats.csv files found. Run "
                         "01_run_segmentation.py for at least one method.")
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Step 2: pairwise IoU per image
# ---------------------------------------------------------------------------
def compute_agreement(long_df: pd.DataFrame) -> pd.DataFrame:
    """For every image, compute pairwise foreground-mask IoU between methods."""
    methods_present = [m for m in METHODS if m in long_df["method"].unique()]
    if len(methods_present) < 2:
        return pd.DataFrame()

    # Pivot to one row per image, with one count column per method.
    counts = long_df.pivot_table(index=["cohort", "image"],
                                 columns="method", values="nucleus_count").reset_index()

    rows = []
    for _, r in counts.iterrows():
        cohort = r["cohort"]
        image = r["image"]
        stem = Path(image).stem
        masks = {m: load_mask(m, cohort, stem) for m in methods_present}
        masks = {m: msk for m, msk in masks.items() if msk is not None}
        out = {"cohort": cohort, "image": image}
        for m in methods_present:
            out[f"count_{m}"] = int(r[m]) if m in r and pd.notna(r[m]) else None
        # pairwise IoU
        ms = list(masks.keys())
        for i in range(len(ms)):
            for j in range(i + 1, len(ms)):
                key = f"iou_{ms[i]}_vs_{ms[j]}"
                out[key] = round(binary_iou(masks[ms[i]], masks[ms[j]]), 4)
        rows.append(out)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Step 3: figures
# ---------------------------------------------------------------------------
def figure_count_scatter(long_df: pd.DataFrame, out_path: Path) -> None:
    """Per-image nucleus-count scatter: classical vs each DL method."""
    methods_present = [m for m in METHODS if m in long_df["method"].unique()]
    if "classical" not in methods_present or len(methods_present) < 2:
        return

    pivot = long_df.pivot_table(index=["cohort", "image"],
                                columns="method", values="nucleus_count").reset_index()

    others = [m for m in methods_present if m != "classical"]
    fig, axes = plt.subplots(1, len(others), figsize=(5.5 * len(others), 5),
                             squeeze=False)

    cohort_colour = {c: f"C{i}" for i, c in enumerate(COHORTS)}

    for ax, m in zip(axes[0], others):
        for cohort in COHORTS:
            sub = pivot[pivot["cohort"] == cohort]
            if "classical" in sub and m in sub:
                ax.scatter(sub["classical"], sub[m],
                           label=cohort, c=cohort_colour[cohort], s=40, alpha=0.85)
        # y = x reference line
        lo = min(pivot[["classical", m]].min())
        hi = max(pivot[["classical", m]].max())
        ax.plot([lo, hi], [lo, hi], "k--", alpha=0.4, linewidth=1)
        ax.set_xlabel("classical count")
        ax.set_ylabel(f"{m} count")
        ax.set_title(f"classical vs {m}")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="upper left")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def figure_method_grid(out_path: Path) -> None:
    """5x4 qualitative grid: one row per cohort, columns = original + 3 methods."""
    methods_present = [m for m in METHODS
                       if (RESULTS_DIR / m / "masks").exists()]
    if not methods_present:
        return

    fig, axes = plt.subplots(len(COHORTS), 1 + len(methods_present),
                             figsize=(3.5 * (1 + len(methods_present)),
                                      3.0 * len(COHORTS)),
                             squeeze=False)

    for r, cohort in enumerate(COHORTS):
        # Use Image1.png from each cohort as the canonical example.
        img_path = INPUT_DIR / cohort / "Image1.png"
        rgb = load_rgb(img_path)
        axes[r, 0].imshow(rgb)
        axes[r, 0].set_ylabel(cohort, fontsize=12)
        if r == 0:
            axes[r, 0].set_title("Original")

        for c, m in enumerate(methods_present, start=1):
            mask = load_mask(m, cohort, img_path.stem)
            overlay = overlay_boundaries(rgb, mask)
            axes[r, c].imshow(overlay)
            count = 0 if mask is None else int(mask.max())
            if r == 0:
                axes[r, c].set_title(m)
            axes[r, c].text(8, 22, f"n={count}", color="yellow", fontsize=10,
                             bbox=dict(facecolor="black", alpha=0.6, pad=2))

        for c in range(1 + len(methods_present)):
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    long_df = build_long_table()
    print(f"Loaded {len(long_df)} rows across methods: "
          f"{sorted(long_df['method'].unique())}")

    long_df.to_csv(RESULTS_DIR / "per_image_all_methods.csv", index=False)

    agreement = compute_agreement(long_df)
    if not agreement.empty:
        agreement.to_csv(RESULTS_DIR / "method_agreement.csv", index=False)

        # Print summary IoU per cohort.
        iou_cols = [c for c in agreement.columns if c.startswith("iou_")]
        print("\n=== Mean foreground-mask IoU per cohort ===")
        per_cohort = agreement.groupby("cohort")[iou_cols].mean().round(3)
        print(per_cohort.to_string())

        print("\n=== Per-method mean count per cohort ===")
        means = (long_df.groupby(["cohort", "method"])["nucleus_count"]
                        .mean().unstack().round(1))
        print(means.to_string())

    figure_count_scatter(long_df, FIGURES_DIR / "05_method_count_scatter.png")
    figure_method_grid(FIGURES_DIR / "06_method_qualitative_grid.png")
    print(f"\nWrote figures into {FIGURES_DIR}")


if __name__ == "__main__":
    main()
