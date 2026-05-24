#!/usr/bin/env python3
"""
slice_5_vertical.py
--------------------
Cuts an animated (or static) GIF into vertical slices, preserving all
frames, timing, and loop settings.

Requires: opencv-python, Pillow
    pip install opencv-python pillow

Modes:
  --mode 5    Five equal slices of 155×450 each  (default)
  --mode 2    Two slices: 100×930 (side) + 506×930 (middle)

Usage:
    python3 slice_5_vertical.py <input.gif> [output_folder] [--mode 5|2]

Examples:
    python3 slice_5_vertical.py banner.gif
    python3 slice_5_vertical.py banner.gif ./out --mode 2
    python3 slice_5_vertical.py banner.gif ./out --mode 5
"""

import sys
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

# ── Slice configs ─────────────────────────────────────────────────────────────
MODES = {
    "5": {
        "slices": [
            {"name": "slice_1", "w": 155},
            {"name": "slice_2", "w": 155},
            {"name": "slice_3", "w": 155},
            {"name": "slice_4", "w": 155},
            {"name": "slice_5", "w": 155},
        ],
        "h": 450,
    },
    "2": {
        "slices": [
            {"name": "side",   "w": 100},
            {"name": "middle", "w": 506},
        ],
        "h": 930,
    },
}
# ──────────────────────────────────────────────────────────────────────────────


def read_gif_frames(path: str):
    """Read all frames from a GIF via OpenCV. Returns (frames_rgb, duration_ms)."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open: {path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    duration_ms = int(round(1000 / fps)) if fps and fps > 0 else 30

    frames = []
    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            break
        frames.append(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

    cap.release()
    return frames, duration_ms


def frames_to_animated_gif(frames_rgb, out_path: Path, duration_ms: int) -> None:
    """Save a list of RGB numpy arrays as an animated GIF."""
    pil_frames = []
    for f in frames_rgb:
        img = Image.fromarray(f).convert("P", palette=Image.ADAPTIVE, colors=256)
        pil_frames.append(img)

    pil_frames[0].save(
        out_path,
        format="GIF",
        save_all=True,
        append_images=pil_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )

    # Replace GIF trailer (0x3B) with 0x21 — matches hexed.it behaviour.
    # Appending after 0x3B causes Steam to reject the file; replacing it works.
    with open(out_path, "r+b") as f:
        f.seek(-1, 2)
        if f.read(1) == b"\x3b":
            f.seek(-1, 2)
            f.write(b"\x21")


def slice_gif(input_path: str, output_dir: str, mode: str) -> None:
    if mode not in MODES:
        print(f"[ERROR] Invalid mode '{mode}'. Choose 2 or 5.")
        sys.exit(1)

    cfg     = MODES[mode]
    slices  = cfg["slices"]
    total_h = cfg["h"]
    total_w = sum(s["w"] for s in slices)

    src = Path(input_path)
    if not src.exists():
        print(f"[ERROR] File not found: {src}")
        sys.exit(1)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Mode: {mode}-slice  |  target canvas: {total_w}×{total_h}")
    print(f"Reading frames from {src.name} ...")
    frames, duration_ms = read_gif_frames(str(src))
    print(f"  {len(frames)} frames @ {duration_ms}ms each")

    # Resize every frame to the full canvas size
    print(f"Resizing frames to {total_w}×{total_h} ...")
    resized = [
        cv2.resize(f, (total_w, total_h), interpolation=cv2.INTER_LANCZOS4)
        for f in frames
    ]

    stem = src.stem
    x0 = 0
    for s in slices:
        x1 = x0 + s["w"]
        strip_frames = [f[:, x0:x1, :] for f in resized]

        out_path = out / f"{stem}_{s['name']}.gif"
        frames_to_animated_gif(strip_frames, out_path, duration_ms)

        print(f"  Saved → {out_path}  ({s['w']}×{total_h})  [0x3B → 0x21]")
        x0 = x1

    print(f"\nDone! {len(slices)} slices written to: {out.resolve()}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    mode = "5"
    if "--mode" in args:
        idx = args.index("--mode")
        mode = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    input_file    = args[0]
    output_folder = args[1] if len(args) > 1 else str(Path(input_file).parent / "slices")

    slice_gif(input_file, output_folder, mode)
