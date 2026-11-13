
#!/usr/bin/env python3
"""
DataSaverVideoFinder
Crawls a media directory for video files exceeding a configurable size threshold,
prioritizes MP4-containing folders, and exports a nested HTML or DOCX tree
with persistent progress checkboxes.
"""

import os
import json
import time
import html
import argparse
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv',
    '.flv', '.webm', '.m4v', '.ts', '.mpg', '.mpeg'
}


def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def load_checkpoint(checkpoint_path):
    if checkpoint_path and os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"[RESUME] {len(data['visited'])} folders scanned, {len(data['results'])} matches.")
                return set(data["visited"]), data["results"]
        except Exception as e:
            print(f"[WARN] Could not read checkpoint ({e}), starting fresh.")
    return set(), []


def save_checkpoint(checkpoint_path, visited, results):
    if not checkpoint_path:
        return
    tmp_file = f"{checkpoint_path}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump({"visited": list(visited), "results": results}, f)
    os.replace(tmp_file, checkpoint_path)


def scan_directory(base_path, size_threshold, sleep_sec=0.002, checkpoint_path=None):
    visited, results = load_checkpoint(checkpoint_path)
    folders_processed = len(visited)
    start_time = time.time()
    stack = [str(base_path)]

    while stack:
        current_path = stack.pop()
        video_files = []
        subdirs = []
        total_video_size = 0
        has_large_video = False
        has_mp4 = False

        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    if sleep_sec > 0:
                        time.sleep(sleep_sec)

                    if entry.is_dir(follow_symlinks=False):
                        subdirs.append(entry.path)
                    elif entry.is_file(follow_symlinks=False) and current_path not in visited:
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in VIDEO_EXTENSIONS:
                            size = entry.stat().st_size
                            is_mp4 = (ext == '.mp4')
                            total_video_size += size
                            if size > size_threshold:
                                has_large_video = True
                            if is_mp4:
                                has_mp4 = True

                            video_files.append({
                                "name": entry.name,
                                "size": size,
                                "is_mp4": is_mp4
                            })
        except PermissionError:
            print(f"[SKIP] Permission Denied: {current_path}")
            continue
        except OSError as e:
            print(f"[WARN] OS error on {current_path}: {e}")
            continue

        for d in sorted(subdirs, reverse=True):
            stack.append(d)

        if current_path not in visited:
            visited.add(current_path)
            folders_processed += 1

            if has_large_video:
                video_files.sort(key=lambda f: (not f["is_mp4"], f["name"].lower()))
                rel_path = os.path.relpath(current_path, base_path)
                results.append({
                    "folder": rel_path if rel_path != "." else os.path.basename(base_path),
                    "total_size": total_video_size,
                    "file_count": len(video_files),
                    "has_mp4": has_mp4,
                    "files": video_files
                })

            if folders_processed % 500 == 0:
                elapsed = int(time.time() - start_time)
                print(f"[PROGRESS] {folders_processed} folders | {len(results)} matches | {elapsed}s")

            if checkpoint_path and folders_processed % 250 == 0:
                save_checkpoint(checkpoint_path, visited, results)

    results.sort(key=lambda x: (not x["has_mp4"], x["folder"].lower()))
    return results


def build_nested_tree(results):
    root = {"children": {}, "files": [], "meta": "", "has_mp4": False}
    for item in results:
        parts = Path(item["folder"]).parts
        node = root
        for part in parts:
            if part not in node["children"]:
                node["children"][part] = {"children": {}, "files": [], "meta": "", "has_mp4": False}
            node = node["children"][part]
            if item["has_mp4"]:
                node["has_mp4"] = True
        node["meta"] = f"({item['file_count']} videos, {format_size(item['total_size'])})"
        node["has_mp4"] = item["has_mp4"]
        node["files"] = item["files"]
    return root


