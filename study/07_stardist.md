# 07 — StarDist explained

## What StarDist is
A deep-learning segmenter that represents each nucleus as a
**star-convex polygon** (Schmidt et al., 2018). For our task we use the
pretrained model `2D_versatile_he`, trained specifically on H&E
histopathology nuclei.

## The core idea — star-convex polygons

A polygon is **star-convex** with respect to a centre $\mathbf{c}$ if
every line segment from $\mathbf{c}$ to any boundary point lies entirely
inside the polygon.

For each pixel $\mathbf{p}$ inside a nucleus:
1. Pick a fixed number of **rays** $K$ (the model uses $K = 32$),
   evenly spaced in angle around $\mathbf{p}$.
2. Predict the **distance to the nearest boundary** along each ray
   $\mathbf{r}_k(\mathbf{p})$.

So for every pixel the network outputs:
- $p(\mathbf{p})$ — probability that this pixel is inside *some* nucleus.
- 32 ray distances $\mathbf{r}_1, \ldots, \mathbf{r}_{32}$.

A pixel + its 32 distances → a candidate polygon.

## How to get instances out
1. Score every candidate polygon by $p(\mathbf{p})$.
2. Apply **Non-Maximum Suppression (NMS)** with IoU threshold
   `nms_thresh` (we use 0.30): keep the highest-probability polygon, drop
   any other candidate that overlaps it by more than 30%.
3. Keep candidates with $p > $ `prob_thresh` (we use 0.40).
4. Rasterise the surviving polygons into an instance label image.

## Why it's well-suited to nuclei
Nuclei are roughly elliptical → close to star-convex w.r.t. their
centroid. The polygon prior is a *strong* inductive bias that hand-tunes
the model toward the right shapes, which makes it data-efficient and
fast at inference time.

## Why we lowered `prob_thresh`

The default `prob_thresh = 0.6925` (loaded from the pretrained model's
`thresholds.json`) was empirically too strict on dense lymphocyte
clusters in BRC and CRC: in our smoke test on `BRC/Image1.png`,
StarDist returned only **216** nuclei vs ~580 from the other two
methods.

Lowering to `prob_thresh = 0.40` brought the count to **495** — much
closer to classical (577) and Cellpose (590). The change cost zero
qualitative artefacts (we visually inspected) and is documented as a
common practice for `2D_versatile_he` on dense H&E.

## Our wrapper — local model load (no network)

We deliberately do *not* call `StarDist2D.from_pretrained(...)` because
that path goes through Keras' `get_file`, which performs an HTTPS hash
check. On some networks with custom certificates that fails. Instead
we point StarDist at a local copy:

```
~/.stardist/models/2D_versatile_he/
  ├── config.json
  ├── thresholds.json
  └── weights_best.h5
```

```python
import os
from stardist.models import StarDist2D
from csbdeep.utils import normalize

def _get_model():
    return StarDist2D(
        None,
        name="2D_versatile_he",
        basedir=os.path.expanduser("~/.stardist/models"),
    )

def segment(rgb):
    img = normalize(rgb, 1.0, 99.8, axis=(0, 1))
    labels, _ = _get_model().predict_instances(
        img, prob_thresh=0.40, nms_thresh=0.30,
    )
    return labels.astype(np.uint32)
```

## Strengths and weaknesses

**Strengths**
- Tiny model (~5 MB).
- Very fast on CPU (~0.6 s/image; ~30 s for 50 images).
- Strong shape prior → clean polygon outputs, no jagged edges.

**Weaknesses**
- The polygon prior is a constraint. Heavily overlapping or
  non-convex nuclei get under-segmented compared to Cellpose.
- Returns ~14% fewer total nuclei than the other two methods on our data.

## Why polygons (and not pixel masks)?

A traditional U-Net would output a per-pixel mask and then we'd run
connected components / watershed to get instances. That works but has
failure modes: two touching nuclei with no boundary gap between them
become one mask.

StarDist sidesteps this entirely: each polygon is *defined by its
centre*, so two touching nuclei produce two centres, hence two polygons.
NMS then enforces non-overlap. The instance question is solved by
construction, not by post-processing.

The price: nuclei that are not star-convex (e.g. heavily lobed or
overlapping) cannot be perfectly represented and are sometimes missed
or under-fit.

## How NMS works in StarDist (concretely)

1. Sort all candidate polygons by their probability $p$ in descending order.
2. Take the highest-probability polygon. Add it to the kept set.
3. For every remaining polygon, compute its IoU with the kept one.
4. Discard any whose IoU exceeds `nms_thresh = 0.30`.
5. Repeat from step 2 with the next highest-probability polygon
   that is still alive.
6. Stop when all polygons have either been kept or discarded.

The lower `nms_thresh` is, the more aggressive the suppression. 0.30
is StarDist's default and we did not change it.

## Why specifically `prob_thresh = 0.40` (and not 0.30 or 0.50)?

| `prob_thresh` | Total nuclei across BRC/Image1 | Visual impression                  |
|---------------|--------------------------------|------------------------------------|
| 0.69 (default)| 216                            | Massive under-detection.           |
| 0.50          | 358                            | Better but still misses many.       |
| **0.40**      | **495**                        | **Sweet spot**.                    |
| 0.30          | 532                            | A few visible false positives.      |
| 0.20          | 587                            | Many false positives in stroma.     |

We chose 0.40 because it brought StarDist closest to the other two
methods without introducing visible spurious detections in the
overlay.

## Limitations specific to StarDist

- **Overlapping nuclei** (lymphocyte clusters with cells partially
  occluding each other) are systematically under-detected because NMS
  removes them.
- **Highly elongated** nuclei (some columnar epithelial cells in CRC)
  press against the polygon prior — 32 rays struggle to capture a long
  thin shape.
- **Magnification mismatch**: the model was trained on H&E at
  particular magnifications. Our images appear close enough that no
  rescaling was needed, but always something to check.

## Reading
- Schmidt, Weigert, Broaddus, Myers (2018) — *Cell Detection with
  Star-convex Polygons* (MICCAI).
- StarDist GitHub: https://github.com/stardist/stardist
- Pretrained models:
  https://github.com/stardist/stardist-models/releases/tag/v0.1
