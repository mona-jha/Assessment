#!/usr/bin/env python3
"""
YOLOv8 Instance Segmentation — trained on Cellpose pseudo-labels.

Steps:
  1. Convert Cellpose uint16 instance masks → YOLO polygon .txt labels
  2. Build train/val split (8/2 per cohort = 40 train + 10 val)
  3. Train yolov8n-seg for N epochs
  4. Run inference on all 50 images, save overlays + per-image counts

Usage:
  python code/05_yolov8_seg.py                     # full pipeline
  python code/05_yolov8_seg.py --step convert      # only convert masks
  python code/05_yolov8_seg.py --step train         # only train
  python code/05_yolov8_seg.py --step infer         # only infer
  python code/05_yolov8_seg.py --epochs 50          # custom epoch count
"""

import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
MASK_DIR = ROOT / "results" / "cellpose" / "masks"
IMG_DIR = ROOT / "doc" / "Assessment"
YOLO_DIR = ROOT / "yolo_dataset"
RESULTS_DIR = ROOT / "results" / "yolov8"
COHORTS = ["BRC", "CRC", "HCC", "NSCLC_AD", "NSCLC_SCC"]

# Train/val split: images 1-8 → train, 9-10 → val  (per cohort)
VAL_IMAGES = {"Image9", "Image10"}


# ── Step 1: Convert Cellpose masks to YOLO polygon labels ───────────────────

def mask_to_yolo_polygons(mask: np.ndarray, min_points: int = 6) -> list[str]:
    """Convert a uint16 instance mask to YOLO segmentation lines.

    Each line: `0 x1 y1 x2 y2 ... xn yn`  (class 0 = nucleus, normalised coords).
    Tiny contours (< min_points vertices) are skipped.
    """
    h, w = mask.shape
    lines = []
    for label_id in np.unique(mask):
        if label_id == 0:
            continue
        binary = (mask == label_id).astype(np.uint8)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            cnt = cnt.squeeze()
            if cnt.ndim != 2 or len(cnt) < min_points:
                continue
            # Simplify to reduce file size (epsilon ~1% of perimeter)
            eps = 0.01 * cv2.arcLength(cnt.reshape(-1, 1, 2), True)
            cnt = cv2.approxPolyDP(cnt.reshape(-1, 1, 2), eps, True).squeeze()
            if cnt.ndim != 2 or len(cnt) < min_points:
                continue
            # Normalise to [0, 1]
            coords = []
            for x, y in cnt:
                coords.append(f"{x / w:.6f}")
                coords.append(f"{y / h:.6f}")
            lines.append("0 " + " ".join(coords))
    return lines


def tile_image_and_mask(img_np: np.ndarray, mask: np.ndarray,
                        grid: int = 2, overlap: int = 32):
    """Split image and mask into grid×grid tiles with overlap.
    Returns list of (tile_img, tile_mask, suffix)."""
    h, w = mask.shape
    th = h // grid
    tw = w // grid
    tiles = []
    for row in range(grid):
        for col in range(grid):
            y0 = max(0, row * th - overlap) if row > 0 else 0
            y1 = min(h, (row + 1) * th + overlap) if row < grid - 1 else h
            x0 = max(0, col * tw - overlap) if col > 0 else 0
            x1 = min(w, (col + 1) * tw + overlap) if col < grid - 1 else w
            tile_img = img_np[y0:y1, x0:x1]
            tile_mask = mask[y0:y1, x0:x1].copy()
            # Re-label: keep only nuclei whose centroid is in this tile
            for lid in np.unique(tile_mask):
                if lid == 0:
                    continue
                ys, xs = np.where(tile_mask == lid)
                cy, cx = ys.mean(), xs.mean()
                # Check if centroid is in the core (non-overlap) region
                core_y0 = row * th - y0
                core_y1 = (row + 1) * th - y0 if row < grid - 1 else y1 - y0
                core_x0 = col * tw - x0
                core_x1 = (col + 1) * tw - x0 if col < grid - 1 else x1 - x0
                if not (core_y0 <= cy < core_y1 and core_x0 <= cx < core_x1):
                    tile_mask[tile_mask == lid] = 0
            suffix = f"_r{row}c{col}"
            tiles.append((tile_img, tile_mask, suffix))
    return tiles


