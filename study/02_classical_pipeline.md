# 02 — Classical pipeline walkthrough

This file traces our classical (no-DL) segmenter end-to-end. Code is in
[`code/method_classical.py`](../code/method_classical.py). Read this
together with that file open.

## The pipeline at a glance

```
RGB image
 │
 ▼  (1) Stain deconvolution (rgb2hed) → keep H channel
Hematoxylin channel
 │
 ▼  (2) Percentile clip [1%, 99%] + Gaussian smoothing (σ=1)
Smooth nuclei map
 │
 ▼  (3) Otsu threshold
Binary "is this a nucleus pixel?" mask
 │
 ▼  (4) Morphology: opening, hole-fill, drop tiny specks
Cleaned binary mask
 │
 ▼  (5) Distance transform → peak_local_max → watershed
Instance label image (1 integer per nucleus)
 │
 ▼  (6) Region filter: area in [30, 4000], solidity ≥ 0.70
Final instance labels
```

Each step has its own deep-dive file — they are linked inline below.

## Step 1: stain deconvolution
Goal: get a grayscale image where pixel intensity = "how blue/purple is
this pixel?"

```python
from skimage import color
hed = color.rgb2hed(rgb)        # 3-channel: H, E, DAB
h_channel = hed[..., 0]          # nucleus-specific
```

Why not grayscale? Because grayscale collapses *all* colours to one
value. H&E gives us colour-coded structures; deconvolution preserves
that information.

→ Full math in [03_stain_deconvolution.md](03_stain_deconvolution.md).

## Step 2: contrast stretch + smoothing

```python
import numpy as np
from skimage import filters
lo, hi = np.percentile(h_channel, [1, 99])
h = np.clip((h_channel - lo) / (hi - lo + 1e-8), 0, 1)
smooth = filters.gaussian(h, sigma=1.0, preserve_range=True)
```

- **Percentile clip** is a robust contrast stretch. Min/max would be
  fooled by a single bright artefact; the 1st/99th percentiles ignore
  outliers.
- **σ = 1.0 Gaussian** removes single-pixel speckle without dissolving
  small lymphocyte nuclei (which are ~5 px across).

## Step 3: Otsu threshold

```python
thr = filters.threshold_otsu(smooth)
binary = smooth > thr
```

Otsu picks the threshold that minimises within-class variance — the
"natural" split between two intensity populations (background vs nucleus).

→ Theory in [04_thresholding_morphology.md](04_thresholding_morphology.md).

## Step 4: morphological cleanup

```python
from skimage import morphology
from scipy import ndimage as ndi
binary = morphology.opening(binary, morphology.disk(2))
binary = ndi.binary_fill_holes(binary)
binary = morphology.remove_small_objects(binary, min_size=30)
```

- **Opening (erode then dilate)** with a 2-pixel disk peels off
  single-pixel noise and thin connections between nuclei without
  shrinking real nuclei much.
- **Hole-fill** closes pinpricks inside a nucleus that survived Otsu
  (e.g. a slightly lighter nucleolus).
- **Drop < 30 px²** kills the rest of the speckle.

→ Why each operator works: [04_thresholding_morphology.md](04_thresholding_morphology.md).

## Step 5: watershed splits touching nuclei

This is the hardest and most important step. After Step 4 we have a
binary mask that says "nucleus pixel: yes/no", but two touching nuclei
share **one** connected component.

```python
distance = ndi.distance_transform_edt(binary)
from skimage.feature import peak_local_max
coords = peak_local_max(distance, min_distance=6, labels=binary)
markers = np.zeros_like(distance, dtype=int)
markers[tuple(coords.T)] = np.arange(1, len(coords)+1)
markers, _ = ndi.label(markers)
from skimage.segmentation import watershed
labels = watershed(-distance, markers, mask=binary)
```

Concept: each nucleus has a *deepest interior point* far from any edge.
That point is a peak of the distance map. Watershed floods from each
peak, splitting touching nuclei along their narrow joining ridge.

→ Picture-book explanation in [05_watershed_instances.md](05_watershed_instances.md).

## Step 6: region filter

```python
from skimage import measure
out = np.zeros_like(labels, dtype=np.uint32)
nid = 1
for r in measure.regionprops(labels):
    if not (30 <= r.area <= 4000):  continue
    if r.solidity < 0.70:           continue
    out[labels == r.label] = nid
    nid += 1
```

- **Area window** rejects specks (too small) and merged blobs / vessels
  (too big).
