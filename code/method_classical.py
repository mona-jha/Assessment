"""
method_classical.py
-------------------
Classical (no-deep-learning) nucleus segmenter.

Pipeline, in plain English:

    RGB image
      |  Stain deconvolution (rgb2hed) keeps ONLY the hematoxylin channel,
      |  which is the one that stains nuclei blue/purple. Eosin (cytoplasm,
      |  stroma) is discarded. This gives us a clean grayscale "where are
      |  the nuclei?" map.
      v
    Hematoxylin channel
      |  Percentile clip + Gaussian smoothing handle stain variability and
      |  speckle without erasing small lymphocyte nuclei.
      v
    Otsu threshold -> binary mask of "this pixel is part of some nucleus"
      |
      |  Morphological cleanup (opening, hole-fill, drop tiny specks).
      v
    Binary mask of nuclei
      |  Two touching nuclei share a single connected component, so we use
      |  the distance transform: the pixel "deepest" inside each nucleus
      |  forms a peak, and watershed splits the component along the valleys
      |  between peaks. This is what gives us per-nucleus instances.
      v
    Watershed instance labels
      |  Final filter: drop regions outside a plausible nucleus area window
      |  and reject very non-convex shapes (staining artefacts, vessels).
      v
    Instance label image (uint32)

The single global parameter set lives in config.ClassicalParams so the
comparison across cohorts is fair (no per-cohort tuning).
"""

from __future__ import annotations

import warnings

import numpy as np
from scipy import ndimage as ndi
from skimage import color, filters, measure, morphology, segmentation
from skimage.feature import peak_local_max

from config import CLASSICAL, ClassicalParams

# scikit-image 0.26 emits a FutureWarning about a parameter rename in
# remove_small_objects. The behaviour we use is unaffected; suppress to
# keep the tqdm progress bar readable.
warnings.filterwarnings("ignore", category=FutureWarning, module="skimage")


NAME = "classical"


def hematoxylin_channel(rgb: np.ndarray, params: ClassicalParams = CLASSICAL) -> np.ndarray:
    """
    Run stain deconvolution and return the normalised H channel in [0, 1].

    Exposed as a standalone function because the qualitative grid in the
    report wants to display it side-by-side with the original image.
    """
    hed = color.rgb2hed(rgb)
    h = hed[..., 0]
    lo, hi = np.percentile(h, [params.h_percentile_lo, params.h_percentile_hi])
    h = np.clip((h - lo) / (hi - lo + 1e-8), 0.0, 1.0)
    return h.astype(np.float32)


def segment(rgb: np.ndarray, params: ClassicalParams = CLASSICAL) -> np.ndarray:
    """
    Segment nuclei from an RGB H&E image and return a uint32 instance-label
    image where 0 == background and each positive integer == one nucleus.
    """
    h = hematoxylin_channel(rgb, params)
    smooth = filters.gaussian(h, sigma=params.gaussian_sigma, preserve_range=True)

    # Otsu picks an automatic intensity threshold separating nuclear from
    # non-nuclear pixels in the H channel.
    thr = filters.threshold_otsu(smooth)
    binary = smooth > thr

    # Cleanup: opening removes single-pixel specks; hole-fill closes
    # small interior gaps; remove_small_objects drops noise blobs.
    binary = morphology.opening(binary, morphology.disk(2))
    binary = ndi.binary_fill_holes(binary)
    binary = morphology.remove_small_objects(binary, min_size=params.min_area, out=binary)

    if not binary.any():
        return np.zeros(rgb.shape[:2], dtype=np.uint32)

    # Distance transform: each foreground pixel gets its distance to the
    # nearest background pixel. Local maxima of this map -> nucleus centres.
    distance = ndi.distance_transform_edt(binary)
    coords = peak_local_max(
        distance,
        min_distance=params.watershed_min_distance,
        labels=binary,
        exclude_border=False,
    )

    markers = np.zeros(distance.shape, dtype=np.int32)
    if len(coords) == 0:
        # No clear peaks -> treat each connected component as one nucleus.
        markers, _ = ndi.label(binary)
    else:
        markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)
        markers, _ = ndi.label(markers)

    # Watershed flooding from the marker peaks splits touching nuclei
    # along the "ridges" of the inverted distance map.
    labels = segmentation.watershed(-distance, markers, mask=binary)

    # Final region filter: enforce plausible area + convexity.
    out = np.zeros_like(labels, dtype=np.uint32)
    next_id = 1
    for region in measure.regionprops(labels):
        if region.area < params.min_area or region.area > params.max_area:
            continue
        if region.solidity < params.min_solidity:
            continue
        out[labels == region.label] = next_id
        next_id += 1
    return out
