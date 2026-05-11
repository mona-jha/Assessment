"""
03_make_report_figures.py
=========================

Build the per-cohort aggregate figures used in the report and slides.
Reads each method's per_image_stats.csv and writes:

    results/figures/01_qualitative_grid_classical.png
    results/figures/02_count_by_cohort.png
    results/figures/03_area_by_cohort.png
    results/figures/04_density_by_cohort.png
    results/per_cohort_summary.csv  (one row per cohort, all methods)

Run after 01_run_segmentation.py has produced output for at least the
classical method. Cellpose / StarDist columns are added automatically if
those methods have also been run.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import COHORTS, INPUT_DIR, RESULTS_DIR, FIGURES_DIR
from image_io import load_rgb
from method_classical import hematoxylin_channel, segment as classical_segment
from visualisation import make_overlay, qualitative_grid


METHODS = ["classical", "cellpose", "stardist"]


# ---------------------------------------------------------------------------
# Aggregate per-cohort summary across methods
# ---------------------------------------------------------------------------
def per_cohort_summary() -> pd.DataFrame:
    rows = []
    for m in METHODS:
        p = RESULTS_DIR / m / "per_image_stats.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        for cohort, sub in df.groupby("cohort"):
            rows.append({
                "method": m,
                "cohort": cohort,
                "images": len(sub),
                "total_nuclei": int(sub["nucleus_count"].sum()),
                "count_mean": float(sub["nucleus_count"].mean()),
                "count_std": float(sub["nucleus_count"].std()),
                "area_mean_px": float(sub["mean_area_px"].mean()),
                "density_mean": float(sub["density_per_megapixel"].mean()),
                "density_std": float(sub["density_per_megapixel"].std()),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Figures (classical method drives the qualitative grid; the cross-method
# grid lives in 02_compare_methods.py)
# ---------------------------------------------------------------------------
def _classical_df() -> pd.DataFrame:
    p = RESULTS_DIR / "classical" / "per_image_stats.csv"
    if not p.exists():
        raise SystemExit(f"Missing {p}. Run 01_run_segmentation.py --method classical first.")
    return pd.read_csv(p)


def figure_count_box(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    df.boxplot(column="nucleus_count", by="cohort", ax=ax, grid=False)
    ax.set_title("Nucleus count per image, by cohort (classical)")
    ax.set_ylabel("Nucleus count")
    ax.set_xlabel("Cohort")
    plt.suptitle("")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def figure_area_box(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    df.boxplot(column="mean_area_px", by="cohort", ax=ax, grid=False)
    ax.set_title("Mean nucleus area (px^2) per image, by cohort (classical)")
    ax.set_ylabel("Mean area (px^2)")
    ax.set_xlabel("Cohort")
    plt.suptitle("")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def figure_density_bar(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    grp = df.groupby("cohort")["density_per_megapixel"]
    grp.mean().plot(kind="bar", yerr=grp.std(), ax=ax, capsize=4, color="#3a78b8")
    ax.set_ylabel("Nuclei per megapixel (mean +/- std)")
    ax.set_title("Nucleus density per cohort (classical)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def figure_qualitative_grid(out: Path) -> None:
    rows = []
    for cohort in COHORTS:
        path = INPUT_DIR / cohort / "Image1.png"
        rgb = load_rgb(path)
        h = hematoxylin_channel(rgb)
        labels = classical_segment(rgb)
        overlay = make_overlay(rgb, labels)
        rows.append((cohort, rgb, h, labels, overlay))
    qualitative_grid(rows, out_path=out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    summary = per_cohort_summary()
    summary_path = RESULTS_DIR / "per_cohort_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Wrote {summary_path}")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    df = _classical_df()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    figure_qualitative_grid(FIGURES_DIR / "01_qualitative_grid_classical.png")
    figure_count_box(df, FIGURES_DIR / "02_count_by_cohort.png")
    figure_area_box(df, FIGURES_DIR / "03_area_by_cohort.png")
    figure_density_bar(df, FIGURES_DIR / "04_density_by_cohort.png")
    print(f"Wrote figures into {FIGURES_DIR}")


if __name__ == "__main__":
    main()