def step_convert():
    """Convert all 50 Cellpose masks → YOLO .txt + copy images as 2×2 tiles,
    organised into train/val splits."""
    print("Step 1: Converting Cellpose masks → YOLO polygon labels (2×2 tiles) …")

    for split in ("train", "val"):
        (YOLO_DIR / split / "images").mkdir(parents=True, exist_ok=True)
        (YOLO_DIR / split / "labels").mkdir(parents=True, exist_ok=True)

    n_train = n_val = 0
    total_nuclei = 0

    for cohort in COHORTS:
        cohort_img_dir = IMG_DIR / cohort
        for img_path in sorted(cohort_img_dir.glob("*.png")):
            stem = img_path.stem                       # e.g. Image1
            mask_name = f"{cohort}_{stem}_mask.png"
            mask_path = MASK_DIR / mask_name

            if not mask_path.exists():
                print(f"  WARN: {mask_path} not found, skipping")
                continue

            # Decide split
            split = "val" if stem in VAL_IMAGES else "train"
            out_stem = f"{cohort}_{stem}"

            # Load image + mask
            img = Image.open(img_path)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img_np = np.array(img)
            mask = np.array(Image.open(mask_path))

            # Tile into 2×2 grid to keep nuclei per tile manageable for YOLO
            tiles = tile_image_and_mask(img_np, mask, grid=2, overlap=32)

            for tile_img, tile_mask, suffix in tiles:
                tile_stem = f"{out_stem}{suffix}"
                lines = mask_to_yolo_polygons(tile_mask)
                # Cap at 200 labels per tile to avoid YOLO assigner OOM
                if len(lines) > 200:
                    lines = lines[:200]
                total_nuclei += len(lines)

                # Write label file
                label_path = YOLO_DIR / split / "labels" / f"{tile_stem}.txt"
                label_path.write_text("\n".join(lines) + "\n" if lines else "")

                # Save tile image
                Image.fromarray(tile_img).save(
                    YOLO_DIR / split / "images" / f"{tile_stem}.png"
                )

            if split == "train":
                n_train += 1
            else:
                n_val += 1

    # Write data.yaml
    yaml_path = YOLO_DIR / "data.yaml"
    yaml_path.write_text(
        f"path: {YOLO_DIR}\n"
        f"train: train/images\n"
        f"val: val/images\n"
        f"nc: 1\n"
        f"names: ['nucleus']\n"
    )

    print(f"  Done: {n_train} train + {n_val} val images, "
          f"{total_nuclei} nucleus polygons total")
    print(f"  Dataset: {YOLO_DIR}")
    print(f"  Config:  {yaml_path}")


# ── Step 2: Train ───────────────────────────────────────────────────────────

def step_train(epochs: int = 30, imgsz: int = 640, batch: int = 1):
    """Train YOLOv8n-seg on the pseudo-labelled dataset."""
    from ultralytics import YOLO

    yaml_path = YOLO_DIR / "data.yaml"
    if not yaml_path.exists():
        sys.exit("data.yaml not found. Run --step convert first.")

    # Resume from last.pt if it exists, else start from pretrained
    last_pt = ROOT / "results" / "yolov8_train" / "weights" / "last.pt"
    if last_pt.exists():
        print(f"Step 2: Resuming training from {last_pt} for {epochs} epochs …")
        model = YOLO(str(last_pt))
        model.train(
            data=str(yaml_path),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            project=str(ROOT / "results"),
            name="yolov8_train",
            exist_ok=True,
            device="mps",
            workers=2,
            patience=10,
            save=True,
            plots=True,
            resume=True,
        )
    else:
        print(f"Step 2: Training yolov8n-seg for {epochs} epochs …")
        local_weights = ROOT / "yolov8n-seg.pt"
        model = YOLO(str(local_weights))
        model.train(
            data=str(yaml_path),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            project=str(ROOT / "results"),
            name="yolov8_train",
            exist_ok=True,
            device="mps",
            workers=2,
            patience=10,
            save=True,
            plots=True,
        )
    # Copy best weights to results/yolov8/
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    best_src = ROOT / "results" / "yolov8_train" / "weights" / "best.pt"
    best_dst = RESULTS_DIR / "best.pt"
    if best_src.exists():
        shutil.copy2(best_src, best_dst)
        print(f"  Best weights saved to {best_dst}")
    else:
        print("  WARN: best.pt not found in training output")


# ── Step 3: Inference ──────────────────────────────────────────────────────

