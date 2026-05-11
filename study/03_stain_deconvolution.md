# 03 — Stain deconvolution (HED) deep dive

## Why we cannot just grayscale
Pathologists look at H&E in **colour** because the colour encodes which
biological structure is which. If we collapse to grayscale, a dark blue
nucleus and a dark pink piece of stroma can have the *same* intensity.
We lose the structural information we need.

## The Beer-Lambert idea
Light passes through stained tissue and is absorbed. The fraction of
light reaching the camera at each colour channel depends on:

1. how much of each dye is at that pixel,
2. how much each dye absorbs at each colour channel.

Mathematically, for a pixel with red/green/blue transmitted intensities
$I_R, I_G, I_B$ and incident intensity $I_0$ (typically $\approx 255$):

$$
\text{OD}_c = -\log_{10}\!\left(\frac{I_c}{I_0}\right) \quad \text{for } c \in \{R, G, B\}
$$

OD ("optical density") is what actually combines linearly with stain
amounts (transmitted intensity does not).

Stack the three OD values into a vector $\mathbf{y} \in \mathbb{R}^3$:

$$
\mathbf{y} = M \,\mathbf{x}
$$

where $\mathbf{x} \in \mathbb{R}^3$ is the unknown amounts of
(Hematoxylin, Eosin, DAB) at that pixel and $M$ is the **stain matrix**:
each column is the characteristic OD of pure unit-amount of that dye in
RGB.

For standard H&E (with a residual DAB column for completeness),
the canonical Ruifrok–Johnston matrix is hard-coded in scikit-image as
`hed_from_rgb`.

## Inverting it
If $M$ is invertible:

$$
\mathbf{x} = M^{-1}\,\mathbf{y}
$$

That single matrix–vector multiply per pixel is **stain deconvolution**.
The output channel $\mathbf{x}_H$ is the per-pixel "amount of
Hematoxylin" — a clean, nucleus-specific grayscale image.

## What `skimage.color.rgb2hed` actually does

```python
from skimage.color import rgb2hed
hed = rgb2hed(rgb)        # shape HxWx3, channels = (H, E, DAB)
h = hed[..., 0]           # the Hematoxylin (nucleus) channel
```

Internally, scikit-image:
1. Adds a tiny epsilon to avoid `log(0)`.
2. Computes OD per channel.
3. Multiplies by the inverse stain matrix.

Output is float in roughly $[-0.5, 1.0]$ — values can be slightly
negative because of noise / non-physical pixels. We robust-stretch to
$[0, 1]$ before thresholding:

```python
import numpy as np
lo, hi = np.percentile(h, [1, 99])
h = np.clip((h - lo) / (hi - lo + 1e-8), 0, 1)
```

## Why this is better than "just take the blue channel"
- **Pure blue channel** is contaminated by anything that scatters blue
  light: clear backgrounds, glass, very pale eosin areas.
- **Hematoxylin channel** specifically isolates the dye of interest.
  Whatever is not hematoxylin gets pushed close to zero by the inverse
  matrix.

You can see this experimentally in the qualitative figure: the H channel
shows nuclei as bright blobs on a near-black background, with cytoplasm
already suppressed.

## Limitations
- The standard stain matrix assumes "average" H&E. Extreme stain shifts
  (very weak hematoxylin, batch effects) can leak eosin signal into the
  H channel.
- **Stain normalisation** (Macenko 2009, Reinhard 2001) is the next
  step — it estimates a per-image $M$ from the data itself. Out of scope
  for this assessment but a clear future improvement.

## Code reference
Lines in [`code/method_classical.py`](../code/method_classical.py):

```python
def hematoxylin_channel(rgb, params=CLASSICAL):
    hed = color.rgb2hed(rgb)
    h = hed[..., 0]
    lo, hi = np.percentile(h, [params.h_percentile_lo, params.h_percentile_hi])
    h = np.clip((h - lo) / (hi - lo + 1e-8), 0.0, 1.0)
    return h.astype(np.float32)
```

## Worked example — a single pixel

Suppose a pixel has RGB intensities $(R, G, B) = (180, 95, 165)$, with
$I_0 = 255$. The optical densities are:

$$
\text{OD}_R = -\log_{10}(180/255) \approx 0.151
$$

$$
\text{OD}_G = -\log_{10}(95/255) \approx 0.428
$$

$$
\text{OD}_B = -\log_{10}(165/255) \approx 0.188
$$

Multiply by `hed_from_rgb` (the inverse stain matrix in scikit-image).
The Hematoxylin component comes out positive and large — the pixel is
mostly stained with hematoxylin. The Eosin component is small. That's
what the H channel will display as a bright value.

If you instead had $(R, G, B) = (240, 220, 230)$ — a near-white
background pixel — every OD is close to zero, so all three deconvolved
channels are close to zero. Background is correctly suppressed.

## What goes wrong without deconvolution

If you tried to segment on the **green channel** of the RGB image
(a common shortcut because green has the highest variance for H&E
stains), background and faintly-stained cytoplasm would have similar
intensity to faintly-stained nuclei. Otsu would split them poorly. We
verified this experimentally during prototyping: green-channel Otsu
produced ~30% more false positives in the dense BRC images.

## How to spot a deconvolution failure

If you save the H channel and see:
- **Pink stroma showing up as bright** — the stain matrix is wrong for
  this image (it was probably stained with a non-standard hematoxylin).
- **Many negative values** — OD values exceeded the assumed range; the
  image is too dark or has been pre-processed.
- **Very low contrast everywhere** — the slide is faintly stained;
  consider Macenko normalisation first.

In our 50 images none of these failure modes happened, but it's worth
knowing what to look for in production.

## Reading
- Ruifrok & Johnston, 2001 — *Quantification of histochemical staining
  by color deconvolution.* Anal. Quant. Cytol. Histol.
- Macenko et al., 2009 — *A method for normalizing histology slides for
  quantitative analysis.*
