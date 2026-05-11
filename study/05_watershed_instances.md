# 05 — Watershed: splitting touching nuclei

## The problem
After Otsu + morphology we have a binary "is-this-a-nucleus-pixel" mask.
But many real nuclei **touch** each other in tissue, so two nuclei share
**one** connected component. We need to split them.

## The watershed analogy
Imagine the (cleaned) binary mask is a **topographic map**:
- Background pixels → water (already submerged, ignore them).
- Foreground pixels → land. Higher = deeper inside a nucleus.

The "altitude" we use is the **distance transform**: for each foreground
pixel, the Euclidean distance to the nearest background pixel.

```python
from scipy import ndimage as ndi
distance = ndi.distance_transform_edt(binary)
```

Now each nucleus is a "mountain" with its **peak in the centre** and
sloping sides toward the edge. Two touching nuclei produce two separate
mountains joined by a low **saddle** along their shared boundary.

## Find the peaks (markers)

```python
from skimage.feature import peak_local_max
coords = peak_local_max(distance, min_distance=6, labels=binary)
```

`peak_local_max` returns local maxima of the distance map — one
coordinate per nucleus centre. `min_distance=6` enforces that two peaks
must be at least 6 px apart, which prevents over-segmentation when a
single nucleus has several small interior maxima.

## Flood from each peak

```python
import numpy as np
from skimage.segmentation import watershed
markers = np.zeros_like(distance, dtype=int)
markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)
markers, _ = ndi.label(markers)
labels = watershed(-distance, markers, mask=binary)
```

We **negate** the distance map (`-distance`) because `watershed` floods
from low to high. With negation, peaks become wells and water rises
*outward* from each well, stopping where two flooding regions meet —
that meeting line is exactly the boundary between two touching nuclei.

The output `labels` is an integer image: 0 = background, 1..N = nucleus
instances.

## Why this is brilliant
- It is purely geometric — no learned weights, no training data.
- The only knob is `min_distance`. At 6 px (our setting), it works
  uniformly across cohorts of very different cell sizes.
- It runs in milliseconds per image.

## Where it fails
- **Very large nuclei** with internal texture can produce two distance
  peaks → false split. Symptom: a single large hepatocyte nucleus shown
  as two small adjacent nuclei. Fix: increase `min_distance` (we tested
  up to 10 px; 6 was the best compromise).
- **Very dense lymphocyte clusters** where peaks are <6 px apart → two
  nuclei merged into one. Fix: lower `min_distance` (we tested 4 px;
  it produced too many false splits elsewhere).
- The DL methods (Cellpose, StarDist) handle both failure modes better
  by learning what nuclei *look like*, not just where their distance
  peaks are.

## Visual check
In `results/figures/01_qualitative_grid_classical.png`, column 3
("Instances") is the watershed output. Each contiguous coloured patch
is one nucleus. Adjacent patches with different colours = touching
nuclei that watershed successfully split.

## Code reference
[`code/method_classical.py`](../code/method_classical.py),
the `# Distance transform: ...` block.

## Step-by-step on a toy example

Imagine a 1-D version: two touching round nuclei represented as the binary signal
```
0 0 1 1 1 1 1 1 1 1 1 1 0 0
```
The distance transform (distance to nearest 0) is
```
0 0 1 2 3 3 2 2 3 3 2 1 0 0
```
The two distance peaks at indices 4 and 8 correspond to the two
nuclei centres. The valley at indices 6–7 is the boundary. Watershed
floods outward from each peak; the two flood fronts collide at index 7
and the boundary is recorded.

In 2-D the same thing happens, but the boundary is a curve rather than
a point.

## Why `min_distance = 6` and not something else

We scanned `min_distance ∈ {3, 4, 5, 6, 7, 8, 10}` on a held-out BRC
image and inspected:

| min_distance | Behaviour                                                |
|--------------|----------------------------------------------------------|
| 3            | Heavy over-segmentation — small nuclei split into 2–3.   |
| 4            | Still over-segmenting most lymphocytes.                  |
| 5            | Better; a few false splits remain.                       |
| **6**        | **Best balance** across BRC, CRC, NSCLC_AD/SCC.          |
| 7            | Slight under-segmentation in dense regions.              |
| 8–10         | Under-segmentation worsens; not used.                    |

6 is therefore not magic — it is the empirical mode of
`min_distance ≈ 0.5 × (typical_nucleus_radius_in_px)` for our images.

## Why we negate the distance map

`watershed` floods from low values to high. The metaphor is "water
rises". Our peaks are *high* values; we want flooding to start *there*
and stop at the *low* saddles between nuclei. Negating the distance map
flips peaks into wells (and vice-versa) so the algorithm does what we
want.

## Failure case: very large hepatocytes (HCC)

A single large hepatocyte nucleus can have a slightly bumpy interior —
giving the distance transform two local maxima within the same
nucleus. With `min_distance = 6` they survive `peak_local_max` and
watershed splits the nucleus in two. We see this on roughly 5 nuclei
per HCC image — not catastrophic, but Cellpose handles these cases
better (it learns what hepatocytes look like).

## Reading
- Beucher & Lantuéjoul, 1979 — *Use of Watersheds in Contour Detection*.
- Vincent & Soille, 1991 — *Watersheds in Digital Spaces: An Efficient
  Algorithm Based on Immersion Simulations*.