def export_html(results, output_path, min_mb):
    tree = build_nested_tree(results)
    threshold_bytes = min_mb * 1024 * 1024

    def render(name, node, path_prefix="", is_root=False):
        full_key = f"{path_prefix}/{name}" if path_prefix else name
        mp4_badge = '<span class="badge mp4">MP4</span>' if node["has_mp4"] else ""
        meta_html = f'<span class="meta">{html.escape(node["meta"])}</span>' if node["meta"] else ""
        sorted_children = sorted(
            node["children"].items(),
            key=lambda item: (not item[1]["has_mp4"], item[0].lower())
        )
        children_html = "".join(render(k, v, "" if is_root else full_key) for k, v in sorted_children)

        files_html = ""
        if node["files"]:
            items = []
            for f in node["files"]:
                is_large = f["size"] > threshold_bytes
                cls = " ".join(c for c in ["large" if is_large else "", "mp4-file" if f["is_mp4"] else ""] if c)
                badge = f'<span class="badge large">&gt;{min_mb:g}MB</span>' if is_large else ""
                items.append(f'<li class="{cls}">🎬 {html.escape(f["name"])} ({format_size(f["size"])}) {badge}</li>')
            files_html = f'<ul class="file-list">{"".join(items)}</ul>'

        if is_root:
            return children_html
        open_attr = " open" if node["has_mp4"] else ""
        safe_key = html.escape(full_key, quote=True)
        return f"""<details{open_attr} data-key="{safe_key}">
        <summary>
            <input type="checkbox" class="done-cb" data-key="{safe_key}" aria-label="Mark {html.escape(name, quote=True)} as processed" onclick="event.stopPropagation(); toggleDone(this)">
            <span class="folder-label">📁 <strong>{html.escape(name)}</strong> {mp4_badge} {meta_html}</span>
        </summary>
        <div class="branch">{children_html}{files_html}</div></details>"""

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>DataSaverVideoFinder (&gt;{min_mb:g} MB)</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #121212; color: #e0e0e0; padding: 20px; line-height: 1.5; }}
  h1 {{ color: #ffffff; border-bottom: 1px solid #333; padding-bottom: 10px; }}
  .controls {{ margin-bottom: 15px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
  button, input[type="text"] {{ background: #1e1e1e; color: #fff; border: 1px solid #444; padding: 8px 12px; border-radius: 6px; font-size: 14px; }}
  button:hover {{ background: #2d2d2d; cursor: pointer; }}
  input[type="text"] {{ width: 260px; }}
  .status-pill {{ color: #9cdcfe; font-size: 14px; margin-left: auto; }}
  details {{ margin: 4px 0; }}
  summary {{ cursor: pointer; padding: 4px 6px; border-radius: 4px; list-style: none; display: flex; align-items: center; gap: 8px; }}
  summary::-webkit-details-marker {{ display: none; }}
  summary:hover, summary:focus {{ background: #252526; outline: 1px solid #555; }}
  .done-cb {{ width: 16px; height: 16px; accent-color: #2ea043; cursor: pointer; flex-shrink: 0; }}
  details.completed > summary .folder-label {{ text-decoration: line-through; opacity: 0.5; }}
  body.hide-completed details.completed {{ display: none; }}
  .branch {{ margin-left: 22px; padding-left: 12px; border-left: 1px solid #333; }}
  .meta {{ color: #9cdcfe; font-size: 0.9em; margin-left: 6px; }}
  .file-list {{ list-style: none; padding-left: 0; margin: 4px 0 8px 0; font-family: monospace; font-size: 13px; }}
  .file-list li {{ padding: 2px 4px; color: #cccccc; }}
  .file-list li.mp4-file {{ color: #4fc1ff; font-weight: bold; }}
  .badge {{ font-size: 11px; padding: 1px 6px; border-radius: 4px; font-weight: bold; margin-left: 6px; }}
  .badge.mp4 {{ background: #005a9e; color: #fff; }}
  .badge.large {{ background: #8a3b08; color: #ffd8b8; }}
</style></head><body>
<h1>DataSaverVideoFinder (Files &gt; {min_mb:g} MB) — {len(results)} Matching Folders</h1>
<div class="controls">
  <input type="text" id="search" placeholder="Filter folders or files..." onkeyup="filterTree()">
  <button onclick="document.querySelectorAll('#tree details').forEach(d=>d.open=true)">Expand All</button>
  <button onclick="document.querySelectorAll('#tree details').forEach(d=>d.open=false)">Collapse All</button>
  <button id="toggleHideBtn" onclick="toggleHideCompleted()">Hide Completed</button>
  <button onclick="clearProgress()">Reset Checkboxes</button>
  <span class="status-pill" id="progressText">0 checked</span>
</div>
<div id="tree">{render("Root", tree, is_root=True)}</div>
<script>
const STORAGE_KEY = 'dsvf_checked_' + document.title;
let checkedState = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}');

function updateCounter() {{
  const topTotal = document.querySelectorAll('#tree > details').length;
  const topDone = document.querySelectorAll('#tree > details.completed').length;
  document.getElementById('progressText').textContent = `${{topDone}} / ${{topTotal}} top folders completed`;
}}

function applyState() {{
  document.querySelectorAll('.done-cb').forEach(cb => {{
    const isDone = !!checkedState[cb.dataset.key];
    cb.checked = isDone;
    const details = cb.closest('details');
    details.classList.toggle('completed', isDone);
    if (isDone) details.open = false;
  }});
  updateCounter();
}}

function toggleDone(cb) {{
  const key = cb.dataset.key;
  const details = cb.closest('details');
  if (cb.checked) {{
    checkedState[key] = true;
    details.classList.add('completed');
    details.open = false;
  }} else {{
    delete checkedState[key];
    details.classList.remove('completed');
  }}
  localStorage.setItem(STORAGE_KEY, JSON.stringify(checkedState));
  updateCounter();
}}

function toggleHideCompleted() {{
  const hidden = document.body.classList.toggle('hide-completed');
  document.getElementById('toggleHideBtn').textContent = hidden ? 'Show Completed' : 'Hide Completed';
}}

function clearProgress() {{
  if (!confirm('Clear all saved checkboxes for this report?')) return;
  checkedState = {{}};
  localStorage.removeItem(STORAGE_KEY);
  applyState();
}}

function filterTree() {{
  const q = document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('#tree > details').forEach(top => {{
    const match = top.textContent.toLowerCase().includes(q);
    top.style.display = match ? '' : 'none';
    if (q && match && !top.classList.contains('completed')) {{
      top.querySelectorAll('details').forEach(d => d.open = true);
    }}
  }});
}}

applyState();
</script></body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"[DONE] Saved HTML tree to {output_path}")


def export_docx(results, output_path, min_mb):
    if not HAS_DOCX:
        raise RuntimeError("python-docx is not installed. Run: pip install python-docx")
    threshold_bytes = min_mb * 1024 * 1024
    doc = Document()
    doc.add_heading(f"DataSaverVideoFinder (Folders with Videos > {min_mb:g} MB)", level=1)

    for item in results:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        mp4_tag = " [CONTAINS MP4]" if item["has_mp4"] else ""
        r = p.add_run(f"📁 {item['folder']}{mp4_tag} ({item['file_count']} videos, {format_size(item['total_size'])})")
        r.bold = True
        if item["has_mp4"]:
            r.font.color.rgb = RGBColor(0, 102, 204)

        for idx, f in enumerate(item["files"]):
            branch = "└── " if idx == len(item["files"]) - 1 else "├── "
            pf = doc.add_paragraph()
            pf.paragraph_format.left_indent = Pt(18)
            pf.paragraph_format.space_after = Pt(1)
            flag = f" [>{min_mb:g}MB]" if f["size"] > threshold_bytes else ""
            fr = pf.add_run(f"{branch}{f['name']} ({format_size(f['size'])}){flag}")
            fr.font.name = "Consolas"
            fr.font.size = Pt(9)
            if f["is_mp4"]:
                fr.bold = True

    doc.save(output_path)
    print(f"[DONE] Saved DOCX report to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        prog="DataSaverVideoFinder",
        description="Crawl a media directory for large video files to identify transcoding or cleanup candidates."
    )
    parser.add_argument("target_dir", help="Path to the media directory to scan")
    parser.add_argument("-s", "--min-size-mb", type=float, default=500.0, help="Minimum file size in MB (default: 500)")
    parser.add_argument("-o", "--output", default="video_tree.html", help="Output file path (.html or .docx)")
    parser.add_argument("--sleep", type=float, default=0.002, help="Sleep seconds per entry for CPU throttling (default: 0.002)")
    parser.add_argument("--checkpoint", default="scan_checkpoint.json", help="Checkpoint JSON path (pass '' to disable)")
    args = parser.parse_args()

    threshold_bytes = int(args.min_size_mb * 1024 * 1024)
    print(f"[START] Scanning {args.target_dir} for videos > {args.min_size_mb:g} MB...")
    results = scan_directory(args.target_dir, threshold_bytes, args.sleep, args.checkpoint or None)

    if args.output.lower().endswith(".docx"):
        export_docx(results, args.output, args.min_size_mb)
    else:
        export_html(results, args.output, args.min_size_mb)

    if args.checkpoint and os.path.exists(args.checkpoint):
        os.remove(args.checkpoint)
        print("[CLEANUP] Removed temporary checkpoint file.")


if __name__ == "__main__":
    main()

