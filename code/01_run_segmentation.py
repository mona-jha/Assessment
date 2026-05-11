"""
01_run_segmentation.py
======================

Run ONE nucleus-segmentation method on all 50 H&E images and write its
artefacts to results/<method>/.

USAGE
-----
    python code/01_run_segmentation.py --method classical
    python code/01_run_segmentation.py --method cellpose
    python code/01_run_segmentation.py --method stardist

    # Smoke-test on one image per cohort:
    python code/01_run_segmentation.py --method classical --cohort BRC --limit 1

OUTPUTS (per method)
--------------------
    results/<method>/overlays/<COHORT>_<Image>_overlay.png
    results/<method>/masks/<COHORT>_<Image>_mask.png
    results/<method>/per_image_stats.csv      (50 rows, one per image)

WHY MULTIPLE METHODS?
---------------------
There is no ground-truth annotation for these images, so we run a
transparent classical pipeline plus one or two pretrained deep-learning
models. Agreement across methods is our main proxy for correctness; this is
analysed by 02_compare_methods.py.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from config import COHORTS, INPUT_DIR, RESULTS_DIR
from features import extract_features
from image_io import gather_inputs, load_rgb, output_paths, save_mask, save_overlay
from stain_norm import macenko_normalize
from visualisation import make_overlay


# Every method module exposes a `segment(rgb) -> labels` function and a
# `NAME` constant. Adding a new method = drop a new module here.
AVAILABLE_METHODS = {
    "classical": "method_classical",
    "cellpose": "method_cellpose",
    "stardist": "method_stardist",
}


def load_method(name: str):
    """Lazy-import the chosen method so we don't pay TF/Torch import costs
    when the user only wants the classical run."""
    if name not in AVAILABLE_METHODS:
        raise SystemExit(
            f"Unknown method '{name}'. Choose from: {list(AVAILABLE_METHODS)}"
        )
    return importlib.import_module(AVAILABLE_METHODS[name])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--method", required=True, choices=list(AVAILABLE_METHODS),
                        help="Which segmentation method to run.")
    parser.add_argument("--cohort", default=None,
                        help="Restrict to one cohort (e.g. BRC). Default: all.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N images (smoke-test).")
    parser.add_argument("--normalize", action="store_true",
                        help="Apply Macenko stain normalisation (off by default).")
    args = parser.parse_args()

    method = load_method(args.method)
    method_name = method.NAME

    items = gather_inputs(INPUT_DIR, COHORTS)
    if args.cohort:
        items = [it for it in items if it[0] == args.cohort]
    if args.limit:
        items = items[: args.limit]

    rows = []
    for cohort, path in tqdm(items, desc=f"Segmenting [{method_name}]"):
        rgb = load_rgb(path)
        rgb_in = macenko_normalize(rgb) if args.normalize else rgb
        labels = method.segment(rgb_in)

        overlay_p, mask_p = output_paths(method_name, cohort, path.stem, RESULTS_DIR)
        save_mask(labels, mask_p)
        save_overlay(make_overlay(rgb, labels), overlay_p)  # overlay on ORIGINAL

        feats = extract_features(labels, rgb.shape)
        feats.update({"cohort": cohort, "image": path.name})
        rows.append(feats)

    cols = ["cohort", "image", "nucleus_count", "mean_area_px", "median_area_px",
            "std_area_px", "mean_eccentricity", "mean_solidity",
            "density_per_megapixel"]
    df = pd.DataFrame(rows)[cols].sort_values(["cohort", "image"]).reset_index(drop=True)

    out_csv = RESULTS_DIR / method_name / "per_image_stats.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    # Per-cohort summary printed to stdout for quick eyeballing.
    summary = (df.groupby("cohort")
                 .agg(images=("image", "count"),
                      total_nuclei=("nucleus_count", "sum"),
                      count_mean=("nucleus_count", "mean"),
                      count_std=("nucleus_count", "std"),
                      area_mean=("mean_area_px", "mean"),
                      density_mean=("density_per_megapixel", "mean"))
                 .reset_index())
    print(f"\n=== [{method_name}] per-cohort summary ===")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nImages: {len(df)}   Total nuclei: {int(df['nucleus_count'].sum())}")
    print(f"Wrote: {out_csv}")


if __name__ == "__main__":
    main()
