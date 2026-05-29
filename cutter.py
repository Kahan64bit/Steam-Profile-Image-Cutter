#!/usr/bin/env python3
"""
cutter.py  —  Steam Profile Image Cutter
GUI + CLI tool to slice animated GIFs into Steam showcase pieces.

Requires: opencv-python, Pillow, customtkinter, tkinterdnd2
    pip install opencv-python pillow customtkinter tkinterdnd2
"""

import sys
import threading
import cv2
from pathlib import Path
from PIL import Image

# ── Slice configs ─────────────────────────────────────────────────────────────
MODES = {
    "5": {
        "label": "5-Slice  —  Workshop Showcase  (155×450 each)",
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
        "label": "2-Slice  —  Featured Artwork  (side + middle)",
        "slices": [
            {"name": "side",   "w": 100},
            {"name": "middle", "w": 506},
        ],
        "h": 930,
    },
}
# ──────────────────────────────────────────────────────────────────────────────


def read_gif_frames(path: str):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open: {path}")
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
    pil_frames = [
        Image.fromarray(f).convert("P", palette=Image.ADAPTIVE, colors=256)
        for f in frames_rgb
    ]
    pil_frames[0].save(
        out_path, format="GIF", save_all=True,
        append_images=pil_frames[1:], duration=duration_ms, loop=0, optimize=False,
    )
    with open(out_path, "r+b") as f:
        f.seek(-1, 2)
        if f.read(1) == b"\x3b":
            f.seek(-1, 2)
            f.write(b"\x21")


def slice_gif(input_path: str, output_dir: str, mode: str, log_fn=print) -> None:
    cfg     = MODES[mode]
    slices  = cfg["slices"]
    total_h = cfg["h"]
    total_w = sum(s["w"] for s in slices)
    src     = Path(input_path)
    out     = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    log_fn(f"Reading frames from {src.name} ...")
    frames, duration_ms = read_gif_frames(str(src))
    log_fn(f"  {len(frames)} frames @ {duration_ms}ms each")

    log_fn(f"Resizing to {total_w}x{total_h} ...")
    resized = [
        cv2.resize(f, (total_w, total_h), interpolation=cv2.INTER_LANCZOS4)
        for f in frames
    ]

    log_fn("Slicing ...")
    x0 = 0
    for s in slices:
        x1 = x0 + s["w"]
        strip_frames = [f[:, x0:x1, :] for f in resized]
        out_path = out / f"{src.stem}_{s['name']}.gif"
        frames_to_animated_gif(strip_frames, out_path, duration_ms)
        log_fn(f"  OK  {out_path.name}  ({s['w']}x{total_h})")
        x0 = x1

    log_fn(f"\nDone!  {len(slices)} slices saved to:\n{out.resolve()}")


# ================================================================================
#  GUI
# ================================================================================

