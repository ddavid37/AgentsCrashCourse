#!/usr/bin/env python3
"""
CourseWorks File Watcher Agent
================================
Monitors Columbia CourseWorks (Canvas) for new files in COMS3261W - Computer Science Theory.
Downloads new files locally and sends an email notification via SendGrid.

Usage:
    python watcher.py            # Normal run: check for new files and download them
    python watcher.py --init     # First-time setup: catalog existing files WITHOUT downloading
                                 # Run this once before scheduling so you don't re-download everything
"""

import os
import sys
import json
import logging
import argparse
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


# ── Load .env from project root ──────────────────────────────────────────────
def find_and_load_dotenv() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / ".env"
        if candidate.exists():
            load_dotenv(candidate, override=True)
            return candidate
        current = current.parent
    load_dotenv(override=True)
    return None


find_and_load_dotenv()

# ── Config from environment ───────────────────────────────────────────────────
CANVAS_BASE     = "https://courseworks2.columbia.edu"
CANVAS_TOKEN    = os.getenv("CANVAS_API_TOKEN", "")
COURSE_ID       = os.getenv("CANVAS_COURSE_ID", "237725")
DOWNLOAD_DIR    = Path(os.getenv("DOWNLOAD_DIR", "/mnt/c/Users/97254/Desktop/Columbia/S26/COMS3261W - COMPUTER SCIENCE THEORY"))
TRACKING_FILE   = Path(__file__).parent / "downloaded_files.json"
LOG_FILE        = Path(__file__).parent / "watcher.log"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Canvas API helpers ────────────────────────────────────────────────────────
def canvas_headers() -> dict:
    return {"Authorization": f"Bearer {CANVAS_TOKEN}"}


def canvas_get_all(url: str, params: dict = None) -> list:
    """GET a paginated Canvas API endpoint and return all results."""
    results = []
    params = {**(params or {}), "per_page": 100}
    while url:
        resp = requests.get(url, headers=canvas_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Canvas sometimes returns a dict with an error key
        if isinstance(data, dict):
            log.warning(f"Unexpected dict response from {url}: {data}")
            break
        results.extend(data)
        url = resp.links.get("next", {}).get("url")
        params = {}   # pagination URL already contains params
    return results


def get_all_course_files() -> list[dict]:
    """Return every file in every folder of the course, with folder_path attached."""
    log.info(f"Fetching folder list for course {COURSE_ID}…")
    folders = canvas_get_all(f"{CANVAS_BASE}/api/v1/courses/{COURSE_ID}/folders")
    log.info(f"  Found {len(folders)} folder(s)")

    all_files = []
    for folder in folders:
        files = canvas_get_all(f"{CANVAS_BASE}/api/v1/folders/{folder['id']}/files")
        for f in files:
            f["_folder_full_name"] = folder.get("full_name", "")
            f["_folder_name"]      = folder.get("name", "")
        all_files.extend(files)

    log.info(f"  Found {len(all_files)} total file(s) across all folders")
    return all_files


# ── Tracking file ─────────────────────────────────────────────────────────────
def load_tracking() -> dict:
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE) as fh:
            return json.load(fh)
    return {}


def save_tracking(data: dict) -> None:
    with open(TRACKING_FILE, "w") as fh:
        json.dump(data, fh, indent=2)
    log.info(f"Tracking file updated: {TRACKING_FILE}")


# ── Download ──────────────────────────────────────────────────────────────────
def local_path_for(file_info: dict) -> Path:
    """
    Mirror the Canvas folder hierarchy under DOWNLOAD_DIR.
    'course files/Handouts/lecture1.pdf'  →  DOWNLOAD_DIR/Handouts/lecture1.pdf
    'course files/lecture1.pdf'           →  DOWNLOAD_DIR/lecture1.pdf
    """
    full_name: str = file_info["_folder_full_name"]
    # Strip the leading 'course files' segment Canvas always adds
    parts = [p for p in full_name.split("/") if p and p.lower() != "course files"]
    subfolder = Path(*parts) if parts else Path(".")
    return DOWNLOAD_DIR / subfolder / file_info["display_name"]