- **Solidity = area / convex_hull_area**. Real nuclei are nearly convex
  (solidity ≥ 0.9 typically). Anything with solidity < 0.7 is usually
  a stromal artefact or fragmented region.

→ Definitions in [09_morphometrics.md](09_morphometrics.md).

## Why a single global parameter set?

We never tune parameters per cohort. That keeps the cohort comparison
**fair** — any difference in counts comes from biology, not from
parameter cheating. Per-cohort tuning would bump numbers but break
generalisation.

## Where this pipeline fails
- **Very dense lymphocyte clusters**: watershed sometimes merges 2–3
  small nuclei when their peaks are within 6 px of each other. Solution
  in production: lower `min_distance` per cohort, or move to a DL method.
- **Very large nuclei** in HCC: watershed occasionally splits a single
  large hepatocyte nucleus into two pieces. Solution: tune
  `watershed_min_distance` upward, or use the DL methods (which don't
  rely on distance peaks).

## Worked numerical example

For `BRC/Image1.png` (480 × 560 px), the classical pipeline produces:

| Stage                                | Effect                                            |
|--------------------------------------|---------------------------------------------------|
| `rgb2hed` — H channel                | Float image in roughly $[-0.4, 0.9]$.             |
| Percentile clip [1%, 99%] + scale    | Float in $[0, 1]$; histogram now bimodal.         |
| Gaussian σ=1                         | Removes single-pixel speckle.                     |
| Otsu threshold (≈ 0.32)              | ~24% of pixels become foreground.                 |
| Opening (disk r=2)                   | Foreground drops by ~3% — single-pixel noise gone.|
| Hole-fill                            | Adds back ~0.5% — interior nucleolus pinpricks.   |
| Drop < 30 px²                        | Removes ~150 specks, no real nuclei lost.         |
| Distance transform                   | Per-pixel distance to nearest background pixel.   |
| `peak_local_max(min_distance=6)`     | ~620 candidate centres found.                     |
| `watershed(-distance, markers, mask)`| 620 candidate instances.                          |
| Region filter (area, solidity)       | 577 final nuclei.                                 |

Final: 577 nuclei in this image. Cellpose finds 590, StarDist 495 (with
`prob_thresh=0.4`). Classical and Cellpose disagree by ~2%.

## Parameter sensitivity (what happens if you tune the wrong knob)

| Knob                          | Default | If too small                            | If too large                            |
|-------------------------------|---------|-----------------------------------------|-----------------------------------------|
| `gaussian_sigma`              | 1.0     | Specks survive → false positives.       | Small lymphocyte nuclei dissolve.       |
| `min_area`                    | 30      | Many specks become "nuclei".            | Small lymphocytes excluded.             |
| `max_area`                    | 4000    | Large hepatocytes excluded.             | Merged blobs survive as one nucleus.    |
| `min_solidity`                | 0.70    | Stromal artefacts retained.             | Real but lobed nuclei rejected.         |
| `peak_local_max(min_distance)`| 6       | Over-segmentation (one nucleus → many).| Under-segmentation (many → one).        |
| `opening` disk radius         | 2       | Thin bridges between nuclei survive.    | Real small nuclei eaten by erosion.     |

We set every knob once, by visual inspection on a single BRC image, and
never touched them again — that's the whole point of the "single global
parameter set" rule.

## When this pipeline shines
- Tissue with **well-separated** nuclei (HCC).
- Datasets where you cannot afford a GPU.
- When you need **fully explainable** decisions (regulatory contexts).

## When it falls behind DL
- Very dense lymphocyte clusters (CRC, BRC) — distance peaks fight.
- Strong stain shifts (no Macenko normalisation here).
- Unusual nucleus shapes (apoptotic, mitotic).

## Mental model

The classical pipeline is a sequence of *priors*:

1. **Stain prior**: nuclei stain with hematoxylin (Step 1).
2. **Intensity prior**: nuclei are uniformly bright in the H channel (Steps 2–3).
3. **Shape prior — connectivity**: a nucleus is one connected component (Step 4).
4. **Shape prior — geometry**: a nucleus has one centre, well inside it (Step 5).
5. **Shape prior — convexity**: nuclei are convex with bounded area (Step 6).

If any of these priors is wrong for a particular image, the
corresponding step fails. DL methods replace these explicit priors with
learned ones — that's the only real difference.

## Next steps
- See [03_stain_deconvolution.md](03_stain_deconvolution.md) for the
  math of step 1.
- See [05_watershed_instances.md](05_watershed_instances.md) for the
  intuition behind the trickiest step.
