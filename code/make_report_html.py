"""
make_report_html.py
===================
Build report/report.html — a self-contained, professionally styled HTML
report with embedded figures, tables, and interactive elements.

    python code/make_report_html.py

All images are base64-encoded inline so the HTML file is fully portable
(no broken image links when shared).

Author: Mona Kumari
"""
from __future__ import annotations

import base64
from pathlib import Path

from config import RESULTS_DIR, FIGURES_DIR

ROOT = Path(__file__).resolve().parent.parent
HTML_OUT = ROOT / "report" / "report.html"

AUTHOR = "Mona Kumari"
DATE = "May 2026"


def _img_b64(path: Path) -> str:
    """Return a data-URI string for an image file."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    suffix = path.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "svg": "image/svg+xml"}.get(suffix, "image/png")
    return f"data:{mime};base64,{b64}"


def _read_csv_html(path: Path, classes: str = "") -> str:
    """Read a CSV and return an HTML table string."""
    import pandas as pd
    df = pd.read_csv(path)
    # Round floats for display
    for col in df.select_dtypes(include="float").columns:
        df[col] = df[col].round(1)
    cls = f' class="{classes}"' if classes else ""
    return df.to_html(index=False, classes=classes, border=0)


CSS = """
:root {
    --primary: #0B3D5C;
    --secondary: #1B6E8F;
    --accent: #E26D2C;
    --light-bg: #F5F7FA;
    --body-text: #222B33;
    --muted: #555C66;
    --border: #D0D5DC;
    --gold: #F59527;
}
* { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    color: var(--body-text);
    background: #fff;
    line-height: 1.7;
    font-size: 15px;
}

/* ─── Cover ─── */
.cover {
    background: linear-gradient(135deg, var(--primary) 0%, #0A2045 60%, #283C4D 100%);
    color: #fff;
    padding: 80px 60px;
    min-height: 400px;
    position: relative;
    overflow: hidden;
}
.cover::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(245,149,39,0.15) 0%, transparent 70%);
    border-radius: 50%;
}
.cover .label {
    font-size: 13px;
    letter-spacing: 3px;
    text-transform: uppercase;
    opacity: 0.7;
    margin-bottom: 20px;
}
.cover h1 {
    font-size: 42px;
    font-weight: 300;
    line-height: 1.2;
    margin-bottom: 12px;
    max-width: 700px;
}
.cover .subtitle {
    font-size: 18px;
    color: var(--gold);
    margin-bottom: 30px;
}
.cover .meta {
    font-size: 14px;
    opacity: 0.7;
}
.cover .accent-bar {
    position: absolute;
    left: 0; top: 0;
    width: 6px; height: 100%;
    background: var(--gold);
}

/* ─── Layout ─── */
.container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 40px 40px 80px;
}

/* ─── TOC ─── */
.toc {
    background: var(--light-bg);
    border-left: 4px solid var(--accent);
    padding: 24px 30px;
    margin: 30px 0 40px;
    border-radius: 0 8px 8px 0;
}
.toc h2 { font-size: 16px; color: var(--primary); margin-bottom: 12px; }
.toc ol { padding-left: 20px; }
.toc li { margin: 6px 0; }
.toc a {
    color: var(--secondary);
    text-decoration: none;
    font-weight: 500;
}
.toc a:hover { text-decoration: underline; }

/* ─── Headings ─── */
h2 {
    color: var(--primary);
    font-size: 26px;
    font-weight: 700;
    margin: 50px 0 16px;
    padding-bottom: 8px;
    border-bottom: 3px solid var(--accent);
}
h3 {
    color: var(--secondary);
    font-size: 20px;
    font-weight: 600;
    margin: 36px 0 12px;
}

/* ─── Paragraphs ─── */
p { margin: 12px 0; }

