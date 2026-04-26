#!/usr/bin/env python3
"""
fetch_and_build.py — Build content packs for JotSpace Memory Kids Trainer.

Run from the repo root:
    python tools/fetch_and_build.py

What it does:
  1. Downloads the OBS images bulk zip from cdn.door43.org (~35 MB)
  2. Extracts the 50 first-frame images (one per chapter)
  3. Converts each to WebP at 720px (for the core pack) and 480px (for
     the bundled APK assets)
  4. Builds:
        packs/memory-core-en.zip      (50 × 720px WebP + manifest fragment)
        packs/memory-bundled-en.zip   (12 × 480px WebP + tiny manifest)
  5. Computes SHA256 for each pack and updates manifest-v1.json
  6. Prints a summary including upload instructions

This is idempotent — re-running re-fetches the zip only if missing,
re-derives images, rebuilds packs.
"""

import json
import os
import re
import shutil
import sys
import zipfile
import hashlib
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install -r tools/requirements.txt")
    sys.exit(1)

# --- Configuration ----------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "source"
STAGING_DIR = SOURCE_DIR / "_staging"
PACKS_DIR = REPO_ROOT / "packs"
MANIFEST_PATH = REPO_ROOT / "manifest-v1.json"

OBS_IMAGES_URL = "https://cdn.door43.org/obs/jpg/obs-images-360px.zip"
OBS_IMAGES_LOCAL = SOURCE_DIR / "obs" / "obs-images-360px.zip"

# Output WebP target widths
WIDTH_FULL = 720    # for memory-core-en.zip (server-distributed)
WIDTH_BUNDLED = 480 # for memory-bundled-en.zip (APK assets)
WEBP_QUALITY = 85   # quality 85 = visually lossless for illustrations

# --- Helpers ----------------------------------------------------------

