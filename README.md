# Steam Profile Image Cutter

A Python tool that slices animated GIFs into Steam-ready profile showcase images — preserving full animation, frame timing, and loop settings.

## Versions

| Version | Interface | Notes |
|---------|-----------|-------|
| v1.1 | GUI + CLI | Drag-and-drop window, recommended |
| v1.0 | CLI only | Terminal only |

## Overview

Steam's profile showcase requires images to be uploaded as individual slotted pieces rather than a single wide image. This tool automates that process by taking any animated GIF, scaling it to the correct canvas dimensions, and cutting it into the exact slice sizes Steam expects — including the byte-level adjustment required for proper rendering on Steam's end.

Two display formats are supported:

| Mode | Layout | Use Case |
|------|--------|----------|
| 5-Slice | Five equal slices — `117×338` each | Workshop Showcase (5-slot) |
| 2-Slice | Side `100×930` + Middle `506×930` | Featured Artwork / 2-slot display |

## Requirements

- Python 3.8+
- [opencv-python](https://pypi.org/project/opencv-python/)
- [Pillow](https://pypi.org/project/Pillow/)
- [customtkinter](https://pypi.org/project/customtkinter/) *(v1.1 GUI only)*
- [tkinterdnd2](https://pypi.org/project/tkinterdnd2/) *(v1.1 drag-and-drop only)*

```bash
pip install opencv-python pillow customtkinter tkinterdnd2
```

## Installation

```bash
git clone https://github.com/Kahan64bit/Steam-Profile-Image-Cutter.git
cd Steam-Profile-Image-Cutter
pip install opencv-python pillow customtkinter tkinterdnd2
```

Or download the latest binary from the [Releases](https://github.com/Kahan64bit/Steam-Profile-Image-Cutter/releases) page — no Python required.

## Usage

### GUI (v1.1)

Run with no arguments to open the GUI:

```bash
python3 cutter.py
```

Or double-click the downloaded binary for your OS.

1. Drop your `.gif` onto the drop zone or click **Browse File**
2. Select a cut mode
3. Optionally change the output folder
4. Click **Slice GIF**

Progress and saved file names appear in the log at the bottom.

### CLI (v1.0)

```bash
python3 cutter.py <input.gif> [output_folder] [--mode 5|2]
```

**Examples:**

```bash
# 5-slice Workshop Showcase (default)
python3 cutter.py banner.gif

# 5-slice with explicit output folder
python3 cutter.py banner.gif ./output --mode 5

# 2-slice Featured Artwork layout
python3 cutter.py banner.gif ./output --mode 2
```

### Output

**5-Slice** produces five files named:
```
banner_slice_1.gif  banner_slice_2.gif  banner_slice_3.gif  banner_slice_4.gif  banner_slice_5.gif
```

**2-Slice** produces two files named:
```
banner_side.gif   banner_middle.gif
```

## Uploading to Steam

Once you have your slices, upload each one to Steam Workshop using the browser console trick:

1. Go to the Steam Workshop upload page
2. Open your browser's developer console (`F12` → Console tab)
3. Paste and run the following line for **Workshop Showcase** images:
   ```js
   $J('[name=consumer_app_id]').val(480);$J('[name=file_type]').val(0);$J('[name=visibility]').val(0);
   ```
   Or for **Featured Artwork** images:
   ```js
   $J('#image_width').val(1000).attr('id',''),$J('#image_height').val(1).attr('id','');
   ```
4. Upload each slice file and note the Workshop item ID
5. Add the IDs to your profile showcase slots in order

## How It Works

- **Frame preservation** — OpenCV reads every frame of the source GIF since Pillow has known compatibility issues with certain animated GIF encodings
- **Lanczos resampling** — Each frame is resized to the full target canvas using high-quality Lanczos interpolation before cropping
- **GIF trailer fix** — Steam rejects GIF files that contain data after the standard `0x3B` trailer byte. The tool replaces the trailer with `0x21` in-place rather than appending, which matches the byte structure Steam accepts

## License

MIT
