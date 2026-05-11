# 06 — Cellpose explained

## What Cellpose is
A **pretrained, generalist deep-learning segmenter** for cells and
nuclei. Trained by Stringer et al. (2020, *Nature Methods*) on a very
diverse dataset of microscopy images. The headline feature: it works
out-of-the-box on data it has never seen — including H&E.

We use **Cellpose v4 (`cpsam`)**, released in 2024. v4 unified all
previous models into a single SAM-based architecture and removed the
need to choose a model variant or specify input channels.

## The core algorithm (v3 and earlier — flow vectors)

Cellpose's traditional trick is to predict, for every pixel, a 2D
**flow vector** that points toward the centre of its nucleus.

1. A U-Net takes the image and predicts:
   - $f_y(x,y)$ — vertical flow at each pixel.
   - $f_x(x,y)$ — horizontal flow at each pixel.
   - $p(x,y)$ — probability that the pixel belongs to *some* cell.
2. Run **gradient ascent** on the flow field starting from each pixel.
   Pixels that converge to the same fixed point belong to the same cell.
3. Connected components of "same convergence point" → instances.

This neatly handles the touching-nuclei problem (each nucleus has its
own attractor), without needing watershed or any geometric prior.

## What changed in v4 (`cpsam`)
- Backbone is a **Segment Anything (SAM)**-style transformer instead of
  a U-Net.
- A **single unified model** replaces v3's many variants.
- The `channels` argument is gone — you pass the RGB image directly.
- `diameter=None` lets the model auto-estimate scale per image.

The output mask format is identical to v3, so our wrapper code is
trivially short.

## Our wrapper

[`code/method_cellpose.py`](../code/method_cellpose.py):

```python
from cellpose import models
import torch

def _get_model():
    if torch.backends.mps.is_available():
        device = torch.device("mps")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    return models.CellposeModel(gpu=(device.type != "cpu"), device=device)

def segment(rgb):
    model = _get_model()
    masks, _flows, _styles = model.eval(
        rgb,
        diameter=None,
        flow_threshold=0.4,
        cellprob_threshold=0.0,
    )
    return masks.astype(np.uint32)
```

## Why MPS matters

| Device              | Time per image | 50-image total |
|---------------------|----------------|-----------------|
| Apple M-series CPU  | ~150 s         | ~2 h            |
| Apple Metal (MPS)   | ~6 s           | ~5 min          |

That's a **25× speedup** for free — no installation hassle, no NVIDIA
GPU needed. This is why the pipeline is practical on a laptop.

## Hyperparameters we expose

| Param                | Default | What it does                                     |
|----------------------|---------|--------------------------------------------------|
| `diameter`           | None    | Expected cell diameter (px); None = auto-estimate |
| `flow_threshold`     | 0.4     | Reject masks whose flow doesn't match prediction |
| `cellprob_threshold` | 0.0     | Min cell probability to keep a pixel             |
| `min_size`           | 15      | Drop masks smaller than this (px²)               |

We use the defaults except `diameter=None`. They worked well across all
five cohorts without tuning — that's the whole appeal of a generalist
DL model.

## Strengths and weaknesses

**Strengths**
- Robust across tissue types, stain variations, magnifications.
- Handles touching nuclei without an explicit watershed step.
- No training data required.

**Weaknesses**
- Slow without a GPU/MPS.
- ~1 GB model file to download.
- Behaviour is opaque — when it makes a mistake, you cannot debug
  parameters the way you can in the classical pipeline.

## Toy example of the flow-field idea

Imagine a single round nucleus centred at $(c_x, c_y)$. For a pixel
$(x, y)$ inside the nucleus, the *target* flow vector points toward the
centre:

$$
\mathbf{f}(x, y) = \frac{(c_x - x,\; c_y - y)}{\|(c_x - x,\; c_y - y)\|}
$$

A U-Net is trained, image-by-image, to predict this normalised vector
at every pixel. At inference time we don't know the centre, but we
follow the predicted vector field one step at a time — like rolling a
ball downhill. After ~200 steps every pixel has converged to a
single attractor (the nucleus centre). All pixels with the same
attractor belong to the same nucleus.

The beauty of this formulation: **two touching nuclei have two
different attractors**, so they get different labels automatically. No
watershed step needed.

## How v4 differs from v3 in practice

| Aspect                | Cellpose v3 (`nuclei`, `cyto`, `cyto2`, ...) | Cellpose v4 (`cpsam`)            |
|-----------------------|-----------------------------------------------|----------------------------------|
| Backbone              | U-Net                                         | SAM-style transformer            |
| Channel argument      | Required (`channels=[0, 0]` etc.)             | None — takes RGB directly        |
| Model variants        | ~6                                            | 1 unified model                  |
| Weights size          | ~25 MB                                        | ~1.1 GB                          |
| Speed (CPU)           | ~3 s/image                                    | ~150 s/image                     |
| Speed (GPU/MPS)       | ~0.3 s/image                                  | ~6 s/image                       |
| Quality across H&E    | Good with `nuclei` model                      | Better, more uniform across cohorts |

v4 is much heavier but generalises better. For this assessment we
stuck with v4 because we wanted the most accurate generalist baseline.

## Why `flow_threshold = 0.4`?

During inference Cellpose:
1. Predicts flow + cell-prob.
2. Runs gradient ascent to get instance proposals.
3. **Re-projects each proposal** through the flow field and compares
   the resulting flow to the predicted flow.
4. Rejects proposals where the discrepancy exceeds `flow_threshold`.

`flow_threshold = 0.4` is the v4 default and was empirically a good
compromise. Lowering it would be more conservative (drop more
proposals); raising it would keep more.

## What can go wrong

- **MPS bug on early macOS releases**: certain ops fall back to CPU
  silently. Fix: ensure `torch >= 2.1` and `macOS >= 14`.
- **Out-of-memory** on whole-slide images: split into 1024-px tiles.
- **First-time download**: ~1.1 GB through the Hugging Face hub.
  Use the `weights` sub-command of [`run.sh`](../run.sh) to download.

## Reading
- Stringer et al., 2020 — *Cellpose: a generalist algorithm for cellular
  segmentation* (Nature Methods).
- Pachitariu & Stringer, 2022 — *Cellpose 2.0: how to train your own
  model* (Nature Methods).
- Cellpose v4 release notes:
  https://github.com/MouseLand/cellpose