def ensure_dirs():
    for p in [SOURCE_DIR / "obs", STAGING_DIR, PACKS_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def download_if_needed(url: str, dest: Path):
    """Download a URL to dest, skipping if already present and non-empty."""
    if dest.exists() and dest.stat().st_size > 1_000_000:
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  ✓ Already have {dest.name} ({size_mb:.1f} MB)")
        return

    print(f"  Downloading {url}")
    print(f"  → {dest}")
    print(f"  This is ~35 MB, please wait…")

    # Stream download with progress
    req = urllib.request.Request(url, headers={"User-Agent": "jotspace-memory-builder/1.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 64 * 1024
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  Progress: {pct}% ({downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB)", end="")
    print()
    print(f"  ✓ Downloaded {dest.stat().st_size // 1024 // 1024} MB")

def extract_first_frames(src_zip: Path, dst_dir: Path) -> dict:
    """
    Extract the first frame of each chapter (the canonical 'story' image).

    OBS image filenames in the bulk zip follow the pattern:
        obs-en-CC-FF.jpg    where CC = chapter (01-50), FF = frame (01-NN)

    We want CC-01 for each CC.

    Returns: {chapter_int: extracted_path}
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    found = {}

    with zipfile.ZipFile(src_zip, "r") as zf:
        names = zf.namelist()
        # Match files like ".../obs-en-01-01.jpg" — keep first frame only
        pattern = re.compile(r"obs-en-(\d{2})-01\.jpg$", re.IGNORECASE)
        for name in names:
            m = pattern.search(name)
            if not m:
                continue
            chapter = int(m.group(1))
            if chapter < 1 or chapter > 50:
                continue
            out_path = dst_dir / f"chapter_{chapter:02d}.jpg"
            with zf.open(name) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            found[chapter] = out_path

    if len(found) != 50:
        missing = sorted(set(range(1, 51)) - set(found.keys()))
        print(f"  ⚠ Extracted only {len(found)}/50 chapter frames")
        print(f"    Missing chapters: {missing}")
        # Don't fail — let the user inspect; they can re-run later.
    else:
        print(f"  ✓ Extracted all 50 first-frame images")

    return found

def to_webp(src_jpg: Path, dst_webp: Path, target_width: int):
    """Resize JPG to target_width and save as WebP at WEBP_QUALITY."""
    with Image.open(src_jpg) as im:
        im = im.convert("RGB")
        ratio = target_width / im.width
        new_h = int(round(im.height * ratio))
        im = im.resize((target_width, new_h), Image.LANCZOS)
        dst_webp.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst_webp, "WEBP", quality=WEBP_QUALITY, method=6)

def build_core_pack(chapter_jpgs: dict, manifest: dict) -> Path:
    """Build memory-core-en.zip with all 50 stories at 720px WebP plus
    a manifest fragment listing them."""
    out_zip = PACKS_DIR / "memory-core-en.zip"
    print(f"  Building {out_zip.name}")

    work_dir = STAGING_DIR / "core_en"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    # Convert each chapter's JPG to WebP under images/obs/
    for chapter in sorted(chapter_jpgs.keys()):
        src = chapter_jpgs[chapter]
        dst = work_dir / "images" / "obs" / f"story_{chapter:03d}.webp"
        to_webp(src, dst, WIDTH_FULL)

    # Write text/en/stories.json — verse refs + key text per story
    stories_text = []
    for s in manifest["stories"]:
        stories_text.append({
            "id":             s["id"],
            "chapter":        s["chapter"],
            "title_en":       s["title_en"],
            "key_verse_ref":  s["key_verse_ref"],
            "key_verse_en":   s["key_verse_en"],
            "image_path":     s["image_path"]
        })
    text_dir = work_dir / "text" / "en"
    text_dir.mkdir(parents=True, exist_ok=True)
    with open(text_dir / "stories.json", "w", encoding="utf-8") as f:
        json.dump({"version": 1, "language": "en", "stories": stories_text},
                  f, ensure_ascii=False, indent=2)

    # Write LICENSES.txt fragment
    license_text = (REPO_ROOT / "LICENSES.md").read_text(encoding="utf-8")
    (work_dir / "LICENSES.txt").write_text(license_text, encoding="utf-8")

    # Zip it up
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in work_dir.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(work_dir)
                zf.write(path, arcname)

    size_mb = out_zip.stat().st_size / (1024 * 1024)
    print(f"  ✓ {out_zip.name} = {size_mb:.1f} MB")
    return out_zip

def build_bundled_pack(chapter_jpgs: dict, manifest: dict) -> Path:
    """Build memory-bundled-en.zip with the 12 selected stories at 480px
    WebP. This is what JotSpace bundles inside its APK assets folder."""
    bundled_ids = manifest["bundled_story_ids"]
    bundled_chapters = sorted(int(s["chapter"]) for s in manifest["stories"]
                              if s["id"] in bundled_ids)

    out_zip = PACKS_DIR / "memory-bundled-en.zip"
    print(f"  Building {out_zip.name} (12 stories for APK)")

    work_dir = STAGING_DIR / "bundled_en"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    # 12 lightweight WebP images at 480px
    for chapter in bundled_chapters:
        if chapter not in chapter_jpgs:
            print(f"  ⚠ Chapter {chapter} missing from extracted set — skipping")
            continue
        src = chapter_jpgs[chapter]
        dst = work_dir / "images" / "obs" / f"story_{chapter:03d}.webp"
        to_webp(src, dst, WIDTH_BUNDLED)

    # Tiny manifest for the bundled set
    bundled_manifest = {
        "version": 1,
        "language": "en",
        "stories": [
            {
                "id":             s["id"],
                "chapter":        s["chapter"],
                "title_en":       s["title_en"],
                "key_verse_ref":  s["key_verse_ref"],
                "key_verse_en":   s["key_verse_en"],
                "image_path":     f"images/obs/story_{int(s['chapter']):03d}.webp"
            }
            for s in manifest["stories"] if s["id"] in bundled_ids
        ]
    }
    (work_dir / "manifest_bundled.json").write_text(
        json.dumps(bundled_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Brief LICENSES.txt
    bundled_license = """JotSpace Memory Kids Trainer — Bundled Content

Images: Sweet Publishing / Open Bible Stories (unfoldingWord)
License: CC BY-SA 4.0
Source:  https://openbiblestories.org

Full license text and attribution: see app's "Image Sources & Credits"
screen, or the GitHub repo at:
https://github.com/REPLACE_OWNER/jotspace-memory-content/blob/main/LICENSES.md
"""
    (work_dir / "LICENSES.txt").write_text(bundled_license, encoding="utf-8")

    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in work_dir.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(work_dir)
                zf.write(path, arcname)

    size_mb = out_zip.stat().st_size / (1024 * 1024)
    print(f"  ✓ {out_zip.name} = {size_mb:.2f} MB (this goes inside the APK)")
    return out_zip

def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def update_manifest(core_pack: Path, bundled_pack: Path, manifest: dict):
    """Update manifest-v1.json with real sizes + SHA256 for the built packs."""
    core_size = core_pack.stat().st_size
    core_sha = sha256_of_file(core_pack)

    if "core_en" in manifest["packs"]:
        manifest["packs"]["core_en"]["size_bytes_estimate"] = core_size
        manifest["packs"]["core_en"]["sha256"] = core_sha

    # The bundled pack isn't a release asset — it's bundled into the APK.
    # We still record its hash for app-side integrity checks.
    manifest["bundled_pack_sha256"] = sha256_of_file(bundled_pack)
    manifest["bundled_pack_size_bytes"] = bundled_pack.stat().st_size

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Updated manifest-v1.json")

def main():
    print("=" * 60)
    print("JotSpace Memory Kids Trainer — Content Pack Builder")
    print("=" * 60)
    print()

    print("Step 1: Setup")
    ensure_dirs()
    print(f"  Working in: {REPO_ROOT}")
    print()

    print("Step 2: Fetch OBS images (cached after first run)")
    download_if_needed(OBS_IMAGES_URL, OBS_IMAGES_LOCAL)
    print()

    print("Step 3: Extract first-frame images (one per chapter)")
    extracted_dir = STAGING_DIR / "obs_jpgs"
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    chapter_jpgs = extract_first_frames(OBS_IMAGES_LOCAL, extracted_dir)
    print()

    if not chapter_jpgs:
        print("ERROR: No images extracted. The OBS zip filename pattern may have changed.")
        print(f"Inspect the zip's contents:  unzip -l {OBS_IMAGES_LOCAL}")
        sys.exit(1)

    print("Step 4: Load manifest")
    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} not found")
        sys.exit(1)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(f"  ✓ Loaded with {len(manifest['stories'])} stories defined")
    print()

    print("Step 5: Build packs")
    core_pack = build_core_pack(chapter_jpgs, manifest)
    bundled_pack = build_bundled_pack(chapter_jpgs, manifest)
    print()

    print("Step 6: Update manifest with sizes & SHA256")
    update_manifest(core_pack, bundled_pack, manifest)
    print()

    print("=" * 60)
    print("DONE.")
    print("=" * 60)
    print()
    print("Built artifacts:")
    print(f"  packs/memory-core-en.zip         ← upload to GitHub Release v1")
    print(f"  packs/memory-bundled-en.zip      ← extract into JotSpace APK assets")
    print(f"  manifest-v1.json                  ← upload to release + commit to repo")
    print()
    print("Next steps:")
    print("  1. Replace 'REPLACE_OWNER' in manifest-v1.json with your GitHub username")
    print("     (e.g., 'befin'). Same for LICENSES.md if linked from the manifest.")
    print()
    print("  2. Commit & push:")
    print("       git add manifest-v1.json")
    print("       git commit -m 'v1: pack sizes + SHA256'")
    print("       git push origin main")
    print()
    print("  3. Create a GitHub release tagged 'v1' and upload:")
    print("       packs/memory-core-en.zip")
    print("       manifest-v1.json")
    print()
    print("  4. Extract memory-bundled-en.zip into the JotSpace project at:")
    print("       app/src/main/assets/memory_kids_bundled/")
    print("     (this becomes part of the APK)")
    print()

if __name__ == "__main__":
    main()
