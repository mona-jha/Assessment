# 01 — H&E staining basics

## Why H&E?
**Hematoxylin & Eosin (H&E)** is the standard histology stain — used on
essentially every diagnostic tissue slide in the world. It is cheap,
fast, and produces high-contrast images that pathologists are trained
to read.

## What each dye binds to

| Dye          | Colour       | Binds to                     | Highlights      |
|--------------|--------------|------------------------------|-----------------|
| Hematoxylin  | Blue/purple  | Nucleic acids (DNA, RNA)     | **Nuclei**      |
| Eosin        | Pink/red     | Basic proteins (cytoplasm, collagen) | Cytoplasm, stroma |

The two dyes are complementary: hematoxylin is *basic*, binds to
*acidic* DNA → blue nuclei. Eosin is *acidic*, binds to *basic*
cytoplasmic proteins → pink everything-else. The colour difference is
why segmentation is feasible at all.

## What this means for our pipeline
- The **blue/purple intensity** tells us where nuclei are.
- The **pink intensity** is mostly noise from our point of view (we want
  to suppress it).
- A simple grayscale conversion would *mix* both, losing the signal we
  want. We need **stain deconvolution** (see
  [03_stain_deconvolution.md](03_stain_deconvolution.md)) to extract a
  clean nuclei-only channel.

## Tissue you'll see in the 5 cohorts

| Cohort      | Visual cue                                                        |
|-------------|-------------------------------------------------------------------|
| BRC         | Heterogeneous: glandular structures + stroma + lymphocytes        |
| CRC         | Glandular crypts; abundant stroma; often dense lymphocytic cuffs  |
| HCC         | Large hepatocytes with abundant pink cytoplasm; sparse nuclei     |
| NSCLC_AD    | Glandular pattern with cuboidal/columnar cells lining lumens      |
| NSCLC_SCC   | Dense monomorphic squamous nests, small uniform nuclei            |

That biology directly explains our results: HCC has the lowest nucleus
density, NSCLC_SCC has the smallest and most uniform nuclei, etc. (See
[10_results_interpretation.md](10_results_interpretation.md).)

## Real-world H&E variability — and why it bites you
- **Stain intensity** varies between labs, batches, even slides in the
  same batch. Our pipeline mitigates this with percentile clipping and
  HED deconvolution.
- **Section thickness** changes nucleus appearance.
- **Out-of-focus regions** can blur boundaries.
- **Artefacts**: bubbles, dust, folded tissue.

The classical pipeline's `min_solidity ≥ 0.70` filter rejects most
artefacts; the DL methods are robust to them by training.

## Further reading
- Ruifrok & Johnston (2001), *Quantification of histochemical staining
  by color deconvolution* — the paper behind `skimage.color.rgb2hed`.
- Bancroft & Gamble, *Theory and Practice of Histological Techniques*
  (textbook) — the standard reference for staining chemistry.

## Key terms a pathologist would use

| Term            | Meaning                                                      |
|-----------------|--------------------------------------------------------------|
| Stroma          | Connective tissue (collagen + fibroblasts) supporting glands |
| Parenchyma      | The functional cells of an organ (epithelial in tumours)     |
| Lymphocyte      | Small immune cell with a small dense round nucleus           |
| Mitotic figure  | A nucleus in active division — distinctive shape             |
| Apoptotic body  | A nucleus that is fragmenting — also distinctive             |
| Pleomorphism    | Variation in nucleus size/shape — a malignancy clue          |
| Nuclear:cytoplasmic ratio | Nucleus area / cell area — high in many cancers     |

All of these affect what your segmentation "should" find. Our
pipelines are agnostic to these distinctions; HoVer-Net (a future-work
item) is the obvious next step if you wanted to classify nuclei by type.

## What "good" segmentation looks like, by tissue

- **HCC**: should detect ~250–400 large round nuclei per ROI; missing
  hepatocyte nuclei would be a clear failure.
- **NSCLC_SCC**: should produce a sea of small uniform circles;
  irregular shapes are usually wrong.
- **CRC**: must follow the curve of crypt linings; nuclei should be
  cigar-shaped, not round.
- **BRC**: heterogeneous; expect many lymphocytes (small, dense, round)
  alongside larger tumour cell nuclei.
- **NSCLC_AD**: similar gland linings to CRC but with smaller, more
  varied nuclei.

Knowing this lets you eyeball whether a method is working before any
IoU number is computed.
