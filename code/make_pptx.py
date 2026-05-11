"""
make_pptx.py
============
Build presentation/slides.pptx from the figures and tables already in
results/. Run this AFTER 02_compare_methods.py and 03_make_report_figures.py.

    python code/make_pptx.py

Design goals:
  - Consistent visual style: brand bar, footer with page numbers, palette.
  - Narrative on every slide -- not just bullet points.
  - Tables and figures embedded directly (no broken relative links).
  - 16:9 widescreen; readable on both projector and laptop.

Author: Mona Kumari
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

from config import RESULTS_DIR, FIGURES_DIR

ROOT = Path(__file__).resolve().parent.parent
PPT_OUT = ROOT / "presentation" / "slides.pptx"

# -- 16:9 widescreen ---------------------------------------------------------
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# -- Brand palette -----------------------------------------------------------
PRIMARY    = RGBColor(0x0B, 0x3D, 0x5C)   # deep teal/navy
SECONDARY  = RGBColor(0x1B, 0x6E, 0x8F)   # mid teal
ACCENT     = RGBColor(0xE2, 0x6D, 0x2C)   # warm orange
LIGHT_BG   = RGBColor(0xF5, 0xF7, 0xFA)   # near-white panel
BODY_TEXT  = RGBColor(0x22, 0x2B, 0x33)   # near-black
MUTED_TEXT = RGBColor(0x55, 0x5C, 0x66)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)

# Author info shown on every slide footer
AUTHOR  = "Mona Kumari"
PROJECT = "Nucleus Detection & Quantification | Syngene/BBRC | May 2026"

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def _set_solid_fill(shape, rgb):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb
    shape.line.fill.background()


def _add_rect(slide, left, top, width, height, fill, line=None):
    rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(left), Inches(top),
                                  Inches(width), Inches(height))
    _set_solid_fill(rect, fill)
    if line is None:
        rect.line.fill.background()
    else:
        rect.line.color.rgb = line
    rect.shadow.inherit = False
    return rect


def _set_run(run, text, *, size=14, bold=False, italic=False,
             color=BODY_TEXT, font="Calibri"):
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def _add_textbox(slide, left, top, width, height, *, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(left), Inches(top),
                                   Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    tf.vertical_anchor = anchor
    return box, tf


def _put_paragraph(tf, text, *, size=14, bold=False, italic=False,
                   color=BODY_TEXT, align=PP_ALIGN.LEFT,
                   space_after=6, level=0, first=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.level = level
    p.space_after = Pt(space_after)
    if not p.runs:
        run = p.add_run()
    else:
        run = p.runs[0]
    _set_run(run, text, size=size, bold=bold, italic=italic, color=color)
    return p


# ---------------------------------------------------------------------------
# Slide chrome -- brand bar at top, footer at bottom
# ---------------------------------------------------------------------------
def _new_slide(prs, *, page_no=None, total=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

    # Top brand bar (thin)
    _add_rect(slide, 0, 0, 13.333, 0.32, PRIMARY)
    # Accent stripe
    _add_rect(slide, 0, 0.32, 13.333, 0.05, ACCENT)

    # Footer separator + text
    _add_rect(slide, 0, 7.18, 13.333, 0.04, PRIMARY)

    box, tf = _add_textbox(slide, 0.4, 7.22, 12.5, 0.28,
                           anchor=MSO_ANCHOR.MIDDLE)
    _put_paragraph(tf, PROJECT, size=9, color=MUTED_TEXT,
                   align=PP_ALIGN.LEFT, first=True, space_after=0)
    if page_no is not None:
        box2, tf2 = _add_textbox(slide, 12.0, 7.22, 1.2, 0.28,
                                 anchor=MSO_ANCHOR.MIDDLE)
        _put_paragraph(tf2, f"{page_no} / {total}", size=9,
                       color=MUTED_TEXT, align=PP_ALIGN.RIGHT,
                       first=True, space_after=0)
    return slide


def _slide_title(slide, title, subtitle=None):
    box, tf = _add_textbox(slide, 0.55, 0.55, 12.3, 0.7,
                           anchor=MSO_ANCHOR.TOP)
    _put_paragraph(tf, title, size=30, bold=True, color=PRIMARY,
                   first=True, space_after=2)
    if subtitle:
        _put_paragraph(tf, subtitle, size=14, italic=True,
                       color=MUTED_TEXT, space_after=0)


def _add_image(slide, path, left, top, width=None, height=None):
    p = Path(path)
    if not p.exists():
        return None
    kw = {}
    if width is not None:  kw["width"]  = Inches(width)
    if height is not None: kw["height"] = Inches(height)
    return slide.shapes.add_picture(str(p), Inches(left), Inches(top), **kw)


def _add_table(slide, df, left, top, width, height,
               *, font_size=12, header_fill=PRIMARY,
               header_text=WHITE, zebra=True):
    rows, cols = df.shape[0] + 1, df.shape[1]
    tbl = slide.shapes.add_table(rows, cols,
                                 Inches(left), Inches(top),
                                 Inches(width), Inches(height)).table
    # Header
    for j, col in enumerate(df.columns):
        cell = tbl.cell(0, j)
        cell.text = ""
        p = cell.text_frame.paragraphs[0]
        run = p.add_run()
        _set_run(run, str(col), size=font_size, bold=True, color=header_text)
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_fill
    # Body
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            cell = tbl.cell(i + 1, j)
            v = df.iat[i, j]
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            run = p.add_run()
            _set_run(run, "" if pd.isna(v) else str(v),
                     size=font_size, color=BODY_TEXT)
            if zebra and (i % 2 == 0):
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT_BG
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE
    return tbl


def _info_panel(slide, left, top, width, height, title, paragraphs,
                *, fill=LIGHT_BG, title_color=PRIMARY):
    """A coloured panel with a bold heading and one or more body paragraphs."""
    rect = _add_rect(slide, left, top, width, height, fill)
    # Inner text
    box, tf = _add_textbox(slide, left + 0.18, top + 0.12,
                           width - 0.35, height - 0.2)
    _put_paragraph(tf, title, size=14, bold=True, color=title_color,
                   first=True, space_after=4)
    for txt in paragraphs:
        _put_paragraph(tf, txt, size=12, color=BODY_TEXT, space_after=4)
    return rect


def _bullets(slide, items, left, top, width, height,
             *, size=14, accent=True):
    box, tf = _add_textbox(slide, left, top, width, height)
    for i, txt in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(6)
        if accent:
            r1 = p.add_run()
            _set_run(r1, "▍ ", size=size, color=ACCENT, bold=True)
        r2 = p.add_run()
        _set_run(r2, txt, size=size, color=BODY_TEXT)


def _section_divider(prs, page_no, total, label, title, blurb):
    slide = _new_slide(prs, page_no=page_no, total=total)
    # Big colored panel
    _add_rect(slide, 0, 1.4, 13.333, 4.7, PRIMARY)
    _add_rect(slide, 0.55, 1.6, 0.16, 4.3, ACCENT)
    box, tf = _add_textbox(slide, 1.0, 1.8, 11.5, 4.0,
                           anchor=MSO_ANCHOR.MIDDLE)
    _put_paragraph(tf, label, size=16, bold=True, color=ACCENT,
                   first=True, space_after=6)
    _put_paragraph(tf, title, size=46, bold=True, color=WHITE,
                   space_after=10)
    _put_paragraph(tf, blurb, size=18, italic=True, color=LIGHT_BG)
    return slide


# ---------------------------------------------------------------------------
# Slide builders -- each returns nothing, just appends to prs
# ---------------------------------------------------------------------------
def slide_title(prs, total):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # Full-bleed gradient-ish: solid primary, accent stripe, decorative bar
    _add_rect(slide, 0, 0, 13.333, 7.5, PRIMARY)
    _add_rect(slide, 0, 5.6, 13.333, 0.07, ACCENT)
    _add_rect(slide, 11.0, 0, 2.333, 5.6, SECONDARY)

    # Project label
    box, tf = _add_textbox(slide, 0.7, 1.6, 11.0, 0.5)
    _put_paragraph(tf, "DIGITAL PATHOLOGY  ·  H&E HISTOPATHOLOGY",
                   size=16, bold=True, color=ACCENT, first=True, space_after=0)

    # Title
    box, tf = _add_textbox(slide, 0.7, 2.2, 11.0, 1.6)
    _put_paragraph(tf, "Nucleus Detection &", size=54, bold=True,
                   color=WHITE, first=True, space_after=4)
    _put_paragraph(tf, "Quantification at Scale", size=54, bold=True,
                   color=WHITE, space_after=0)

    # Tagline
    box, tf = _add_textbox(slide, 0.7, 4.4, 11.0, 1.0)
    _put_paragraph(tf,
                   "Three independent methods.  Five cancer cohorts.  "
                   "Fifty images.  Zero ground-truth annotations.",
                   size=20, italic=True, color=LIGHT_BG,
                   first=True, space_after=0)

    # Author block
    box, tf = _add_textbox(slide, 0.7, 6.0, 11.0, 1.2)
    _put_paragraph(tf, AUTHOR, size=22, bold=True, color=WHITE,
                   first=True, space_after=2)
    _put_paragraph(tf, "Syngene / BBRC Digital Pathology Assessment  ·  May 2026",
                   size=14, color=LIGHT_BG, space_after=0)


def slide_agenda(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Agenda",
                 "What we will cover in the next ~10 minutes")

    items = [
        ("01", "Problem & dataset",
         "What we were asked to do; what the 50 images look like."),
        ("02", "Approach: three methods",
         "Why we run a classical pipeline alongside two deep-learning models."),
        ("03", "Method walkthroughs",
         "Classical (HED + watershed), Cellpose v4, StarDist 2D_versatile_he."),
        ("04", "Quantitative results",
         "Total counts, per-cohort morphometrics, cross-method agreement."),
        ("05", "Biological interpretation",
         "What the numbers tell us about each tumour type."),
        ("06", "Limitations & next steps",
         "What we cannot answer without ground truth, and how to fix it."),
    ]
    top = 1.7
    for label, title, blurb in items:
        # Number badge
        _add_rect(s, 0.6, top, 0.7, 0.7, ACCENT)
        box, tf = _add_textbox(s, 0.6, top, 0.7, 0.7,
                               anchor=MSO_ANCHOR.MIDDLE)
        _put_paragraph(tf, label, size=18, bold=True, color=WHITE,
                       align=PP_ALIGN.CENTER, first=True, space_after=0)
        # Title + blurb
        box, tf = _add_textbox(s, 1.5, top - 0.05, 11.5, 0.85)
        _put_paragraph(tf, title, size=16, bold=True, color=PRIMARY,
                       first=True, space_after=2)
        _put_paragraph(tf, blurb, size=12, color=MUTED_TEXT,
                       space_after=0)
        top += 0.85


def slide_problem(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Problem statement",
                 "Detect every nucleus. Report counts and morphometrics.")

    # Big context block
    box, tf = _add_textbox(s, 0.6, 1.6, 7.6, 4.5)
    _put_paragraph(tf,
                   "We are given 50 H&E-stained histopathology images "
                   "covering five cancer cohorts (10 images each).",
                   size=15, color=BODY_TEXT, first=True, space_after=10)
    _put_paragraph(tf,
                   "The task is to segment EVERY nucleus, count them, "
                   "and quantify their morphology -- area, eccentricity, "
                   "solidity, density per megapixel.",
                   size=15, color=BODY_TEXT, space_after=10)
    _put_paragraph(tf,
                   "Catch:  no manual annotations were provided.",
                   size=16, bold=True, color=ACCENT, space_after=10)
    _put_paragraph(tf,
                   "So we cannot compute precision / recall / F1 directly. "
                   "We need a defensible substitute for accuracy.",
                   size=15, color=BODY_TEXT, space_after=10)
    _put_paragraph(tf,
                   "Solution: run THREE independent segmentation methods of "
                   "different families and use their AGREEMENT as evidence "
                   "of correctness.",
                   size=15, color=BODY_TEXT, space_after=0)

    # Stats panel on the right
    _info_panel(s, 8.5, 1.6, 4.4, 4.5,
                "By the numbers",
                ["50 input images (5 cohorts × 10)",
                 "3 segmentation methods",
                 "~480 × 560 px each",
                 "~24,000 nuclei detected per method",
                 "0 ground-truth annotations",
                 "End-to-end pipeline: ~6 min",
                 "Hardware: MacBook Pro (Apple Silicon, MPS)"])


def slide_dataset(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "The dataset",
                 "Five cancer cohorts, ten images each, mixed tissue architectures")

    df = pd.DataFrame([
        ["BRC",       "Breast carcinoma",                                          "10",
         "Heterogeneous: glands, stroma, lymphocytes"],
        ["CRC",       "Colorectal carcinoma",                                      "10",
         "Glandular crypts; columnar epithelial cells"],
        ["HCC",       "Hepatocellular carcinoma",                                  "10",
         "Large hepatocytes; abundant cytoplasm"],
        ["NSCLC_AD",  "Non-small-cell lung carcinoma — adenocarcinoma",            "10",
         "Glandular pattern; cuboidal cells"],
        ["NSCLC_SCC", "Non-small-cell lung carcinoma — squamous cell carcinoma",   "10",
         "Dense monomorphic squamous nests"],
    ], columns=["Cohort", "Disease", "Images", "Visual cue"])
    _add_table(s, df, left=0.6, top=1.6, width=12.1, height=2.6, font_size=13)

    _info_panel(s, 0.6, 4.5, 12.1, 2.4,
                "Why this matters for segmentation",
                [
                    "The five cohorts span a wide range of nucleus density, size, and shape.",
                    "Stain intensity also varies between images. A method that works on one "
                    "cohort but breaks on another is not useful.",
                    "We deliberately use a SINGLE global parameter set across all cohorts -- "
                    "any difference in counts is biology, not parameter cheating.",
                ])


def slide_approach(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Approach: three methods, three families",
                 "Independent failure modes — agreement is meaningful.")

    df = pd.DataFrame([
        ["Classical (HED + watershed)",
         "Image processing",
         "Fully transparent. Every step inspectable. No training data."],
        ["Cellpose v4 (cpsam)",
         "Generalist deep learning",
         "Pretrained flow-based segmenter. Robust across tissue types."],
        ["StarDist (2D_versatile_he)",
         "H&E-specific deep learning",
         "Star-convex polygon prior. Trained specifically on H&E nuclei."],
    ], columns=["Method", "Family", "Why include it"])
    _add_table(s, df, left=0.6, top=1.6, width=12.1, height=2.6, font_size=13)

    # Key insight banner
    _add_rect(s, 0.6, 4.45, 12.1, 0.7, PRIMARY)
    box, tf = _add_textbox(s, 0.8, 4.45, 11.7, 0.7,
                           anchor=MSO_ANCHOR.MIDDLE)
    _put_paragraph(tf,
                   "Key insight: when three orthogonal methods agree, "
                   "the count is almost certainly correct.",
                   size=15, bold=True, color=WHITE, first=True, space_after=0)

    _bullets(s, [
        "Same Python interface: every method exposes segment(rgb) -> uint32 instance map.",
        "Same outputs per image: yellow-boundary overlay, instance mask, per-image stats CSV.",
        "Same driver script: code/01_run_segmentation.py --method <classical|cellpose|stardist>.",
        "Adding a fourth method is ~30 lines of code -- the architecture is plug-and-play.",
    ], left=0.6, top=5.4, width=12.1, height=1.7, size=13)


def slide_classical_pipeline(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Classical pipeline — step by step",
                 "Pure image processing. No learned weights. ~18 s for 50 images on CPU.")

    steps = [
        ("1", "Stain deconvolution",
         "rgb2hed isolates the Hematoxylin channel — pixel intensity now means "
         "‘amount of nucleus dye here’, free of pink eosin contamination."),
        ("2", "Contrast + smoothing",
         "Robust [1%, 99%] percentile clip + Gaussian σ=1 — kills speckle, "
         "ignores stray bright artefacts."),
        ("3", "Otsu threshold",
         "Picks the threshold that minimises within-class variance — the natural "
         "split between background and nuclei."),
        ("4", "Morphology cleanup",
         "Opening (disk r=2) removes thin noise; hole-fill closes interior "
         "pinpricks; drop objects < 30 px²."),
        ("5", "Distance + watershed",
         "Distance transform turns each nucleus into a ‘mountain’; "
         "peak_local_max finds centres; watershed splits touching nuclei."),
        ("6", "Region filter",
         "Keep regions with area ∈ [30, 4000] px² and solidity ≥ 0.70 — "
         "rejects specks, vessels, jagged stromal artefacts."),
    ]
    top = 1.6
    for num, title, body in steps:
        _add_rect(s, 0.6, top, 0.6, 0.7, ACCENT)
        box, tf = _add_textbox(s, 0.6, top, 0.6, 0.7,
                               anchor=MSO_ANCHOR.MIDDLE)
        _put_paragraph(tf, num, size=18, bold=True, color=WHITE,
                       align=PP_ALIGN.CENTER, first=True, space_after=0)
        box, tf = _add_textbox(s, 1.4, top - 0.04, 11.5, 0.78)
        _put_paragraph(tf, title, size=14, bold=True, color=PRIMARY,
                       first=True, space_after=2)
        _put_paragraph(tf, body, size=12, color=BODY_TEXT, space_after=0)
        top += 0.83


def slide_stain_norm(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Macenko stain normalisation \u2014 evaluated & rejected",
                 "Normalisation degraded results; un-normalised data used throughout")

    # Before / after table
    df = pd.DataFrame([
        ["Classical", "24,250", "15,497", "\u221236%"],
        ["Cellpose",  "24,097", "24,194", "+0.4%"],
        ["StarDist",  "20,783", "14,732", "\u221229%"],
    ], columns=["Method", "Without norm.", "With norm.", "\u0394"])
    _add_table(s, df, left=0.6, top=1.6, width=7.5, height=1.8, font_size=15)

    _info_panel(s, 8.5, 1.6, 4.3, 1.8,
                "What went wrong?",
                ["Reference image (BRC/Image1) too different from other cohorts.",
                 "Washed out tissue (bright px 6.8%\u219260.7%) or over-darkened.",
                 "IoU dropped from 0.51\u20130.67 \u2192 0.13\u20130.44.",
                 "Real nuclei destroyed, not just false positives."],
                fill=LIGHT_BG, title_color=ACCENT)

    # Three insight panels
    _info_panel(s, 0.6, 3.8, 3.95, 2.8,
                "Cellpose is stain-invariant",
                ["Count barely changes (+0.4%).",
                 "But per-image swings up to \u00b192%.",
                 "Generalist model tolerates stain variation \u2014 "
                 "normalisation adds noise, not signal."],
                fill=LIGHT_BG, title_color=PRIMARY)
    _info_panel(s, 4.7, 3.8, 3.95, 2.8,
                "Classical / StarDist destroyed",
                ["Classical BRC: 5,704 \u2192 2,015 (\u221265%).",
                 "BRC/Image3: 1,084 \u2192 59 nuclei (\u221295%).",
                 "StarDist uniform \u221229% across all cohorts.",
                 "Normalisation killed real detections."],
                fill=LIGHT_BG, title_color=ACCENT)
    _info_panel(s, 8.8, 3.8, 3.95, 2.8,
                "Decision",
                ["All primary results use un-normalised input.",
                 "Normalised results preserved in results_norm/.",
                 "Code retained for future use with better reference."],
                fill=LIGHT_BG, title_color=PRIMARY)


def slide_dl_methods(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Deep-learning methods at a glance",
                 "Two pretrained models — no training, no labels needed.")

    # Two columns
    _info_panel(s, 0.6, 1.6, 6.1, 4.5, "Cellpose v4 (cpsam)",
                [
                    "Backbone: Segment-Anything-style transformer.",
                    "Predicts per-pixel flow vectors pointing to cell centres + a "
                    "cell-probability heatmap.",
                    "Pixels that converge under gradient ascent → same nucleus. "
                    "No watershed needed.",
                    "MPS (Apple Metal): ~6 s/image  ·  CPU: ~150 s/image.",
                    "Used: diameter=None (auto-scale per image); default flow / "
                    "cell-prob thresholds; ~5 min for the whole dataset.",
                ])
    _info_panel(s, 7.0, 1.6, 5.7, 4.5, "StarDist 2D_versatile_he",
                [
                    "Predicts per-pixel: probability of being inside a nucleus + "
                    "32 ray distances to the boundary (a star-convex polygon).",
                    "NMS (IoU 0.30) keeps best non-overlapping polygons.",
                    "Pretrained specifically on H&E histopathology nuclei.",
                    "Lowered prob_thresh from 0.69 → 0.40 to recover dense "
                    "lymphocyte clusters (otherwise misses ~50%).",
                    "Tiny model (~5 MB)  ·  ~30 s for 50 images on CPU.",
                ])
    # Footer takeaway
    _add_rect(s, 0.6, 6.3, 12.1, 0.5, ACCENT)
    box, tf = _add_textbox(s, 0.8, 6.3, 11.7, 0.5,
                           anchor=MSO_ANCHOR.MIDDLE)
    _put_paragraph(tf,
                   "Both DL methods used pretrained weights — no fine-tuning needed for this dataset.",
                   size=14, bold=True, color=WHITE, first=True, space_after=0)


def slide_qual_classical(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Qualitative result — classical pipeline",
                 "One row per cohort.  Original  |  H channel  |  Instances  |  Overlay.")
    _add_image(s, FIGURES_DIR / "01_qualitative_grid_classical.png",
               left=0.6, top=1.45, width=12.1)
    box, tf = _add_textbox(s, 0.6, 6.65, 12.1, 0.4)
    _put_paragraph(tf,
                   "Yellow contours mark detected nucleus boundaries. "
                   "Hematoxylin channel cleanly isolates nuclei from pink stroma.",
                   size=12, italic=True, color=MUTED_TEXT,
                   align=PP_ALIGN.CENTER, first=True, space_after=0)


def slide_qual_cross(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Cross-method qualitative comparison",
                 "Same image, three methods. Boundaries from each overlaid.")
    _add_image(s, FIGURES_DIR / "06_method_qualitative_grid.png",
               left=0.6, top=1.45, width=12.1)
    box, tf = _add_textbox(s, 0.6, 6.65, 12.1, 0.4)
    _put_paragraph(tf,
                   "Differences are concentrated in dense lymphocyte clusters — "
                   "where the methods’ shape priors disagree the most.",
                   size=12, italic=True, color=MUTED_TEXT,
                   align=PP_ALIGN.CENTER, first=True, space_after=0)


def slide_total_counts(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Total nuclei detected",
                 "Per method, broken down by cohort")

    df = pd.DataFrame([
        ["Classical", "24,250", "5,704", "5,391", "3,562", "4,602", "4,991"],
        ["Cellpose",  "24,097", "5,790", "5,499", "3,278", "4,118", "5,412"],
        ["StarDist",  "20,783", "5,309", "4,601", "2,775", "3,662", "4,436"],
    ], columns=["Method", "Total", "BRC", "CRC", "HCC", "NSCLC_AD", "NSCLC_SCC"])
    _add_table(s, df, left=0.6, top=1.6, width=12.1, height=2.0, font_size=15)

    # Three highlight callouts
    _info_panel(s, 0.6, 4.0, 3.95, 2.7,
                "Classical \u2248 Cellpose",
                ["24,250 vs 24,097 (<1% difference).",
                 "Strong cross-method validation \u2014 "
                 "two completely different approaches agree."],
                fill=LIGHT_BG, title_color=PRIMARY)
    _info_panel(s, 4.7, 4.0, 3.95, 2.7,
                "StarDist more conservative",
                ["20,783 total (\u221214% vs classical).",
                 "Star-convex polygon prior misses "
                 "non-convex / overlapping nuclei."],
                fill=LIGHT_BG, title_color=PRIMARY)
    _info_panel(s, 8.8, 4.0, 3.95, 2.7,
                "Cohort ranking preserved",
                ["BRC/CRC densest, HCC sparsest.",
                 "All three methods agree on this ordering \u2014 strong evidence "
                 "the differences are biological, not algorithmic."],
                fill=LIGHT_BG, title_color=PRIMARY)


def slide_count_scatter(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Per-image count agreement",
                 "Each point is one of the 50 images.")
    _add_image(s, FIGURES_DIR / "05_method_count_scatter.png",
               left=0.6, top=1.45, width=8.0)

    _info_panel(s, 8.9, 1.5, 3.9, 5.2,
                "How to read this",
                [
                    "X-axis: classical count for an image.",
                    "Y-axis: DL method count for that same image.",
                    "Diagonal y=x means perfect agreement.",
                    "Classical and Cellpose cluster tightly around y=x.",
                    "StarDist sits slightly below (more conservative).",
                    "All methods preserve the same per-image ranking.",
                ])


def slide_iou_table(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Mask agreement — mean foreground-IoU per cohort",
                 "Each instance map collapsed to ‘any nucleus pixel’; pairwise IoU averaged.")

    df = pd.DataFrame([
        ["BRC",       "0.21", "0.29", "0.36"],
        ["CRC",       "0.39", "0.37", "0.44"],
        ["HCC",       "0.13", "0.29", "0.17"],
        ["NSCLC_AD",  "0.28", "0.30", "0.36"],
        ["NSCLC_SCC", "0.25", "0.29", "0.40"],
    ], columns=["Cohort", "classical vs cellpose",
                "classical vs stardist", "cellpose vs stardist"])
    _add_table(s, df, left=2.5, top=1.6, width=8.3, height=3.0, font_size=15)

    _info_panel(s, 0.6, 5.0, 12.1, 1.9,
                "Why this matters",
                [
                    "IoU values are lower post-normalisation — expected: normalisation removed "
                    "many false detections, so methods now disagree more on which pixels are nuclear.",
                    "Cellpose–StarDist agreement is consistently highest (both DL methods share a "
                    "refined notion of 'nucleus').",
                    "CRC shows strongest agreement (0.44); HCC classical-vs-cellpose lowest (0.13) — "
                    "large hepatocytes are split differently by watershed vs flow fields.",
                ])


def slide_density(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Nucleus density per cohort",
                 "Counts normalised by image area — comparable across image sizes.")
    _add_image(s, FIGURES_DIR / "04_density_by_cohort.png",
               left=0.6, top=1.45, width=8.0)
    _info_panel(s, 8.9, 1.5, 3.9, 5.2,
                "Reading the bars",
                [
                    "Density = nuclei per megapixel of tissue.",
                    "BRC/CRC densest (~2,000/Mpx classical); HCC sparsest (~1,279/Mpx).",
                    "Differences are biology \u2014 not parameter sensitivity.",
                    "All three methods reproduce the same ranking.",
                ])


def slide_distributions(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Count and area distributions",
                 "How variable are nuclei within each cohort?")
    _add_image(s, FIGURES_DIR / "02_count_by_cohort.png",
               left=0.55, top=1.45, width=6.2)
    _add_image(s, FIGURES_DIR / "03_area_by_cohort.png",
               left=6.95, top=1.45, width=6.2)
    box, tf = _add_textbox(s, 0.6, 5.7, 12.1, 1.3)
    _put_paragraph(tf, "What we learn:", size=14, bold=True,
                   color=PRIMARY, first=True, space_after=4)
    _put_paragraph(tf,
                   "BRC and CRC have the widest count spreads — heterogeneous "
                   "tissue. NSCLC_SCC has the tightest area distribution "
                   "(std ≈ 9 px²) — uniformly small squamous nuclei.",
                   size=13, color=BODY_TEXT, space_after=2)
    _put_paragraph(tf,
                   "CRC has the largest mean area — pulled up by columnar "
                   "epithelial nuclei lining gland crypts.",
                   size=13, color=BODY_TEXT, space_after=0)


def slide_fpfn(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "FP / FN analysis (cross-method consensus)",
                 "Green = agreed  |  Red = only this method (FP-like)  |  Blue = missed (FN-like)")

    _add_image(s, FIGURES_DIR / "08_fpfn_counts_bar.png",
               left=0.3, top=1.45, width=8.0)

    _info_panel(s, 8.5, 1.5, 4.4, 2.5,
                "How it works",
                ["Consensus = pixel is nucleus in \u22652 of 3 methods.",
                 "FP-like: method says YES, consensus says NO.",
                 "FN-like: method says NO, consensus says YES.",
                 "Not ground truth \u2014 best available proxy."],
                fill=LIGHT_BG, title_color=PRIMARY)

    _info_panel(s, 8.5, 4.2, 4.4, 2.7,
                "Verdict",
                ["StarDist: highest TP-like (60.9%) \u2014 best balance.",
                 "Cellpose: most FP-like (33.6%) \u2014 high recall, more unique detections.",
                 "Classical: most FN-like (26.2%) \u2014 misses dim lymphocytes.",
                 "Recommendation: Cellpose for recall, StarDist for precision."],
                fill=LIGHT_BG, title_color=ACCENT)


def slide_biology(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Biological interpretation",
                 "Do our numbers make sense to a pathologist?")

    rows = [
        ("HCC",      "Lowest density (~1,279/Mpx)",
         "Hepatocytes are large cells with abundant pink cytoplasm \u2014 "
         "fewer nuclei per unit area, exactly as expected.", PRIMARY),
        ("NSCLC_SCC", "Smallest, most uniform nuclei (mean \u2248 80 px\u00b2)",
         "Dense monomorphic squamous nests — small, tightly-packed cells "
         "with similar nucleus size.", SECONDARY),
        ("BRC / CRC", "Highest density and largest variance",
         "Heterogeneous architecture (glands + stroma + lymphocytic "
         "infiltrate). Variance reflects which mix dominates each crop.", ACCENT),
        ("All cohorts", "Mean solidity ≈ 0.93",
         "Segmented instances are convex and well-formed — they look "
         "like real nuclei, not jagged fragments.", PRIMARY),
    ]
    top = 1.6
    for cohort, headline, body, color in rows:
        _add_rect(s, 0.6, top, 0.18, 1.05, color)
        box, tf = _add_textbox(s, 0.95, top, 11.8, 1.05)
        _put_paragraph(tf, f"{cohort}  ·  {headline}",
                       size=14, bold=True, color=color,
                       first=True, space_after=3)
        _put_paragraph(tf, body, size=12, color=BODY_TEXT, space_after=0)
        top += 1.2


def slide_limitations(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Limitations",
                 "What we cannot conclude from this work, and why.")

    items = [
        ("No ground truth",
         "We report intrinsic morphometrics and cross-method agreement, "
         "not precision/recall. Manual annotation on a held-out subset "
         "would close this gap."),
        ("Watershed over-segmentation",
         "The classical pipeline can split very large nuclei (e.g. some "
         "hepatocytes in HCC). Cellpose and StarDist suffer less."),
        ("StarDist conservatism",
         "Polygon prior misses some non-convex / overlapping nuclei "
         "even at the lowered prob_thresh = 0.40."),
        ("Macenko normalisation degraded results",
         "Normalisation washed out tissue or over-darkened images, "
         "destroying real nuclei. Un-normalised results are used "
         "throughout; normalised data preserved in results_norm/."),
        ("Single global parameter set",
         "Chosen for fairness across cohorts, not maximum per-cohort "
         "accuracy. Per-cohort tuning would bump numbers but break "
         "generalisation."),
    ]
    top = 1.6
    for headline, body in items:
        _add_rect(s, 0.6, top, 0.18, 0.9, ACCENT)
        box, tf = _add_textbox(s, 0.95, top, 11.8, 0.9)
        _put_paragraph(tf, headline, size=14, bold=True,
                       color=PRIMARY, first=True, space_after=3)
        _put_paragraph(tf, body, size=12, color=BODY_TEXT, space_after=0)
        top += 1.05


def slide_future(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Next steps",
                 "How we would extend this work in production.")

    items = [
        ("Manual annotation of ~5 crops/cohort",
         "Unlocks real F1 / panoptic-quality metrics for each method."),
        ("Reinhard normalisation comparison",
         "Compare Reinhard vs Macenko impact; ensemble the two preprocessing approaches."),
        ("HoVer-Net for cell-type classification",
         "Joint segmentation + nucleus type (epithelial / lymphocyte / stromal). "
         "Enables tumour-microenvironment analyses."),
        ("Method ensemble (consensus mask)",
         "Combine all three methods (union + NMS) into a single best segmentation, "
         "likely more accurate than any individual method."),
        ("Hungarian-matched per-instance IoU",
         "Replace foreground-only IoU with proper per-nucleus correspondence."),
        ("Whole-slide tile-based scaling",
         "Move from 480×560 ROIs to gigapixel WSIs with a tiling/stitching layer."),
    ]
    top = 1.6
    for headline, body in items:
        _add_rect(s, 0.6, top, 0.18, 0.78, SECONDARY)
        box, tf = _add_textbox(s, 0.95, top, 11.8, 0.78)
        _put_paragraph(tf, headline, size=14, bold=True,
                       color=PRIMARY, first=True, space_after=3)
        _put_paragraph(tf, body, size=12, color=BODY_TEXT, space_after=0)
        top += 0.92


def slide_deliverables(prs, page_no, total):
    s = _new_slide(prs, page_no=page_no, total=total)
    _slide_title(s, "Deliverables & runtime",
                 "What this repository contains, and how long it takes to reproduce.")

    df = pd.DataFrame([
        ["code/",                  "4 modules + 4 driver scripts (single-command pipeline)"],
        ["results/<method>/",      "50 overlays + 50 masks + per_image_stats.csv per method"],
        ["results/per_cohort_summary.csv", "3 methods × 5 cohorts aggregated table"],
        ["results/method_agreement.csv",   "Pairwise foreground-IoU per image"],
        ["results/figures/",       "Nine figures (this deck embeds them all)"],
        ["report/report.html",     "Styled HTML report with embedded figures"],
        ["report/report.md",       "Plain-text Markdown version"],
        ["presentation/slides.pptx", "This deck"],
        ["study/",                 "13 markdown deep-dives for self-study & reviewer Q&A"],
        ["run.sh",                 "One-command reproducer (./run.sh all)"],
    ], columns=["Path", "Contents"])
    _add_table(s, df, left=0.6, top=1.6, width=12.1, height=4.5, font_size=12)

    _add_rect(s, 0.6, 6.2, 12.1, 0.7, PRIMARY)
    box, tf = _add_textbox(s, 0.8, 6.2, 11.7, 0.7,
                           anchor=MSO_ANCHOR.MIDDLE)
    _put_paragraph(tf,
                   "End-to-end runtime on MacBook Pro (Apple Silicon, no NVIDIA GPU): ~6 minutes.",
                   size=14, bold=True, color=WHITE, first=True, space_after=0)


def slide_thanks(prs, page_no, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_rect(s, 0, 0, 13.333, 7.5, PRIMARY)
    _add_rect(s, 0, 5.2, 13.333, 0.07, ACCENT)
    _add_rect(s, 11.0, 0, 2.333, 5.2, SECONDARY)

    box, tf = _add_textbox(s, 0.7, 2.0, 11.0, 1.4)
    _put_paragraph(tf, "Thank you.", size=72, bold=True, color=WHITE,
                   first=True, space_after=4)
    box, tf = _add_textbox(s, 0.7, 3.4, 11.0, 0.6)
    _put_paragraph(tf, "Questions, comments, or extensions are very welcome.",
                   size=20, italic=True, color=LIGHT_BG, first=True,
                   space_after=0)
    box, tf = _add_textbox(s, 0.7, 5.5, 11.0, 1.6)
    _put_paragraph(tf, AUTHOR, size=24, bold=True, color=WHITE,
                   first=True, space_after=2)
    _put_paragraph(tf, "Syngene / BBRC Digital Pathology Assessment  ·  May 2026",
                   size=14, color=LIGHT_BG, space_after=0)


# ---------------------------------------------------------------------------
# Build & save
# ---------------------------------------------------------------------------
def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # The order in which slides are constructed.
    # We compute total upfront so footers can show "page x / total".
    plan = [
        ("title",       slide_title),
        ("agenda",      slide_agenda),
        ("problem",     slide_problem),
        ("dataset",     slide_dataset),
        ("approach",    slide_approach),
        ("section1",    lambda prs, p, t: _section_divider(
            prs, p, t, "PART 1", "Methods",
            "How each of the three pipelines turns an RGB image into instance labels.")),
        ("stain_norm", slide_stain_norm),
        ("classical",   slide_classical_pipeline),
        ("dl",          slide_dl_methods),
        ("section2",    lambda prs, p, t: _section_divider(
            prs, p, t, "PART 2", "Results",
            "What we found — qualitatively and quantitatively.")),
        ("qual_class",  slide_qual_classical),
        ("qual_cross",  slide_qual_cross),
        ("totals",      slide_total_counts),
        ("scatter",     slide_count_scatter),
        ("iou",         slide_iou_table),
        ("density",     slide_density),
        ("dists",       slide_distributions),
        ("fpfn",        slide_fpfn),
        ("biology",     slide_biology),
        ("section3",    lambda prs, p, t: _section_divider(
            prs, p, t, "PART 3", "Discussion",
            "What we cannot yet conclude — and how to fix it.")),
        ("limits",      slide_limitations),
        ("future",      slide_future),
        ("deliv",       slide_deliverables),
        ("thanks",      slide_thanks),
    ]
    total = len(plan)
    for i, (name, fn) in enumerate(plan, start=1):
        if name == "title":
            fn(prs, total)
        elif name == "thanks":
            fn(prs, i, total)
        else:
            try:
                fn(prs, i, total)
            except TypeError:
                fn(prs, total)

    PPT_OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(PPT_OUT))
    print(f"Wrote {PPT_OUT}  ({total} slides)")


if __name__ == "__main__":
    build()
