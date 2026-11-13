cat << 'EOF' > ~/DataSaverVideoFinder/README.md
# DataSaverVideoFinder

**DataSaverVideoFinder** is a lightweight, CPU-friendly Python utility that crawls local or network-mounted (NFS/SMB/ZFS) media libraries for video files exceeding a configurable size threshold, prioritizes MP4-containing folders, and generates an interactive nested HTML tree (or Word `.docx` report) with persistent browser checkboxes to track processed folders.

## Quick Start

### Run with Python
```bash
pip install -r requirements.txt
python3 data_saver_video_finder.py /path/to/media --min-size-mb 500 -o video_tree.html
```

### Run with Rootless Podman
```bash
podman build -t data-saver-video-finder .
podman run --rm --userns=keep-id --group-add=keep-groups --cpus="0.15" --memory="256m" \
  -v /path/to/media:/media:ro -v "\$PWD":/output \
  data-saver-video-finder /media --min-size-mb 500 -o /output/video_tree.html
```
EOF
