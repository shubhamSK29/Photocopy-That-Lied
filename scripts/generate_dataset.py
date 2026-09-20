"""Generate a clearly-labelled SYNTHETIC demo/development dataset.

No real crop photographs are shipped with this prototype, so this script renders
controlled synthetic "field" scenes and then produces:

  authentic/                 - base renders (label 0)
  natural_variants/          - legitimate processing of the base renders (label 0)
  hard_cases/                - genuine images that look suspicious (label 0)
  copy_move/                 - a region duplicated inside the image (label 1)
  splicing/                  - content pasted in from a different source (label 1)
  manipulated_recompressed/  - manipulations that were then recompressed (label 1)
  timestamp_overlay/         - genuine images with a burned-in timestamp (label 0)

Every manifest row records source_id / session / device_domain so that variants of
the same source image can be kept in the same train/test split.

All of this data is SYNTHETIC and is only suitable for development and
demonstration. Metrics computed on it must not be presented as validation on
real-world crop-insurance photographs.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"
DATASET_VERSION = "dataset-synthetic-v1"

# Pseudo device domains with different sensor noise / sharpening behaviour.
DEVICES = [
    {"id": "phoneA_flagship", "noise": 1.5, "sharpen": 0.2, "jpeg": 92, "size": (1600, 1200), "tier": "high"},
    {"id": "phoneB_midrange", "noise": 3.0, "sharpen": 0.5, "jpeg": 85, "size": (1440, 1080), "tier": "mid"},
    {"id": "phoneC_midrange", "noise": 2.5, "sharpen": 0.4, "jpeg": 88, "size": (1280, 960), "tier": "mid"},
    {"id": "phoneD_budget", "noise": 6.0, "sharpen": 1.1, "jpeg": 72, "size": (1024, 768), "tier": "low"},
    {"id": "phoneE_budget", "noise": 7.5, "sharpen": 1.4, "jpeg": 65, "size": (960, 720), "tier": "low"},
    {"id": "phoneF_old", "noise": 9.0, "sharpen": 0.9, "jpeg": 60, "size": (800, 600), "tier": "low"},
]

SCENES = ["crop_rows", "leaf_canopy", "flooded_field", "dry_patch", "lodged_crop"]
LIGHTING = ["bright", "overcast", "golden", "lowlight"]


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def render_scene(scene: str, lighting: str, size: tuple[int, int], seed: int) -> np.ndarray:
    w, h = size
    rng = _rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    base = np.zeros((h, w, 3), dtype=np.float32)

    palette = {
        "crop_rows": (70, 140, 60),
        "leaf_canopy": (50, 120, 45),
        "flooded_field": (95, 110, 90),
        "dry_patch": (150, 140, 80),
        "lodged_crop": (110, 130, 70),
    }[scene]
    for c in range(3):
        base[..., c] = palette[c]

    if scene == "crop_rows":
        # Rows converge with depth so the pattern is not perfectly periodic.
        depth = np.clip(y / h, 0.05, 1.0)
        period = rng.uniform(16, 32) * depth
        angle = rng.uniform(-0.25, 0.25)
        rows = np.sin((x * np.sin(angle) + y * np.cos(angle)) * 2 * np.pi / period)
        base[..., 1] += rows * 26 * depth
        base[..., 0] += rows * 12 * depth
    elif scene == "leaf_canopy":
        for _ in range(int(w * h / 900)):
            cx, cy = rng.integers(0, w), rng.integers(0, h)
            r = int(rng.integers(6, 22))
            color = (
                float(palette[0] + rng.normal(0, 18)),
                float(palette[1] + rng.normal(0, 26)),
                float(palette[2] + rng.normal(0, 14)),
            )
            cv2.ellipse(base, (int(cx), int(cy)), (r, int(r * 0.6)),
                        float(rng.uniform(0, 180)), 0, 360, color, -1)
    elif scene == "flooded_field":
        ripple = np.sin(x / rng.uniform(9, 16)) * np.cos(y / rng.uniform(11, 20))
        base += ripple[..., None] * 16
        base[int(h * 0.55):, 2] += 25
    elif scene == "dry_patch":
        blotch = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 25)
        base += (blotch * 60)[..., None]
    else:  # lodged_crop
        streaks = np.sin((x * 0.6 + y * 1.7) / rng.uniform(12, 26))
        base[..., 1] += streaks * 22
        base[..., 0] += streaks * 18

    # Scene clutter: distinct local objects (leaves, clods, stones, puddles).
    for _ in range(int(w * h / 9000)):
        cx, cy = int(rng.integers(0, w)), int(rng.integers(int(h * 0.2), h))
        r = int(rng.integers(5, max(8, int(min(w, h) * 0.05))))
        luma = float(rng.normal(0, 28))
        color = tuple(
            float(np.clip(palette[c] + luma + rng.normal(0, 9), 10, 245)) for c in range(3)
        )
        shape = rng.integers(0, 3)
        if shape == 0:
            cv2.ellipse(base, (cx, cy), (r, max(2, int(r * rng.uniform(0.3, 0.9)))),
                        float(rng.uniform(0, 180)), 0, 360, color, -1)
        elif shape == 1:
            pts = np.array(
                [[cx + int(rng.normal(0, r)), cy + int(rng.normal(0, r))] for _ in range(5)],
                dtype=np.int32,
            )
            cv2.fillPoly(base, [pts], color)
        else:
            cv2.line(base, (cx, cy), (cx + int(rng.normal(0, r * 2)), cy + int(rng.normal(0, r * 2))),
                     color, max(1, r // 4))

    # Texture + soil speckle.
    texture = cv2.GaussianBlur(rng.normal(0, 1, (h, w, 3)).astype(np.float32), (0, 0), 1.2) * 12
    base += texture

    # A smooth random warp keeps periodic structures from repeating exactly, as in
    # real photographs with perspective and irregular growth.
    warp = cv2.GaussianBlur(rng.normal(0, 1, (h, w, 2)).astype(np.float32), (0, 0), 60) * 900
    map_x = np.clip(x + warp[..., 0], 0, w - 1)
    map_y = np.clip(y + warp[..., 1], 0, h - 1)
    base = cv2.remap(base, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # Lighting / vignetting.
    gain = {"bright": 1.18, "overcast": 0.92, "golden": 1.05, "lowlight": 0.55}[lighting]
    base *= gain
    if lighting == "golden":
        base[..., 0] *= 1.12
        base[..., 2] *= 0.88
    vignette = 1.0 - 0.35 * (((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    base *= np.clip(vignette, 0.4, 1.0)[..., None]

    # A horizon strip so scenes are not perfectly homogeneous.
    horizon = int(h * rng.uniform(0.12, 0.25))
    base[:horizon] = base[:horizon] * 0.5 + np.array([150, 170, 195], dtype=np.float32) * 0.5
    return np.clip(base, 0, 255).astype(np.uint8)


def apply_camera(rgb: np.ndarray, device: dict, seed: int) -> np.ndarray:
    rng = _rng(seed)
    out = rgb.astype(np.float32)
    out += rng.normal(0, device["noise"], out.shape)
    if device["sharpen"] > 0:
        blur = cv2.GaussianBlur(out, (0, 0), 1.2)
        out = out + device["sharpen"] * (out - blur)
    if device["tier"] == "low":  # aggressive denoise then sharpen, as budget ISPs do
        out = cv2.bilateralFilter(np.clip(out, 0, 255).astype(np.uint8), 7, 45, 45).astype(np.float32)
        blur = cv2.GaussianBlur(out, (0, 0), 1.0)
        out = out + 0.6 * (out - blur)
    return np.clip(out, 0, 255).astype(np.uint8)


def save_jpeg(path: Path, rgb: np.ndarray, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(path, "JPEG", quality=int(quality))


def copy_move(rgb: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = _rng(seed)
    h, w = rgb.shape[:2]
    out = rgb.copy()
    pw, ph = int(w * rng.uniform(0.12, 0.2)), int(h * rng.uniform(0.12, 0.2))
    sx, sy = int(rng.integers(0, w - pw)), int(rng.integers(int(h * 0.3), h - ph))
    for _ in range(12):
        dx, dy = int(rng.integers(0, w - pw)), int(rng.integers(int(h * 0.3), h - ph))
        if abs(dx - sx) > pw * 1.4 or abs(dy - sy) > ph * 1.4:
            break
    patch = out[sy:sy + ph, sx:sx + pw].copy()
    mask = np.zeros((ph, pw), dtype=np.float32)
    cv2.ellipse(mask, (pw // 2, ph // 2), (int(pw * 0.45), int(ph * 0.45)), 0, 0, 360, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), max(2.0, pw * 0.03))[..., None]
    region = out[dy:dy + ph, dx:dx + pw].astype(np.float32)
    out[dy:dy + ph, dx:dx + pw] = np.clip(
        region * (1 - mask) + patch.astype(np.float32) * mask, 0, 255
    ).astype(np.uint8)
    
    # Ground-truth binary mask (1 for manipulated destination region, 0 elsewhere)
    full_mask = np.zeros((h, w), dtype=np.uint8)
    full_mask[dy:dy + ph, dx:dx + pw] = (mask[..., 0] > 0.1).astype(np.uint8)
    return out, full_mask


def splice(rgb: np.ndarray, donor: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = _rng(seed)
    h, w = rgb.shape[:2]
    out = rgb.copy()
    pw, ph = int(w * rng.uniform(0.15, 0.25)), int(h * rng.uniform(0.15, 0.25))
    donor_resized = cv2.resize(donor, (pw, ph))
    # A different processing history for the pasted content.
    donor_resized = cv2.GaussianBlur(donor_resized, (0, 0), 0.7)
    donor_resized = np.clip(
        donor_resized.astype(np.float32) + _rng(seed + 1).normal(0, 4.5, donor_resized.shape), 0, 255
    ).astype(np.uint8)
    # Pasted content normally arrives from a separately compressed file, so it carries
    # its own JPEG history.
    quality = int(rng.integers(55, 75))
    ok, buf = cv2.imencode(".jpg", donor_resized[..., ::-1], [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if ok:
        donor_resized = cv2.imdecode(buf, cv2.IMREAD_COLOR)[..., ::-1]
    dx, dy = int(rng.integers(0, w - pw)), int(rng.integers(int(h * 0.3), h - ph))
    mask = np.zeros((ph, pw), dtype=np.float32)
    cv2.ellipse(mask, (pw // 2, ph // 2), (int(pw * 0.42), int(ph * 0.42)), 0, 0, 360, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), max(2.0, pw * 0.02))[..., None]
    region = out[dy:dy + ph, dx:dx + pw].astype(np.float32)
    out[dy:dy + ph, dx:dx + pw] = np.clip(
        region * (1 - mask) + donor_resized.astype(np.float32) * mask, 0, 255
    ).astype(np.uint8)
    
    # Ground-truth binary mask (1 for spliced region, 0 elsewhere)
    full_mask = np.zeros((h, w), dtype=np.uint8)
    full_mask[dy:dy + ph, dx:dx + pw] = (mask[..., 0] > 0.1).astype(np.uint8)
    return out, full_mask


def add_timestamp(rgb: np.ndarray, text: str) -> np.ndarray:
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    size = max(18, image.size[0] // 28)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except OSError:
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), text, font=font)
    x = image.size[0] - (box[2] - box[0]) - 16
    y = image.size[1] - (box[3] - box[1]) - 18
    draw.rectangle([x - 8, y - 6, x + (box[2] - box[0]) + 8, y + (box[3] - box[1]) + 8], fill=(0, 0, 0))
    draw.text((x, y), text, fill=(255, 210, 60), font=font)
    return np.array(image)


def natural_variant(rgb: np.ndarray, kind: str, device: dict, seed: int) -> tuple[np.ndarray, int]:
    """Return (image, jpeg_quality) for a legitimate processing variant."""
    rng = _rng(seed)
    image = Image.fromarray(rgb)
    quality = device["jpeg"]
    if kind == "resize":
        factor = float(rng.uniform(0.45, 0.8))
        image = image.resize((int(image.width * factor), int(image.height * factor)), Image.LANCZOS)
    elif kind == "jpeg_recompress":
        quality = int(rng.integers(55, 78))
    elif kind == "messaging_compression":
        factor = float(rng.uniform(0.4, 0.6))
        image = image.resize((int(image.width * factor), int(image.height * factor)), Image.LANCZOS)
        quality = int(rng.integers(45, 65))
    elif kind == "screenshot":
        canvas = Image.new("RGB", (1080, 1920), (18, 18, 20))
        scaled = image.resize((1080, int(image.height * 1080 / image.width)), Image.LANCZOS)
        canvas.paste(scaled, (0, 420))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, 1080, 60], fill=(10, 10, 12))
        draw.text((24, 20), "9:41", fill=(240, 240, 240))
        image = canvas
        quality = 90
    elif kind == "sharpen":
        image = ImageEnhance.Sharpness(image).enhance(float(rng.uniform(1.8, 3.0)))
    elif kind == "denoise":
        arr = cv2.fastNlMeansDenoisingColored(np.array(image), None, 7, 7, 7, 21)
        image = Image.fromarray(arr)
    elif kind == "brightness":
        image = ImageEnhance.Brightness(image).enhance(float(rng.uniform(0.7, 1.35)))
    elif kind == "contrast":
        image = ImageEnhance.Contrast(image).enhance(float(rng.uniform(0.75, 1.4)))
    elif kind == "color_enhance":
        image = ImageEnhance.Color(image).enhance(float(rng.uniform(1.2, 1.8)))
    return np.array(image), quality


NATURAL_KINDS = [
    "resize", "jpeg_recompress", "messaging_compression", "screenshot",
    "sharpen", "denoise", "brightness", "contrast", "color_enhance",
]

HARD_CASES = [
    "repetitive_rows", "repetitive_leaves", "strong_shadows", "lowlight",
    "motion_blur", "heavy_sharpening", "heavy_denoise", "heavy_jpeg",
    "screenshot", "resized", "metadata_wiped",
]


def hard_case(rgb: np.ndarray, kind: str, device: dict, seed: int) -> tuple[np.ndarray, int]:
    rng = _rng(seed)
    quality = device["jpeg"]
    out = rgb.copy()
    h, w = out.shape[:2]
    if kind == "repetitive_rows":
        tile = out[: h // 4, : w // 4]
        out = np.tile(tile, (4, 4, 1))[:h, :w]
    elif kind == "repetitive_leaves":
        tile = out[: h // 3, : w // 3]
        out = np.tile(tile, (3, 3, 1))[:h, :w]
    elif kind == "strong_shadows":
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        shadow = (np.sin(xx / 90.0) > 0.2).astype(np.float32) * 0.55 + 0.45
        out = np.clip(out.astype(np.float32) * shadow[..., None], 0, 255).astype(np.uint8)
    elif kind == "lowlight":
        out = np.clip(out.astype(np.float32) * 0.35 + rng.normal(0, 9, out.shape), 0, 255).astype(np.uint8)
    elif kind == "motion_blur":
        kernel = np.zeros((15, 15), np.float32)
        kernel[7, :] = 1.0 / 15
        out = cv2.filter2D(out, -1, kernel)
    elif kind == "heavy_sharpening":
        blur = cv2.GaussianBlur(out.astype(np.float32), (0, 0), 1.5)
        out = np.clip(out.astype(np.float32) + 2.2 * (out.astype(np.float32) - blur), 0, 255).astype(np.uint8)
    elif kind == "heavy_denoise":
        out = cv2.fastNlMeansDenoisingColored(out, None, 16, 16, 7, 21)
    elif kind == "heavy_jpeg":
        quality = 32
    elif kind == "screenshot":
        out, quality = natural_variant(out, "screenshot", device, seed)
    elif kind == "resized":
        out, quality = natural_variant(out, "resize", device, seed)
    elif kind == "metadata_wiped":
        quality = device["jpeg"]
    return out, quality


def build(count_per_device: int, out_dir: Path) -> Path:
    if out_dir.exists():
        for sub in ("authentic", "natural_variants", "copy_move", "splicing",
                    "timestamp_overlay", "manipulated_recompressed", "hard_cases"):
            shutil.rmtree(out_dir / sub, ignore_errors=True)
    rows: list[dict] = []
    random.seed(11)
    seed = 0
    donors: list[np.ndarray] = []

    for device in DEVICES:
        for i in range(count_per_device):
            seed += 1
            scene = SCENES[(i + len(donors)) % len(SCENES)]
            lighting = LIGHTING[(i + DEVICES.index(device)) % len(LIGHTING)]
            session = f"{device['id']}_s{i % 3}"
            source_id = f"{device['id']}_{i:03d}"
            scene_rgb = render_scene(scene, lighting, device["size"], seed)
            captured = apply_camera(scene_rgb, device, seed)
            donors.append(cv2.resize(captured, (320, 240)))

            masks_dir = out_dir / "masks"
            masks_dir.mkdir(parents=True, exist_ok=True)

            def record(category: str, name: str, image: np.ndarray, quality: int,
                       label: int, transformation: str, mask: Optional[np.ndarray] = None) -> None:
                path = out_dir / category / f"{name}.jpg"
                save_jpeg(path, image, quality)
                mask_rel = ""
                if mask is not None:
                    mask_path = masks_dir / f"{name}_mask.png"
                    Image.fromarray(mask.astype(np.uint8)).save(mask_path)
                    mask_rel = str(mask_path.relative_to(out_dir))
                rows.append(
                    {
                        "image_path": str(path.relative_to(out_dir)),
                        "path": str(path.relative_to(out_dir)),  # backwards-compatible alias
                        "category": category,
                        "label": label,
                        "mask_path": mask_rel,
                        "manipulation_type": transformation,
                        "transformation": transformation,
                        "source_id": source_id,
                        "parent_id": source_id,
                        "session_id": session,
                        "session": session,
                        "device_id": device["id"],
                        "device_domain": device["id"],
                        "device_tier": device["tier"],
                        "scene": scene,
                        "lighting": lighting,
                        "synthetic": True,
                        "dataset_version": DATASET_VERSION,
                    }
                )

            record("authentic", f"{source_id}_original", captured, device["jpeg"], 0, "original")

            for kind in random.sample(NATURAL_KINDS, 4):
                img, q = natural_variant(captured, kind, device, seed + hash(kind) % 1000)
                record("natural_variants", f"{source_id}_{kind}", img, q, 0, kind)

            for kind in random.sample(HARD_CASES, 3):
                img, q = hard_case(captured, kind, device, seed + hash(kind) % 997)
                record("hard_cases", f"{source_id}_{kind}", img, q, 0, f"hard_{kind}")

            stamped = add_timestamp(captured, "20/08/2026 14:32")
            record("timestamp_overlay", f"{source_id}_timestamp", stamped, device["jpeg"], 0, "timestamp_overlay")

            cm_img, cm_mask = copy_move(captured, seed + 31)
            record("copy_move", f"{source_id}_copy_move", cm_img, device["jpeg"], 1, "copy_move", cm_mask)

            donor = donors[(len(donors) * 7) % len(donors)]
            sp_img, sp_mask = splice(captured, donor, seed + 57)
            record("splicing", f"{source_id}_splice", sp_img, device["jpeg"], 1, "splice", sp_mask)

            if i % 2 == 0:
                recomp_src, recomp_mask_src = cm_img, cm_mask
            else:
                recomp_src, recomp_mask_src = sp_img, sp_mask
            
            recomp_img = cv2.resize(recomp_src, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA)
            recomp_mask = cv2.resize(recomp_mask_src, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_NEAREST)
            record(
                "manipulated_recompressed",
                f"{source_id}_manip_recompressed",
                recomp_img,
                50,
                1,
                "manipulated_recompressed",
                recomp_mask,
            )

    manifest_dir = out_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    csv_path = manifest_dir / "dataset.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (manifest_dir / "dataset.json").write_text(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "synthetic": True,
                "warning": (
                    "SYNTHETIC development data. Metrics computed on this dataset do not "
                    "represent performance on real crop-insurance photographs."
                ),
                "count": len(rows),
                "image_count": len(rows),
                "class_counts": {"genuine": sum(r["label"] == 0 for r in rows), "manipulated": sum(r["label"] == 1 for r in rows)},
                "source_count": len({r["source_id"] for r in rows}),
                "parent_count": len({r["parent_id"] for r in rows}),
                "devices": DEVICES,
                "rows": rows,
            },
            indent=2,
        )
    )
    return csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-device", type=int, default=8)
    parser.add_argument("--out", type=Path, default=DATASET)
    args = parser.parse_args()
    path = build(args.per_device, args.out)
    print(f"Wrote manifest: {path}")


if __name__ == "__main__":
    main()