/* ─── Tables ─── */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 14px;
}
thead th {
    background: var(--primary);
    color: #fff;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.3px;
}
tbody td {
    padding: 9px 14px;
    border-bottom: 1px solid var(--border);
}
tbody tr:nth-child(even) { background: var(--light-bg); }
tbody tr:hover { background: #E8EDF2; }

/* ─── Highlight / impact table ─── */
table.impact thead th { background: var(--accent); }
table.impact td:last-child { font-weight: 700; }

/* ─── Figures ─── */
.figure {
    margin: 30px 0;
    text-align: center;
}
.figure img {
    max-width: 100%;
    border-radius: 6px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.figure .caption {
    font-size: 13px;
    color: var(--muted);
    margin-top: 8px;
    font-style: italic;
}

/* ─── Info boxes ─── */
.box {
    border-radius: 8px;
    padding: 18px 22px;
    margin: 20px 0;
}
.box-insight {
    background: linear-gradient(135deg, #EBF5FB 0%, #D6EAF8 100%);
    border-left: 4px solid var(--secondary);
}
.box-warning {
    background: #FFF8E1;
    border-left: 4px solid var(--accent);
}
.box h4 {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 6px;
    color: var(--primary);
}

/* ─── Code ─── */
pre {
    background: #1E293B;
    color: #E2E8F0;
    padding: 18px 22px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.6;
    margin: 16px 0;
}
code {
    background: var(--light-bg);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    color: var(--primary);
}
pre code { background: none; padding: 0; color: inherit; }

/* ─── Cards grid ─── */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin: 20px 0;
}
.card {
    background: var(--light-bg);
    border-radius: 8px;
    padding: 20px;
    border-top: 3px solid var(--secondary);
}
.card h4 {
    color: var(--primary);
    font-size: 15px;
    margin-bottom: 8px;
}
.card p { font-size: 14px; color: var(--muted); margin: 0; }

/* ─── Stats row ─── */
.stats-row {
    display: flex;
    gap: 16px;
    margin: 20px 0;
    flex-wrap: wrap;
}
.stat-card {
    flex: 1;
    min-width: 150px;
    background: var(--primary);
    color: #fff;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}
.stat-card .number {
    font-size: 32px;
    font-weight: 700;
    color: var(--gold);
}
.stat-card .label {
    font-size: 12px;
    opacity: 0.8;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ─── Pipeline steps ─── */
.pipeline {
    display: flex;
    gap: 0;
    margin: 20px 0;
    flex-wrap: wrap;
    align-items: stretch;
}
.pipeline .step {
    flex: 1;
    min-width: 120px;
    background: var(--light-bg);
    padding: 14px 16px;
    text-align: center;
    font-size: 13px;
    position: relative;
    border: 1px solid var(--border);
}
.pipeline .step:first-child { border-radius: 8px 0 0 8px; }
.pipeline .step:last-child { border-radius: 0 8px 8px 0; }
.pipeline .step .num {
    display: inline-block;
    background: var(--secondary);
    color: #fff;
    width: 22px; height: 22px;
    border-radius: 50%;
    font-size: 12px;
    line-height: 22px;
    margin-bottom: 4px;
}
.pipeline .step strong { display: block; font-size: 12px; color: var(--primary); }

/* ─── Footer ─── */
.footer {
    background: var(--primary);
    color: rgba(255,255,255,0.7);
    text-align: center;
    padding: 20px;
    font-size: 13px;
}

/* ─── Print ─── */
@media print {
    .cover { min-height: auto; padding: 40px; }
    .container { padding: 20px; }
    body { font-size: 12px; }
}
"""


def build_html():
    fig_paths = {
        "qual_classical": FIGURES_DIR / "01_qualitative_grid_classical.png",
        "count_cohort":   FIGURES_DIR / "02_count_by_cohort.png",
        "area_cohort":    FIGURES_DIR / "03_area_by_cohort.png",
        "density_cohort": FIGURES_DIR / "04_density_by_cohort.png",
        "count_scatter":  FIGURES_DIR / "05_method_count_scatter.png",
        "qual_cross":     FIGURES_DIR / "06_method_qualitative_grid.png",
        "fpfn_grid":      FIGURES_DIR / "07_fpfn_grid.png",
        "fpfn_bar":       FIGURES_DIR / "08_fpfn_counts_bar.png",
        "fpfn_cohort":    FIGURES_DIR / "09_fpfn_cohort_bar.png",
    }

    # Pre-encode all figures
    figs = {k: _img_b64(v) for k, v in fig_paths.items() if v.exists()}

    # Pick a sample overlay from each method for visual comparison
    sample_overlays = {}
    for method in ["classical", "cellpose", "stardist"]:
        p = RESULTS_DIR / method / "overlays" / "CRC_Image1_overlay.png"
        if p.exists():
            sample_overlays[method] = _img_b64(p)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nucleus Detection &amp; Quantification — Report</title>
<style>{CSS}</style>
</head>
<body>

<!-- ═══════════ COVER ═══════════ -->
<div class="cover">
    <div class="accent-bar"></div>
    <div class="label">Syngene / BBRC Digital Pathology Assessment</div>
    <h1>Nucleus Detection &amp; Quantification</h1>
    <div class="subtitle">on H&amp;E Histopathology Images — 5 Cancer Cohorts × 3 Methods</div>
    <div class="meta">{AUTHOR} · {DATE}</div>
</div>

<div class="container">

<!-- ═══════════ TOC ═══════════ -->
<div class="toc">
    <h2>Contents</h2>
    <ol>
        <li><a href="#problem">Problem Statement</a></li>
        <li><a href="#dataset">Dataset</a></li>
        <li><a href="#preprocessing">Preprocessing: Macenko Stain Normalisation</a></li>
        <li><a href="#methods">Approach: Three Independent Methods</a></li>
        <li><a href="#results">Results</a></li>
        <li><a href="#biology">Cross-Cohort Biological Interpretation</a></li>
        <li><a href="#limitations">Limitations</a></li>
        <li><a href="#improvements">Possible Improvements</a></li>
        <li><a href="#reproducibility">Reproducibility</a></li>
    </ol>
</div>

<!-- ═══════════ 1. PROBLEM ═══════════ -->
<h2 id="problem">1. Problem Statement</h2>
<p>
    Detect and quantify <strong>every nucleus</strong> in 50 H&amp;E-stained histopathology
    images spanning five cancer cohorts. No ground-truth annotations are provided, so the
    focus is on a robust, reproducible pipeline plus <strong>method agreement</strong> as
    a proxy for correctness.
</p>

<div class="stats-row">
    <div class="stat-card">
        <div class="number">50</div>
        <div class="label">Images</div>
    </div>
    <div class="stat-card">
        <div class="number">5</div>
        <div class="label">Cancer Cohorts</div>
    </div>
    <div class="stat-card">
        <div class="number">3</div>
        <div class="label">Methods</div>
    </div>
    <div class="stat-card">
        <div class="number">~6 min</div>
        <div class="label">Total Runtime</div>
    </div>
</div>

<!-- ═══════════ 2. DATASET ═══════════ -->
<h2 id="dataset">2. Dataset</h2>
<table>
<thead>
    <tr><th>Cohort</th><th>Tissue / Disease</th><th>Images</th></tr>
</thead>
<tbody>
    <tr><td><strong>BRC</strong></td><td>Breast carcinoma</td><td>10</td></tr>
    <tr><td><strong>CRC</strong></td><td>Colorectal carcinoma</td><td>10</td></tr>
    <tr><td><strong>HCC</strong></td><td>Hepatocellular carcinoma</td><td>10</td></tr>
    <tr><td><strong>NSCLC_AD</strong></td><td>Non-small-cell lung carcinoma — adenocarcinoma</td><td>10</td></tr>
    <tr><td><strong>NSCLC_SCC</strong></td><td>Non-small-cell lung carcinoma — squamous cell</td><td>10</td></tr>
</tbody>
</table>
<p>
    Each image is an RGB PNG (~480 × 560 px). Nuclei stain blue/purple (hematoxylin)
    on a pink eosin background, with substantial variation in cellularity, stain
    intensity, and tissue architecture across cohorts.
</p>

<!-- ═══════════ 3. PREPROCESSING ═══════════ -->
<h2 id="preprocessing">3. Preprocessing: Macenko Stain Normalisation</h2>
<p>
    H&amp;E images from different slides / scanners show substantial colour variation.
    Before segmentation, every image is normalised to a fixed reference
    (<code>BRC/Image1.png</code>) using the Macenko method
    (Macenko et al., ISBI 2009). Implementation is pure numpy/scipy SVD —
    no external stain-normalisation library needed.
</p>

<h3>Impact on Nucleus Counts</h3>
<table class="impact">
<thead>
    <tr><th>Method</th><th>Without Norm.</th><th>With Norm.</th><th>Δ</th></tr>
</thead>
<tbody>
    <tr><td>Classical</td><td>24,250</td><td>15,497</td><td>−36%</td></tr>
    <tr><td>Cellpose</td><td>24,097</td><td>24,194</td><td>+0.4%</td></tr>
    <tr><td>StarDist</td><td>20,783</td><td>14,732</td><td>−29%</td></tr>
</tbody>
</table>

<div class="box box-insight">
    <h4>Key Insight</h4>
    <p>
        <strong>Cellpose is essentially stain-invariant</strong> (+0.4% change) — it learned
        stain robustness from diverse training data. The classical HED pipeline (−36%) and
        StarDist (−29%) are highly sensitive to stain appearance. Normalisation removes
        spurious detections in over-stained regions, giving more conservative and reliable counts.
    </p>
</div>

<p>
    All results below use Macenko-normalised input. The raw (un-normalised) results are
    preserved in git history (commit <code>74c75b2</code>) for comparison.
</p>

<!-- ═══════════ 4. METHODS ═══════════ -->
<h2 id="methods">4. Approach: Three Independent Methods</h2>
<p>
    Because there is no manual ground truth, we run <strong>three methods of different
    families</strong> and use their agreement as evidence of correctness.
</p>

<div class="card-grid">
    <div class="card" style="border-top-color: var(--accent);">
        <h4>Classical (HED + Watershed)</h4>
        <p>Transparent image processing — no training data needed. HED stain
        deconvolution → Otsu → morphology → watershed instance splitting.</p>
    </div>
    <div class="card" style="border-top-color: var(--secondary);">
        <h4>Cellpose v4 (cpsam)</h4>
        <p>Generalist DL model. Pretrained flow-based segmentation, robust across
        tissue types. ~6 s/image on Apple MPS.</p>
    </div>
    <div class="card" style="border-top-color: var(--primary);">
        <h4>StarDist (2D_versatile_he)</h4>
        <p>H&amp;E-specific DL. Trained on H&amp;E nuclei with star-convex polygon
        prior. Conservative but precise.</p>
    </div>
</div>

<h3>Classical Pipeline Steps</h3>
<div class="pipeline">
    <div class="step"><span class="num">1</span><strong>HED Deconv.</strong>Keep H channel</div>
    <div class="step"><span class="num">2</span><strong>Clip + Blur</strong>1–99% + σ=1</div>
    <div class="step"><span class="num">3</span><strong>Otsu Thresh.</strong>Binary mask</div>
    <div class="step"><span class="num">4</span><strong>Morphology</strong>Open, fill, clean</div>
    <div class="step"><span class="num">5</span><strong>Watershed</strong>Split clumps</div>
    <div class="step"><span class="num">6</span><strong>Filter</strong>Area, solidity</div>
</div>

<!-- ═══════════ 5. RESULTS ═══════════ -->
<h2 id="results">5. Results</h2>

<h3>5.1 Total Nuclei Detected (with Macenko Normalisation)</h3>
<table>
<thead>
    <tr><th>Method</th><th>Total</th><th>BRC</th><th>CRC</th><th>HCC</th><th>NSCLC_AD</th><th>NSCLC_SCC</th></tr>
</thead>
<tbody>
    <tr><td><strong>Classical</strong></td><td><strong>15,497</strong></td><td>2,015</td><td>3,671</td><td>3,314</td><td>3,266</td><td>3,231</td></tr>
    <tr><td><strong>Cellpose</strong></td><td><strong>24,194</strong></td><td>4,879</td><td>5,889</td><td>3,568</td><td>4,572</td><td>5,286</td></tr>
    <tr><td><strong>StarDist</strong></td><td><strong>14,732</strong></td><td>3,459</td><td>3,645</td><td>1,934</td><td>2,548</td><td>3,146</td></tr>
</tbody>
</table>

<h3>5.2 Per-Cohort Summary (Classical)</h3>
<table>
<thead>
    <tr><th>Cohort</th><th>Total</th><th>Count Mean ± Std</th><th>Mean Area (px²)</th><th>Density / Mpx</th></tr>
</thead>
<tbody>
    <tr><td>BRC</td><td>2,015</td><td>202 ± 165</td><td>60</td><td>723</td></tr>
    <tr><td>CRC</td><td>3,671</td><td>367 ± 165</td><td>76</td><td>1,318</td></tr>
    <tr><td>HCC</td><td>3,314</td><td>331 ± 127</td><td>201</td><td>1,190</td></tr>
    <tr><td>NSCLC_AD</td><td>3,266</td><td>327 ± 43</td><td>118</td><td>1,173</td></tr>
    <tr><td>NSCLC_SCC</td><td>3,231</td><td>323 ± 150</td><td>93</td><td>1,160</td></tr>
</tbody>
</table>

<h3>5.3 Method Agreement (Mean Foreground-Mask IoU)</h3>
<table>
<thead>
    <tr><th>Cohort</th><th>Classical vs Cellpose</th><th>Classical vs StarDist</th><th>Cellpose vs StarDist</th></tr>
</thead>
<tbody>
    <tr><td>BRC</td><td>0.21</td><td>0.29</td><td>0.36</td></tr>
    <tr><td>CRC</td><td>0.39</td><td>0.37</td><td>0.44</td></tr>
    <tr><td>HCC</td><td>0.13</td><td>0.29</td><td>0.17</td></tr>
    <tr><td>NSCLC_AD</td><td>0.28</td><td>0.30</td><td>0.36</td></tr>
    <tr><td>NSCLC_SCC</td><td>0.25</td><td>0.29</td><td>0.40</td></tr>
</tbody>
</table>

<div class="box box-insight">
    <h4>Agreement Note</h4>
    <p>
        Cellpose–StarDist agreement is consistently highest across cohorts. Both DL methods
        share a more refined notion of "nucleus" than the classical pipeline. The lower absolute
        IoU values (compared to without normalisation) are expected: normalisation removed many
        false positives, so the methods now disagree more on <em>which</em> specific pixels are nuclear.
    </p>
</div>

<h3>5.4 Visual Results</h3>

<div class="figure">
    <img src="{figs.get('qual_classical', '')}" alt="Qualitative grid — classical">
    <div class="caption">Figure 1. Classical pipeline: one sample overlay per cohort showing detected nuclei (coloured contours).</div>
</div>

<div class="figure">
    <img src="{figs.get('qual_cross', '')}" alt="Cross-method qualitative">
    <div class="caption">Figure 2. Same image processed by all three methods — visual comparison of segmentation quality.</div>
</div>

<h3>5.5 Sample Overlays — Method Comparison (CRC Image 1)</h3>
<div class="card-grid">
    {"".join(f'''
    <div class="card" style="padding: 10px; text-align: center; border-top-color: var(--accent);">
        <img src="{uri}" alt="{method} overlay" style="width:100%; border-radius:4px;">
        <h4 style="margin-top:8px;">{method.title()}</h4>
    </div>''' for method, uri in sample_overlays.items())}
</div>

<h3>5.6 Quantitative Charts</h3>

<div class="figure">
    <img src="{figs.get('count_cohort', '')}" alt="Count by cohort">
    <div class="caption">Figure 3. Nucleus count distribution by cohort, all three methods.</div>
</div>

<div class="figure">
    <img src="{figs.get('count_scatter', '')}" alt="Per-image count scatter">
    <div class="caption">Figure 4. Per-image count agreement: classical (x) vs DL methods (y). Points near y=x = good agreement.</div>
</div>

<div class="figure">
    <img src="{figs.get('area_cohort', '')}" alt="Area by cohort">
    <div class="caption">Figure 5. Mean nuclear area (px²) by cohort.</div>
</div>

<div class="figure">
    <img src="{figs.get('density_cohort', '')}" alt="Density by cohort">
    <div class="caption">Figure 6. Nuclear density (nuclei per megapixel) by cohort.</div>
</div>

<!-- ═══════════ 5.7 FP/FN ANALYSIS ═══════════ -->
<h3>5.7 False Positive / False Negative Analysis</h3>
<p>
    Without ground truth, we estimate FPs and FNs using <strong>cross-method consensus</strong>:
    a pixel is considered a "true" nucleus if <strong>≥2 of 3 methods agree</strong>.
    Detections unique to one method are <span style="color:#E74C3C;font-weight:bold;">FP-like</span>;
    consensus nuclei missed by a method are <span style="color:#3498DB;font-weight:bold;">FN-like</span>.
</p>

<div class="box box-warning">
    <h4>Caveat</h4>
    <p>
        This is a <em>proxy</em> for FP/FN, not ground truth. Majority vote can be wrong
        (e.g. if two methods share the same bias). Still, it is the best available
        estimator without manual annotations.
    </p>
</div>

<div class="figure">
    <img src="{figs.get('fpfn_grid', '')}" alt="FP/FN analysis grid">
    <div class="caption">Figure 7. FP/FN overlay per cohort × method.
        <span style="color:#2ECC71;">■</span> Agreed nucleus (TP-like) &nbsp;
        <span style="color:#E74C3C;">■</span> Only this method (FP-like) &nbsp;
        <span style="color:#3498DB;">■</span> Missed by this method (FN-like)</div>
</div>

<div class="figure">
    <img src="{figs.get('fpfn_bar', '')}" alt="FP/FN pixel counts">
    <div class="caption">Figure 8. Total pixel-level FP-like and FN-like counts per method.</div>
</div>

<div class="card-grid">
    <div class="card" style="border-top-color: #E74C3C;">
        <h4>Cellpose: Highest FP-like (33.6%)</h4>
        <p>Detects the most nuclei overall — many are unique to Cellpose and not confirmed
        by the other two methods. High sensitivity, lower specificity.</p>
    </div>
    <div class="card" style="border-top-color: #3498DB;">
        <h4>Classical: Highest FN-like (26.2%)</h4>
        <p>Misses the most consensus nuclei — particularly small, faint lymphocytes that
        the DL methods detect. HED deconvolution threshold is too aggressive on dim nuclei.</p>
    </div>
    <div class="card" style="border-top-color: #2ECC71;">
        <h4>StarDist: Best TP-like Rate (60.9%)</h4>
        <p>Highest agreement with consensus. Conservative polygon prior means fewer
        unique detections (FP) and fewer misses (FN). Best precision-recall balance.</p>
    </div>
</div>

<div class="figure">
    <img src="{figs.get('fpfn_cohort', '')}" alt="Per-cohort FP/FN rates">
    <div class="caption">Figure 9. Per-cohort FP/FN rates by method. HCC shows highest disagreement
        across all methods — large hepatocytes are segmented very differently by each approach.</div>
</div>

<div class="box box-insight">
    <h4>Key Takeaway</h4>
    <p>
        <strong>StarDist has the best overall agreement with consensus</strong> (60.9% TP-like pixels).
        Cellpose detects the most nuclei but 33.6% are unique to it — these may be real nuclei
        that only Cellpose's generalist model can see, or they may be over-detections.
        Without ground truth, we cannot distinguish. The recommendation: if you need
        <em>high recall</em>, use Cellpose; if you need <em>high precision</em>, use StarDist.
    </p>
</div>

<!-- ═══════════ 6. BIOLOGY ═══════════ -->
<h2 id="biology">6. Cross-Cohort Biological Interpretation</h2>

<div class="card-grid">
    <div class="card">
        <h4>HCC — Lowest Density</h4>
        <p>Large hepatocytes with abundant cytoplasm → fewer nuclei per unit tissue area. All 3 methods agree.</p>
    </div>
    <div class="card">
        <h4>CRC — Highest Counts</h4>
        <p>Dense glandular architecture with prominent lymphocytic infiltrate drives up nuclear density.</p>
    </div>
    <div class="card">
        <h4>NSCLC_SCC — Smallest Nuclei</h4>
        <p>Mean area ≈ 93 px². Dense, monomorphic squamous nests typical of squamous-cell carcinoma.</p>
    </div>
    <div class="card">
        <h4>NSCLC_AD — Tightest Variance</h4>
        <p>Count std ≈ 43 (classical). Relatively uniform adenocarcinoma glands lined by cuboidal/columnar cells.</p>
    </div>
    <div class="card">
        <h4>BRC — Most Affected by Normalisation</h4>
        <p>Classical: 5,704 → 2,015 (−65%). Widest stain variability; normalisation exposed false positives from over-stained eosinophilic regions.</p>
    </div>
</div>

<!-- ═══════════ 7. LIMITATIONS ═══════════ -->
<h2 id="limitations">7. Limitations</h2>
<div class="card-grid">
    <div class="card" style="border-top-color: var(--accent);">
        <h4>No Ground Truth</h4>
        <p>We report morphometrics and cross-method agreement, not precision/recall. Manual annotation would close this gap.</p>
    </div>
    <div class="card" style="border-top-color: var(--accent);">
        <h4>Watershed Over-segmentation</h4>
        <p>Classical pipeline can split very large nuclei (e.g. hepatocytes in HCC). DL methods suffer less.</p>
    </div>
    <div class="card" style="border-top-color: var(--accent);">
        <h4>StarDist Conservatism</h4>
        <p>Polygon prior misses non-convex / overlapping nuclei even at lowered prob_thresh = 0.40.</p>
    </div>
    <div class="card" style="border-top-color: var(--accent);">
        <h4>Reference Sensitivity</h4>
        <p>Macenko normalised output depends on reference image choice. A different reference may shift counts.</p>
    </div>
</div>

<!-- ═══════════ 8. IMPROVEMENTS ═══════════ -->
<h2 id="improvements">8. Possible Improvements</h2>
<table>
<thead>
    <tr><th>Improvement</th><th>What It Unlocks</th></tr>
</thead>
<tbody>
    <tr><td><strong>HoVer-Net</strong></td><td>Joint segmentation + cell-type classification (epithelial / lymphocyte / stromal)</td></tr>
    <tr><td><strong>Manual annotation (~5 crops/cohort)</strong></td><td>Real F1 / panoptic-quality metrics for each method</td></tr>
    <tr><td><strong>Reinhard normalisation</strong></td><td>Compare alternative preprocessing; ensemble both approaches</td></tr>
    <tr><td><strong>Hungarian-matched instance IoU</strong></td><td>Per-nucleus correspondence between methods (not just foreground)</td></tr>
    <tr><td><strong>Method ensemble</strong></td><td>Union + NMS → single consensus mask, likely more accurate than any individual</td></tr>
    <tr><td><strong>Whole-slide tiling</strong></td><td>Scale from 480×560 ROIs to gigapixel WSIs</td></tr>
</tbody>
</table>

<!-- ═══════════ 9. REPRODUCIBILITY ═══════════ -->
<h2 id="reproducibility">9. Reproducibility</h2>
<pre><code># 1. Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_deeplearning.txt   # optional (DL methods)

# 2. Pretrained weights (one-time download)
#    ~/.cellpose/models/cpsam              (~1.1 GB)
#    ~/.stardist/models/2D_versatile_he/   (~5 MB)

# 3. Run all three methods
python code/01_run_segmentation.py --method classical    # ~18 s
python code/01_run_segmentation.py --method stardist     # ~40 s
python code/01_run_segmentation.py --method cellpose     # ~5 min (MPS)

# 4. Analysis + figures
python code/02_compare_methods.py
python code/03_make_report_figures.py

# 5. Or use the one-command reproducer:
./run.sh all</code></pre>

<div class="box box-warning">
    <h4>Git History Contains Both Result Sets</h4>
    <p>
        Without normalisation: commit <code>74c75b2</code><br>
        With normalisation: current <code>HEAD</code><br>
        Compare: <code>git diff 74c75b2 HEAD -- results/*/per_image_stats.csv</code>
    </p>
</div>

</div><!-- container -->

<div class="footer">
    {AUTHOR} · Syngene / BBRC Digital Pathology Assessment · {DATE}
</div>

</body>
</html>"""

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(html, encoding="utf-8")
    size_kb = HTML_OUT.stat().st_size / 1024
    print(f"Wrote {HTML_OUT}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    build_html()
