"""
visualisation.py
----------------
Drawing helpers used by every method:
  - make_overlay : original image + nucleus boundaries + count caption
  - qualitative_grid : 5x4 figure (one row per cohort) for the report

Kept small and method-agnostic so adding a new segmenter requires zero
changes here.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from skimage import segmentation


def make_overlay(rgb: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """
    Return an HxWx3 uint8 image where:
      - nucleus boundaries are drawn in yellow
      - the integer nucleus count is printed top-left on a black box

    Yellow was chosen because it is highly visible on both the pink (eosin)
    and purple (hematoxylin) regions of an H&E image.
    """
    boundaries = segmentation.find_boundaries(labels, mode="outer")

    out = rgb.copy()
    if out.dtype != np.uint8:
        # Some loaders/methods produce float in [0, 1]; normalise to uint8.
        out = (out * 255).clip(0, 255).astype(np.uint8) if out.max() <= 1.0 else out.astype(np.uint8)

    out[boundaries] = [255, 255, 0]

    count = int(labels.max())
    text = f"Nuclei: {count}"
    # Black background rectangle for legibility on light/dark tissue.
    cv2.rectangle(out, (5, 5), (5 + 9 * len(text) + 10, 35), (0, 0, 0), thickness=-1)
    cv2.putText(out, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 0), 2, cv2.LINE_AA)
    return out


def qualitative_grid(
    rows: list[tuple[str, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
    column_titles: tuple[str, ...] = ("Original", "H channel", "Instances", "Overlay"),
    out_path: Path | None = None,
):
    """
    rows : list of (label, original_rgb, h_channel_or_None, label_image, overlay_rgb)
           one tuple per cohort.

    Produces a len(rows) x 4 figure. Pass out_path to save; otherwise returns
    the matplotlib Figure for inline display.
    """
    n = len(rows)
    fig, axes = plt.subplots(n, 4, figsize=(14, 3.2 * n))
    if n == 1:
        axes = np.array([axes])

    for r, (label, rgb, h, instances, overlay) in enumerate(rows):
        axes[r, 0].imshow(rgb)
        axes[r, 0].set_ylabel(label, fontsize=12)
        if h is not None:
            axes[r, 1].imshow(h, cmap="magma")
        axes[r, 2].imshow(instances, cmap="nipy_spectral")
        axes[r, 3].imshow(overlay)
        for c, title in enumerate(column_titles):
            if r == 0:
                axes[r, c].set_title(title)
            axes[r, c].set_xticks([])
            axes[r, c].set_yticks([])

    fig.tight_layout()
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return None
    return fig
