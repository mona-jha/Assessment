"""
method_cellpose.py
------------------
Deep-learning nucleus segmenter using Cellpose (v4, the CellposeSAM model).

Why include this:
  Cellpose is a generalist pretrained segmentation model. It uses a different
  architecture (U-Net + flow-vector regression, now SAM-based in v4) than
  StarDist, so when both DL methods AND the classical pipeline agree on a
  count, we have strong evidence the count is correct (we have no ground
  truth for these images).

Notes:
  - Cellpose v4 ships a single unified model ('cpsam'). The 'channels'
    argument from older Cellpose versions is no longer needed - v4 takes
    the RGB image directly.
  - 'diameter=None' lets Cellpose estimate the typical nucleus diameter per
    image; this is robust across the size variation in our 5 cohorts.
  - Runs on CPU; ~5-15 s per image at the resolutions in this dataset.
  - The first call downloads the pretrained weights (~700 MB) into the
    user's cellpose cache dir.
"""

from __future__ import annotations

import numpy as np

NAME = "cellpose"

# Model is heavy to load (~hundreds of MB) so we lazy-init once and cache.
_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        import torch
        from cellpose import models

        # Prefer Apple Metal (MPS) on M-series Macs - ~5-10x faster than CPU
        # for the CellposeSAM model on these image sizes. Falls back to CPU
        # cleanly on any machine without MPS.
        if torch.backends.mps.is_available():
            device = torch.device("mps")
        elif torch.cuda.is_available():
            device = torch.device("cuda")
        else:
            device = torch.device("cpu")
        _MODEL = models.CellposeModel(gpu=(device.type != "cpu"), device=device)
    return _MODEL


def segment(rgb: np.ndarray) -> np.ndarray:
    """
    Run Cellpose on an RGB image and return a uint32 instance-label image
    (0 = background, 1..N = individual nuclei).
    """
    model = _get_model()

    # Cellpose v4 returns (masks, flows, styles). We only need the masks,
    # which are int32 with one integer per detected nucleus.
    masks, _flows, _styles = model.eval(
        rgb,
        diameter=None,           # auto-estimate per-image
        flow_threshold=0.4,      # default; lower -> stricter cell shapes
        cellprob_threshold=0.0,  # default; lower -> more (but noisier) cells
    )

    return masks.astype(np.uint32)
