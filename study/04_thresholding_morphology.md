# 04 — Thresholding & morphology

## Otsu's method (the threshold)

We have a grayscale image where bright = nucleus, dark = background. We
need a single intensity threshold that separates them.

**Otsu's idea**: choose the threshold $t$ that **minimises the
within-class variance** (equivalently, maximises the between-class
variance). For every candidate $t$, compute:

$$
\sigma_W^2(t) = w_0(t)\,\sigma_0^2(t) + w_1(t)\,\sigma_1^2(t)
$$

where $w_0, \sigma_0^2$ describe pixels with intensity $\le t$ and
$w_1, \sigma_1^2$ describe pixels $> t$.

Pick the $t$ that minimises $\sigma_W^2$. That's it.

```python
from skimage import filters
thr = filters.threshold_otsu(smooth)
binary = smooth > thr
```

**When Otsu fails:** if the histogram is not actually bimodal (e.g. the
image is mostly background with a tiny bit of tissue), Otsu picks a
weird threshold. Mitigation in our pipeline: percentile-clip + Gaussian
smooth first; this makes the histogram cleaner and more bimodal.

## Morphological operators (cleanup)

After thresholding, `binary` has a lot of small mistakes:
- Single-pixel noise saying "yes" where it shouldn't.
- Tiny holes inside nuclei (e.g. nucleolus pixels darker than the rest).
- Thin bridges between nearby nuclei.

We fix these with **mathematical morphology** — set operations using a
small "structuring element" $B$ (we use a disk of radius 2).

### Erosion `⊖`
Slide $B$ over the image. A pixel survives only if $B$ fits entirely
inside the foreground.
- Effect: shrinks foreground, removes thin features.

### Dilation `⊕`
Slide $B$. A pixel becomes foreground if $B$ overlaps any foreground.
- Effect: grows foreground, fills small gaps.

### Opening `∘ = (⊖ then ⊕)`
Erode, then dilate.
- Effect: removes small noise specks; preserves big structures.

```python
from skimage import morphology
binary = morphology.opening(binary, morphology.disk(2))
```

### Hole-fill
Specifically targets *interior holes* — connected background components
that are completely enclosed by foreground.

```python
from scipy import ndimage as ndi
binary = ndi.binary_fill_holes(binary)
```

This closes the dark nucleolus inside a nucleus, etc.

### Remove small objects
After the above we still have specks below the size of any plausible
nucleus. Drop them by area.

```python
binary = morphology.remove_small_objects(binary, min_size=30)
```

The `min_size=30` (px²) was set by visual inspection: the smallest real
lymphocyte nuclei in our images are ~30–40 px².

## Why this exact order?
1. **Opening first** — removes thin bridges so erosion in opening doesn't
   need to fight against connected nuclei.
2. **Hole-fill after** — opening can occasionally widen a hole; closing
   it after is safe.
3. **Drop small objects last** — anything smaller than 30 px² that
   survived opening + hole-fill is definitely noise.

## Visualising what happens

In `results/figures/01_qualitative_grid_classical.png` the third column
("Instances") shows the result *after* this stage but with watershed
already applied. To see just-after-morphology, you would inspect the
intermediate binary mask before Step 5.

## Why we don't use thresholding alone for the final step
Even after perfect morphology, two **touching** nuclei still form one
blob. Morphology alone cannot separate them — it just cleans noise.
The next step (watershed,
[05_watershed_instances.md](05_watershed_instances.md)) is what actually
gives us per-instance labels.

## Code reference
[`code/method_classical.py`](../code/method_classical.py), function
`segment`, around the comment `"Cleanup"`.

## Algorithmic depth — Otsu's derivation

Let $L$ be the number of grey levels (256 for 8-bit). Let $p_i$ be the
probability of grey level $i$ (its histogram count divided by total
pixels). For a candidate threshold $t$:

- Class probabilities: $w_0(t) = \sum_{i=0}^{t} p_i$, $w_1(t) = 1 - w_0(t)$.
- Class means: $\mu_0(t) = \frac{1}{w_0(t)} \sum_{i=0}^{t} i \, p_i$,
  $\mu_1(t) = \frac{1}{w_1(t)} \sum_{i=t+1}^{L-1} i \, p_i$.
- Class variances: $\sigma_0^2(t)$, $\sigma_1^2(t)$ — second moments
  about each mean.

Otsu shows that minimising within-class variance is equivalent to
*maximising* between-class variance:

$$
\sigma_B^2(t) = w_0(t)\,w_1(t)\,(\mu_1(t) - \mu_0(t))^2
$$

This is much faster to compute (one pass) and is what scikit-image
actually uses internally.

## A common pitfall

Otsu's method is **per-image**. Two BRC images of similar tissue can
produce slightly different thresholds. That is fine for our use case
but something to remember if you ever need *consistent* thresholds
across a whole study — you would average the per-image Otsu values, or
use a fixed threshold derived from a calibration set.

## Picking the right structuring element

| SE shape   | When to use                                     |
|------------|-------------------------------------------------|
| `disk(r)`  | Most nuclei (rotationally symmetric).           |
| `square(s)`| Faster, slight bias along axes — rarely needed. |
| `diamond(r)` | Sharper corners; we never use this.           |

We use `disk(2)` because it is the smallest disk that *connects through
itself* across single-pixel speckle without erosion eating real ~5 px
lymphocyte nuclei.