def step_infer(imgsz: int = 640):
    """Run YOLOv8 inference on all 50 images using 2×2 tiling (matching
    training), stitch results, save overlays + CSV."""
    from ultralytics import YOLO

    weights = RESULTS_DIR / "best.pt"
    if not weights.exists():
        sys.exit(f"Weights not found at {weights}. Run --step train first.")

    print("Step 3: Running YOLOv8 inference on all 50 images (2×2 tiled) …")
    model = YOLO(str(weights))

    overlay_dir = RESULTS_DIR / "overlays"
    mask_dir = RESULTS_DIR / "masks"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)

    grid = 2
    conf = 0.05  # low threshold to catch more dense nuclei

    rows = []
    for cohort in COHORTS:
        cohort_img_dir = IMG_DIR / cohort
        for img_path in sorted(cohort_img_dir.glob("*.png")):
            stem = img_path.stem
            out_stem = f"{cohort}_{stem}"

            # Load image
            img = Image.open(img_path)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img_np = np.array(img)
            h, w = img_np.shape[:2]

            # Full-image instance mask + overlay
            instance_mask = np.zeros((h, w), dtype=np.uint16)
            overlay = img_np.copy()
            # Collect compact mask crops + bboxes for fast NMS
            detections = []  # list of (y0, y1, x0, x1, area, crop_mask)

            # Tile into 2×2 grid (same as training)
            th = h // grid
            tw = w // grid
            for row in range(grid):
                for col in range(grid):
                    y0 = row * th
                    y1 = h if row == grid - 1 else (row + 1) * th
                    x0 = col * tw
                    x1 = w if col == grid - 1 else (col + 1) * tw

                    tile = img_np[y0:y1, x0:x1]

                    results = model.predict(
                        tile, imgsz=imgsz, conf=conf, max_det=500,
                        verbose=False, device="mps"
                    )
                    r = results[0]

                    if r.masks is not None:
                        tile_h, tile_w = tile.shape[:2]
                        for seg_mask in r.masks.data.cpu().numpy():
                            seg_resized = cv2.resize(
                                seg_mask, (tile_w, tile_h),
                                interpolation=cv2.INTER_NEAREST
                            )
                            binary = seg_resized > 0.5
                            if binary.sum() < 10:
                                continue
                            # Get bbox in full-image coords
                            ys, xs = np.where(binary)
                            by0, by1 = int(ys.min()) + y0, int(ys.max()) + y0
                            bx0, bx1 = int(xs.min()) + x0, int(xs.max()) + x0
                            # Store compact crop in full-image coords
                            full_crop = np.zeros((h, w), dtype=np.uint8)
                            full_crop[y0:y1, x0:x1][binary] = 1
                            detections.append((by0, by1, bx0, bx1, int(binary.sum()), full_crop))

            # Fast bbox-based NMS: only check mask IoU for overlapping bboxes
            keep = [True] * len(detections)
            for i in range(len(detections)):
                if not keep[i]:
                    continue
                iy0, iy1, ix0, ix1, ia, _ = detections[i]
                for j in range(i + 1, len(detections)):
                    if not keep[j]:
                        continue
                    jy0, jy1, jx0, jx1, ja, _ = detections[j]
                    # Fast bbox overlap check
                    oy0, oy1 = max(iy0, jy0), min(iy1, jy1)
                    ox0, ox1 = max(ix0, jx0), min(ix1, jx1)
                    if oy0 >= oy1 or ox0 >= ox1:
                        continue  # no bbox overlap → skip
                    # Compute mask IoU only in the overlap region
                    mi = detections[i][5][oy0:oy1+1, ox0:ox1+1]
                    mj = detections[j][5][oy0:oy1+1, ox0:ox1+1]
                    inter = np.logical_and(mi, mj).sum()
                    if inter == 0:
                        continue
                    union = np.logical_or(mi, mj).sum()
                    iou = inter / union if union > 0 else 0
                    if iou > 0.3:
                        if ia >= ja:
                            keep[j] = False
                        else:
                            keep[i] = False
                            break

            # Build final instance mask + overlay from kept masks
            label_counter = 0
            for idx, det in enumerate(detections):
                if not keep[idx]:
                    continue
                label_counter += 1
                m = det[5].astype(bool)
                instance_mask[m] = label_counter
                contours, _ = cv2.findContours(
                    m.astype(np.uint8), cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                cv2.drawContours(overlay, contours, -1, (0, 255, 0), 1)

            n_nuclei = label_counter

            # Save mask + overlay
            Image.fromarray(instance_mask).save(mask_dir / f"{out_stem}_mask.png")
            Image.fromarray(overlay).save(overlay_dir / f"{out_stem}_overlay.png")

            rows.append({
                "cohort": cohort,
                "image": img_path.name,
                "nucleus_count": n_nuclei,
            })
            print(f"  {out_stem}: {n_nuclei} nuclei")

    # Write CSV
    csv_path = RESULTS_DIR / "per_image_stats.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cohort", "image", "nucleus_count"])
        writer.writeheader()
        writer.writerows(rows)

    total = sum(r["nucleus_count"] for r in rows)
    print(f"\n  Total nuclei (YOLOv8): {total}")
    print(f"  Results: {RESULTS_DIR}")
    print(f"  CSV: {csv_path}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--step", choices=["convert", "train", "infer", "all"],
                        default="all", help="Which step to run (default: all)")
    parser.add_argument("--epochs", type=int, default=30,
                        help="Training epochs (default: 30)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Image size for training/inference (default: 640)")
    parser.add_argument("--batch", type=int, default=4,
                        help="Batch size for training (default: 4)")
    args = parser.parse_args()

    if args.step in ("convert", "all"):
        step_convert()
    if args.step in ("train", "all"):
        step_train(epochs=args.epochs, imgsz=args.imgsz, batch=args.batch)
    if args.step in ("infer", "all"):
        step_infer(imgsz=args.imgsz)


if __name__ == "__main__":
    main()