def ensure_dir(path: Path) -> None:
    """Create directory, falling back to cmd.exe if on a Windows-mounted path."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # /mnt/c paths sometimes need Windows-side mkdir
        import subprocess
        win_path = str(path).replace("/mnt/c/", "C:\\").replace("/", "\\")
        subprocess.run(["cmd.exe", "/c", "mkdir", win_path], check=False, capture_output=True)


def download_file(file_info: dict, dest: Path) -> None:
    ensure_dir(dest.parent)
    # Canvas redirects to an S3 URL; follow redirects, no auth needed after first hop
    resp = requests.get(
        file_info["url"],
        headers=canvas_headers(),
        stream=True,
        allow_redirects=True,
        timeout=60,
    )
    resp.raise_for_status()
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            fh.write(chunk)


# ── Main logic ────────────────────────────────────────────────────────────────
def run_init() -> None:
    """
    First-time setup mode: catalog every existing file so future runs only
    download files that are TRULY new. Nothing is downloaded during init.
    """
    log.info("=== INIT MODE: cataloging existing files (no downloads) ===")
    tracking = load_tracking()
    files = get_all_course_files()

    now = datetime.now().isoformat()
    added = 0
    for f in files:
        fid = str(f["id"])
        if fid not in tracking:
            tracking[fid] = {
                "name":           f["display_name"],
                "folder":         f["_folder_full_name"],
                "size_bytes":     f.get("size", 0),
                "canvas_updated": f.get("updated_at", ""),
                "cataloged_at":   now,
                "downloaded_at":  now,   # mark as handled so watcher skips these
            }
            added += 1

    save_tracking(tracking)
    log.info(f"=== Init complete: {added} file(s) cataloged, {len(tracking)} total in tracking ===")
    log.info("You can now schedule the watcher. Only files added AFTER this point will be downloaded.")


def run_check() -> None:
    """Normal mode: find new files, download them, send email notifications."""
    log.info("=== CourseWorks Watcher — checking for new files ===")

    if not CANVAS_TOKEN:
        log.error("CANVAS_API_TOKEN is not set. Check your .env file.")
        sys.exit(1)

    tracking = load_tracking()
    files = get_all_course_files()

    new_count = 0
    for file_info in files:
        fid = str(file_info["id"])
        already_downloaded = (
            fid in tracking and tracking[fid].get("downloaded_at") is not None
        )
        if already_downloaded:
            continue

        name   = file_info["display_name"]
        folder = file_info["_folder_full_name"]
        dest   = local_path_for(file_info)

        log.info(f"New file: '{name}'  (folder: {folder})")
        log.info(f"  Downloading to: {dest}")

        try:
            download_file(file_info, dest)
            size_kb = file_info.get("size", 0) / 1024
            log.info(f"  Download complete ({size_kb:.1f} KB)")
        except Exception as exc:
            log.error(f"  Download FAILED for '{name}': {exc}")
            continue

        # Update tracking
        tracking[fid] = {
            "name":           name,
            "folder":         folder,
            "size_bytes":     file_info.get("size", 0),
            "canvas_updated": file_info.get("updated_at", ""),
            "cataloged_at":   tracking.get(fid, {}).get("cataloged_at", datetime.now().isoformat()),
            "downloaded_at":  datetime.now().isoformat(),
            "local_path":     str(dest),
        }
        new_count += 1

    save_tracking(tracking)

    if new_count:
        log.info(f"=== Done: {new_count} new file(s) downloaded ===")
    else:
        log.info("=== Done: no new files found ===")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CourseWorks file watcher")
    parser.add_argument(
        "--init",
        action="store_true",
        help="First-time setup: catalog all existing files without downloading them.",
    )
    args = parser.parse_args()

    if args.init:
        run_init()
    else:
        run_check()
