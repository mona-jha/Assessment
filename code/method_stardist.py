"""
method_stardist.py
------------------
Deep-learning nucleus segmenter using StarDist (2D_versatile_he, the model
pretrained specifically on H&E histopathology nuclei).

Why include this:
  StarDist represents nuclei as star-convex polygons radiating from a
  centre point, which is a strong prior for roughly-elliptical nuclei. It
  uses a different architecture than Cellpose (regression of polygon
  distances vs. flow vectors), so agreement between StarDist, Cellpose,
  and the classical pipeline is meaningful evidence in the absence of
  ground truth.

Local model loading:
  We deliberately do NOT use `StarDist2D.from_pretrained("2D_versatile_he")`
  because that path goes through keras' get_file, which performs an HTTPS
  hash check that fails behind a VPN with custom certificates. Instead we
  point StarDist at a local copy of the model:
      ~/.stardist/models/2D_versatile_he/
          config.json
          thresholds.json
          weights_best.h5
  These come from the official release zip:
      https://github.com/stardist/stardist-models/releases/download/v0.1/python_2D_versatile_he.zip
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

NAME = "stardist"

_MODEL = None
_BASEDIR = Path(os.path.expanduser("~/.stardist/models"))
_MODEL_NAME = "2D_versatile_he"


def _get_model():
    """Lazy-load the local StarDist H&E model on first use."""
    global _MODEL
    if _MODEL is None:
        # Quiet TensorFlow info/warning chatter so the tqdm bar stays clean.
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

        from stardist.models import StarDist2D

        model_dir = _BASEDIR / _MODEL_NAME
        if not model_dir.exists():
            raise FileNotFoundError(
                f"StarDist weights not found at {model_dir}.\n"
                "Download the zip and unpack it there:\n"
                "  https://github.com/stardist/stardist-models/releases/"
                "download/v0.1/python_2D_versatile_he.zip"
            )

        # basedir + name = load from disk only, no network calls.
        _MODEL = StarDist2D(None, name=_MODEL_NAME, basedir=str(_BASEDIR))
    return _MODEL


def segment(rgb: np.ndarray) -> np.ndarray:
    """
    Run StarDist on an RGB H&E image and return a uint32 instance-label
    image (0 = background, 1..N = individual nuclei).
    """
    from csbdeep.utils import normalize

    model = _get_model()

    # The H&E model was trained on per-channel 1-99% percentile-normalised
    # input, which is what the StarDist documentation recommends here.
    img = normalize(rgb, 1.0, 99.8, axis=(0, 1))

    labels, _details = model.predict_instances(
        img,
        # The default prob_thresh=0.69 misses many small lymphocyte nuclei
        # in dense regions of these images. 0.4 is a commonly-used setting
        # for 2D_versatile_he on dense H&E (still well above noise).
        prob_thresh=0.40,
        nms_thresh=0.30,
    )
    return labels.astype(np.uint32)
