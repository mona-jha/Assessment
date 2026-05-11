# 09 — Morphometrics: what every column in the CSV means

This file is a glossary for [`results/<method>/per_image_stats.csv`](../results/classical/per_image_stats.csv).

| Column                  | Unit / range            | Meaning                                                                 |
|-------------------------|-------------------------|-------------------------------------------------------------------------|
| `cohort`                | string                  | One of BRC, CRC, HCC, NSCLC_AD, NSCLC_SCC                              |
| `image`                 | string                  | Source filename, e.g. `Image3.png`                                      |
| `nucleus_count`         | integer                 | Number of detected nuclei in the image                                  |
| `mean_area_px`          | px²                     | Mean nucleus area                                                       |
| `median_area_px`        | px²                     | Median nucleus area (more robust to a few merged blobs)                 |
| `std_area_px`           | px²                     | Standard deviation of nucleus areas                                     |
| `mean_eccentricity`     | 0 – 1                   | 0 = perfect circle, → 1 = highly elongated                              |
| `mean_solidity`         | 0 – 1                   | area / convex_hull_area; 1 = perfectly convex                           |
| `density_per_megapixel` | nuclei per Mpx of image | Count divided by (image_height × image_width / 1,000,000)               |

## Why these specific columns

### `nucleus_count`
The headline number. Without GT, this is what we cross-validate between
methods.

### Area (mean / median / std)
- **Mean** is sensitive to outliers (one merged 4000-px blob skews it).
- **Median** is robust.
- **Std** tells us how *uniform* the population is — small std means
  the cohort has a tightly distributed nucleus size (e.g. NSCLC_SCC).

### `mean_eccentricity`

Eccentricity of a region's best-fit ellipse:

$$
\varepsilon = \sqrt{1 - \frac{b^2}{a^2}}
$$

where $a$ is the semi-major and $b$ the semi-minor axis.

- $\varepsilon = 0$: circle.
- $\varepsilon \to 1$: highly elongated.

Real nucleus values typically fall in 0.5–0.85. Higher values per cohort
suggest more elongated nuclei or worse segmentation merging two nuclei
into one elongated blob.

### `mean_solidity`

$$
\text{solidity} = \frac{\text{region area}}{\text{convex hull area}}
$$

A nucleus is roughly elliptical → highly convex → solidity near 1
(typically 0.92–0.96).

We use solidity as a **filter** in the classical pipeline: anything with
solidity < 0.70 is almost certainly a stromal artefact, vessel
fragment, or fragmented region. This filter dropped a meaningful number
of false positives in early experiments.

### `density_per_megapixel`

$$
\text{density} = \frac{\text{count}}{\text{image area in megapixels}}
$$

Density is the **only count metric that is comparable across images of
different sizes**. The 50 images aren't exactly the same shape; reporting
raw count would be misleading. Density is in "nuclei per megapixel of
slide tissue" — typical values 1,000–2,500 in our dataset.

## What does a "normal" set of values look like?

For BRC `Image1.png` (classical pipeline):

| Stat                  | Value      |
|-----------------------|------------|
| nucleus_count         | 577        |
| mean_area_px          | 81 px²     |
| median_area_px        | 71 px²     |
| std_area_px           | 39 px²     |
| mean_eccentricity     | 0.65       |
| mean_solidity         | 0.94       |
| density_per_megapixel | 2,071      |

Median < mean (some larger merged blobs pulling the mean up), high
solidity, mid-range eccentricity — all consistent with healthy
breast-carcinoma nuclei.

## Per-cohort headline numbers (classical, mean per image)

| Cohort     | Count | Mean area | Eccentricity | Solidity | Density / Mpx |
|------------|-------|-----------|--------------|----------|----------------|
| BRC        | 570   | 117       | 0.66         | 0.93     | 2,048          |
| CRC        | 539   | 130       | 0.70         | 0.93     | 1,935          |
| HCC        | 356   | 118       | 0.72         | 0.93     | 1,279          |
| NSCLC_AD   | 460   |  96       | 0.71         | 0.92     | 1,652          |
| NSCLC_SCC  | 499   |  80       | 0.67         | 0.94     | 1,792          |

## Code reference
[`code/features.py`](../code/features.py) — function `extract_features`
computes every column from a `regionprops` list.

## Other regionprops you could add (we didn't, but you might)

scikit-image's `regionprops` returns ~40 properties per region. We
subset to the 7 most informative for nucleus analysis. Here are the
ones we considered but did not include, and why:

| Property                  | Why we omitted it                                |
|---------------------------|--------------------------------------------------|
| `perimeter`               | Strongly correlated with area; redundant.        |
| `equivalent_diameter`     | Just a transformation of area.                   |
| `major_axis_length`       | Captured by eccentricity + area.                 |
| `minor_axis_length`       | Same.                                            |
| `extent`                  | (area / bbox area) — noisy on small regions.     |
| `feret_diameter_max`      | Useful for elongated cells — left for HoVer-Net. |
| `intensity_mean` / `intensity_std` | Requires intensity image; cohort-comparable only after stain normalisation. |

If a future iteration wanted **nucleus-level** classification (tumour
vs lymphocyte) we'd add `intensity_mean` of the H channel — lymphocytes
stain darker.

## How to read the per-image CSV

A single row from `results/classical/per_image_stats.csv`:

```
cohort,image,nucleus_count,mean_area_px,median_area_px,std_area_px,mean_eccentricity,mean_solidity,density_per_megapixel
BRC,Image1.png,577,81,71,39,0.65,0.94,2071
```

Reading: "BRC Image1 has 577 nuclei with mean area 81 px² (median 71,
so the distribution has a tail of larger blobs), mean eccentricity 0.65
(modestly elongated), and density 2,071 nuclei per megapixel."

## Aggregation up to the cohort level

The per-cohort summary (`results/per_cohort_summary.csv`) is built by
`code/03_make_report_figures.py`:

```python
perc = df.groupby(["method", "cohort"]).agg(
    total_count        = ("nucleus_count",         "sum"),
    mean_count         = ("nucleus_count",         "mean"),
    std_count          = ("nucleus_count",         "std"),
    mean_area          = ("mean_area_px",          "mean"),
    mean_eccentricity  = ("mean_eccentricity",     "mean"),
    mean_solidity      = ("mean_solidity",         "mean"),
    mean_density       = ("density_per_megapixel", "mean"),
).round(2).reset_index()
```

Aggregating by mean of *means* is the right thing here because each
image is a sample of the cohort — we want "average per-image behaviour",
not "weighted by nucleus count".
