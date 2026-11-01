# YOLO Label Review

English | [简体中文](README.zh-CN.md)

A desktop tool for reviewing YOLO object detection annotations. Inspect images, delete incorrect boxes, and draw missing boxes directly on the image. Every edit is saved automatically.

## Features

- English and Simplified Chinese UI, switchable without reopening the dataset.
- Hold **A** or **D** to browse backward or forward; release to stop.
- Select a box in the sidebar to highlight it, then press **Delete** to remove it.
- Drag with the left mouse button to add a box, including inside overlapping boxes.
- Immediate saves, original label backups, and undo/redo for the current image.
- Zoom, pan, jump to an image, and resume the last viewed image.
- Preserve class names and YOLO normalized coordinates. No model inference is required.

## Install

Requires Python **3.10+**, PyQt5, and a graphical desktop. Linux, Windows, and macOS can run PyQt5; local validation was performed on Linux. CI checks Python 3.10 and 3.12 on Linux.

Download or clone this repository, then open a terminal in its directory:

```bash
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on Linux/macOS or `.venv\Scripts\Activate.ps1` in Windows PowerShell. Then install from the local checkout:

```bash
python -m pip install .
```

## Run

```bash
yolo-review "/path/to/dataset" --lang en
yolo-review "/path/to/dataset" --lang zh
```

The equivalent module command is `python -m yolo_review "/path/to/dataset"`. If no path is provided, the current working directory is used. Paths containing spaces must be quoted. For a source checkout, `python review_annotations.py "/path/to/dataset"` also works after installing the dependencies in `requirements.txt`.

Use the **Language / 语言** selector at the top of the window to change language. The default `--lang auto` uses the dataset's saved language, then the system locale (Chinese for Chinese locales, English otherwise). An explicit `--lang en` or `--lang zh` takes precedence. Class names are never translated.

`yolo-review --help`, `yolo-review --lang zh --help`, and `yolo-review --version` work without opening a window.

## Dataset layout

```text
dataset/
├── images/
│   ├── frame001.png
│   └── train/frame002.jpg
├── labels/
│   ├── frame001.txt
│   └── train/frame002.txt
└── classes.txt
```

Images are discovered recursively in natural filename order. Labels match image paths relative to `images/`, with the extension changed to `.txt` under `labels/`. Supported image extensions are PNG, JPG/JPEG, BMP, WebP, and TIF/TIFF, subject to the installed Qt image plugins. `classes.txt` is UTF-8 with one class name per line, starting at class ID 0. Missing class names are shown as numeric class IDs with a localized label. The tool reads these folders directly and does not follow paths or split definitions in `data.yaml`.

Each label line must contain exactly:

```text
class_id x_center y_center width height
0 0.500000 0.500000 0.200000 0.100000
```

Coordinates are normalized to 0–1; sizes must be positive. This tool handles axis-aligned detection rectangles, not segmentation, pose, or oriented boxes. Missing labels load as empty and are created on the first edit. Deleting the last box leaves an empty label file. Malformed labels disable editing for that image and display an error instead of silently discarding data.

## Controls

| Action | Control |
| --- | --- |
| Previous / next image | A / D; hold to repeat using the OS keyboard repeat rate |
| Select and highlight | Click a row in the right sidebar |
| Delete selected box | Delete |
| Add box | Left mouse button + drag; release to save |
| Correct a box | Delete it and draw its replacement |
| Undo / redo | Ctrl+Z / Ctrl+Shift+Z or Ctrl+Y |
| Zoom / pan | Mouse wheel / middle mouse button + drag |
| Fit image | F |
| Cancel drawing / selection | Esc |
| Jump | Enter a 1-based image number, then Enter or Go |

Undo history is cleared when changing images. A drag must cover at least two source-image pixels in each dimension to create a box. Green boxes are existing labels, yellow marks the selection, and blue outlines the box being drawn.

## Saving and recovery

Every add, delete, undo, and redo writes the corresponding label file through a temporary file and atomic replacement. The UI only applies the edit after a successful save. Only one application window may edit the same dataset at a time. Revision checks detect label changes made by other programs; navigate away and back to reload after a conflict. This is not a multi-user annotation server.

Before the first edit to a label, its original contents are backed up to `.yolo_review/backups/labels/` with the same relative path. Subsequent edits do not replace that original backup. To restore it, close the reviewer and copy the backup over the matching file in `labels/`. A `.txt.missing` marker means no label originally existed; remove the newly created label file to restore that state.

`.yolo_review/state.json` stores position and language. Opening images, selecting boxes, and changing language do not rewrite labels. Automatic review backups are local to the dataset; copy them with the dataset if needed.

## Development and GitHub

See [CONTRIBUTING.md](CONTRIBUTING.md) for formatting, tests, architecture, and packaging. GitHub Actions runs checks on pushes and pull requests. All automated tests use temporary synthetic datasets.

Upload **this project directory**, which contains source code and documentation. Dataset images, labels, model files, local backups, environments, and build artifacts are excluded by `.gitignore`. To publish to your own empty GitHub repository, replace `YOUR_ACCOUNT` with your account:

```bash
git init -b main
git add .
git commit -m "Initial YOLO Label Review release"
git remote add origin https://github.com/YOUR_ACCOUNT/yolo-label-review.git
git push -u origin main
```

This project is not yet published to PyPI. Install from the repository or a locally built wheel.

## License

The project source is available under the [MIT License](LICENSE). Dependencies keep their own licenses: PyQt5 is provided under GPL v3 or a commercial license; this project's MIT license does not replace PyQt5's terms.
