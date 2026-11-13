# DataSaverVideoFinder

**DataSaverVideoFinder** is a lightweight, CPU-friendly Python utility that crawls local or network-mounted (NFS/SMB/ZFS) media libraries for video files exceeding a configurable size threshold, prioritizes MP4-containing folders, and generates an interactive nested HTML tree (or Word `.docx` report) with persistent browser checkboxes to track processed folders.

## Features
- **Video-Only Filtering:** Ignores subtitles, images, and `.nfo` metadata, counting only video files (`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.ts`, `.mpg`, `.mpeg`).
- **Format Prioritization:** Flags and sorts folders containing `.mp4` files to the top of the report.
- **Interactive Nested HTML Tree:** Self-contained dark-mode HTML output with live search filtering, keyboard-friendly expand/collapse, and persistent browser checkboxes (`localStorage`) to track processed folders.
- **Low-Impact Crawling:** Uses `os.scandir()` to minimize `stat()` calls over network mounts and includes configurable per-entry micro-sleep throttling (`--sleep`) so busy media servers stay responsive.
- **Clean One-Shot Execution:** Runs as a single-pass task—not a lingering background daemon. Once it finishes scanning and writes your report, it cleans up its checkpoint file and exits completely, freeing all CPU and RAM.
- **Crash-Resilient Checkpointing:** Periodically saves progress to a JSON checkpoint file and automatically resumes if interrupted.

## Quick Start

### 1. Run with Python
No external dependencies are required for HTML output. Install `python-docx` only if you want `.docx` export:

```bash
pip install -r requirements.txt
python3 data_saver_video_finder.py /path/to/media --min-size-mb 500 -o video_tree.html
```

### 2. Run with Rootless Podman (with Hard CPU/RAM Caps)
Build the image:
```bash
podman build -t data-saver-video-finder .
```

Run a read-only scan capped at 15% of a single CPU core and 256 MB RAM:
```bash
podman run --rm \
  --userns=keep-id \
  --group-add=keep-groups \
  --cpus="0.15" \
  --memory="256m" \
  -v /path/to/media:/media:ro \
  -v "\$PWD":/output \
  data-saver-video-finder /media --min-size-mb 500 -o /output/video_tree.html
```


> **Note:** No waste, `DataSaverVideoFinder` is a one-shot batch utility. Once the scan completes and your `.html` or `.docx` file is saved, the container exits and automatically removes itself (`--rm`), leaving zero background processes behind.

## CLI Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `target_dir` | *(Required)* | Directory path to crawl |
| `-s`, `--min-size-mb` | `500` | Minimum video file size in MB to flag a folder |
| `-o`, `--output` | `video_tree.html` | Output filename (`.html` or `.docx`) |
| `--sleep` | `0.002` | Seconds to pause per directory entry to prevent CPU spikes |
| `--checkpoint` | `scan_checkpoint.json` | Path for resume state file (pass `""` to disable) |

## AI Disclosure
This project was developed collaboratively with AI assistance (Google Gemini) for code architecture correction & HTML/CSS tree generation. All code has been reviewed, tested, and verified on a live Linux/ZFS media environment.

## License
Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