def launch_gui() -> None:
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import filedialog

    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        USE_DND = True
    except ImportError:
        USE_DND = False

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    BG       = "#0f0f0f"
    SURFACE  = "#1a1a1a"
    BORDER   = "#2a2a2a"
    ACCENT   = "#c8a97e"
    ACCENT2  = "#e8c9a0"
    TEXT     = "#e8e8e8"
    TEXT_DIM = "#666666"
    SUCCESS  = "#4caf7d"
    ERROR    = "#e05c5c"
    MONO     = ("Courier New", 11)

    root = TkinterDnD.Tk() if USE_DND else tk.Tk()
    root.title("Steam Profile Image Cutter")
    root.geometry("620x700")
    root.resizable(False, False)
    root.configure(bg=BG)
    root.update_idletasks()
    root.geometry(f"620x700+{(root.winfo_screenwidth()-620)//2}+{(root.winfo_screenheight()-700)//2}")

    selected_file   = tk.StringVar()
    selected_output = tk.StringVar()
    selected_mode   = tk.StringVar(value="5")

    def set_input(path: str):
        path = path.strip().strip("{}")
        if Path(path).suffix.lower() != ".gif":
            drop_label.configure(text="  Only .gif files are supported", fg=ERROR)
            return
        selected_file.set(path)
        drop_label.configure(text=f"  {Path(path).name}", fg=SUCCESS)
        default_out = str(Path(path).parent / "slices")
        selected_output.set(default_out)
        out_label.configure(text=default_out, fg=TEXT)

    def browse_input():
        p = filedialog.askopenfilename(title="Select GIF",
            filetypes=[("GIF files", "*.gif"), ("All files", "*.*")])
        if p:
            set_input(p)

    def browse_output():
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            selected_output.set(p)
            out_label.configure(text=p, fg=TEXT)

    def log(msg: str):
        log_box.configure(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    def run_slice():
        inp  = selected_file.get()
        out  = selected_output.get()
        mode = selected_mode.get()
        if not inp:
            log("  No file selected.")
            return
        if not out:
            log("  No output folder selected.")
            return
        run_btn.configure(state="disabled", text="Processing...")
        log_box.configure(state="normal")
        log_box.delete("1.0", "end")
        log_box.configure(state="disabled")

        def worker():
            try:
                slice_gif(inp, out, mode, log_fn=log)
            except Exception as e:
                log(f"\nError: {e}")
            finally:
                run_btn.configure(state="normal", text="   Slice GIF")

        threading.Thread(target=worker, daemon=True).start()

    pad = {"padx": 24}

    # Title
    tf = tk.Frame(root, bg=BG)
    tf.pack(fill="x", pady=(28, 0), **pad)
    tk.Label(tf, text="STEAM  PROFILE", font=("Georgia", 10, "bold"),
             fg=ACCENT, bg=BG).pack(anchor="w")
    tk.Label(tf, text="Image Cutter", font=("Georgia", 26, "bold"),
             fg=TEXT, bg=BG).pack(anchor="w")

    tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(12, 20))

    # Drop zone
    drop_outer = tk.Frame(root, bg=BORDER)
    drop_outer.pack(fill="x", **pad, pady=(0, 4))
    drop_inner = tk.Frame(drop_outer, bg=SURFACE)
    drop_inner.pack(fill="x", padx=1, pady=1)

    drop_label = tk.Label(drop_inner,
        text="Drop your .gif here   or   click Browse",
        font=("Georgia", 12), fg=TEXT_DIM, bg=SURFACE, pady=28, cursor="hand2")
    drop_label.pack(fill="x")

    if USE_DND:
        for w in (drop_outer, drop_inner, drop_label):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>", lambda e: set_input(e.data))

    drop_label.bind("<Button-1>", lambda e: browse_input())
    drop_inner.bind("<Button-1>", lambda e: browse_input())

    ctk.CTkButton(root, text="Browse File", width=120, height=32,
        fg_color=SURFACE, hover_color=BORDER, border_color=BORDER, border_width=1,
        text_color=ACCENT, font=("Georgia", 11), command=browse_input,
    ).pack(anchor="e", padx=24, pady=(4, 20))

    # Mode
    tk.Label(root, text="CUT MODE", font=("Courier New", 9, "bold"),
             fg=ACCENT, bg=BG).pack(anchor="w", **pad)

    mf = tk.Frame(root, bg=BG)
    mf.pack(fill="x", **pad, pady=(8, 20))
    for key, cfg in MODES.items():
        rb_outer = tk.Frame(mf, bg=BORDER)
        rb_outer.pack(fill="x", pady=4)
        rb_inner = tk.Frame(rb_outer, bg=SURFACE)
        rb_inner.pack(fill="x", padx=1, pady=1)
        ctk.CTkRadioButton(rb_inner, text=cfg["label"],
            variable=selected_mode, value=key,
            font=("Georgia", 12), text_color=TEXT,
            fg_color=ACCENT, hover_color=ACCENT2,
        ).pack(anchor="w", padx=16, pady=12)

    # Output folder
    oh = tk.Frame(root, bg=BG)
    oh.pack(fill="x", **pad)
    tk.Label(oh, text="OUTPUT FOLDER", font=("Courier New", 9, "bold"),
             fg=ACCENT, bg=BG).pack(side="left")
    ctk.CTkButton(oh, text="Change", width=70, height=24,
        fg_color=SURFACE, hover_color=BORDER, border_color=BORDER, border_width=1,
        text_color=TEXT_DIM, font=("Courier New", 10), command=browse_output,
    ).pack(side="right")

    out_label = tk.Label(root, text="Auto-set when file is chosen",
        font=MONO, fg=TEXT_DIM, bg=BG, anchor="w", wraplength=570)
    out_label.pack(fill="x", **pad, pady=(6, 20))

    # Run button
    run_btn = ctk.CTkButton(root, text="   Slice GIF", height=48,
        fg_color=ACCENT, hover_color=ACCENT2, text_color="#0f0f0f",
        font=("Georgia", 14, "bold"), command=run_slice)
    run_btn.pack(fill="x", **pad, pady=(0, 16))

    # Log
    tk.Label(root, text="LOG", font=("Courier New", 9, "bold"),
             fg=ACCENT, bg=BG).pack(anchor="w", **pad)
    log_box = ctk.CTkTextbox(root, height=140, fg_color=SURFACE, text_color=TEXT,
        font=MONO, border_color=BORDER, border_width=1, state="disabled")
    log_box.pack(fill="x", **pad, pady=(6, 24))

    root.mainloop()


# ================================================================================
#  Entry point
# ================================================================================

def pause() -> None:
    if sys.platform == "win32":
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]

    if not args:
        launch_gui()
    else:
        mode = "5"
        if "--mode" in args:
            idx  = args.index("--mode")
            mode = args[idx + 1]
            args = args[:idx] + args[idx + 2:]

        input_file    = args[0]
        output_folder = args[1] if len(args) > 1 else str(Path.cwd() / "slices")

        try:
            slice_gif(input_file, output_folder, mode)
        except Exception as e:
            print(f"[ERROR] {e}")
            pause()
            sys.exit(1)

        pause()
