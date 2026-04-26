#!/usr/bin/env python3
"""
verify_pack.py — Sanity check a built content pack.

Run after fetch_and_build.py to confirm everything is in order:
    python tools/verify_pack.py
"""

import json
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = REPO_ROOT / "packs"
MANIFEST_PATH = REPO_ROOT / "manifest-v1.json"

def check_core():
    pack = PACKS_DIR / "memory-core-en.zip"
    if not pack.exists():
        print("✗ memory-core-en.zip not found. Run fetch_and_build.py first.")
        return False

    issues = []
    with zipfile.ZipFile(pack, "r") as zf:
        names = set(zf.namelist())

        # All 50 story images must be present
        for ch in range(1, 51):
            expected = f"images/obs/story_{ch:03d}.webp"
            if expected not in names:
                issues.append(f"  ✗ missing {expected}")

        # text/en/stories.json must be present
        if "text/en/stories.json" not in names:
            issues.append("  ✗ missing text/en/stories.json")
        else:
            try:
                data = json.loads(zf.read("text/en/stories.json"))
                if len(data.get("stories", [])) < 50:
                    issues.append(f"  ✗ stories.json has only {len(data.get('stories', []))} entries")
            except json.JSONDecodeError as e:
                issues.append(f"  ✗ stories.json invalid: {e}")

        # LICENSES.txt must be present
        if "LICENSES.txt" not in names:
            issues.append("  ✗ missing LICENSES.txt")

    size_mb = pack.stat().st_size / (1024 * 1024)
    print(f"memory-core-en.zip — {size_mb:.1f} MB, {len(names)} files")
    if issues:
        print("Issues found:")
        for issue in issues:
            print(issue)
        return False
    print("  ✓ All 50 story images present")
    print("  ✓ text/en/stories.json valid")
    print("  ✓ LICENSES.txt present")
    return True

def check_bundled():
    pack = PACKS_DIR / "memory-bundled-en.zip"
    if not pack.exists():
        print("✗ memory-bundled-en.zip not found.")
        return False

    issues = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    bundled_chapters = sorted(int(s["chapter"]) for s in manifest["stories"]
                              if s["id"] in manifest["bundled_story_ids"])

    with zipfile.ZipFile(pack, "r") as zf:
        names = set(zf.namelist())
        for ch in bundled_chapters:
            expected = f"images/obs/story_{ch:03d}.webp"
            if expected not in names:
                issues.append(f"  ✗ missing {expected}")

    size_mb = pack.stat().st_size / (1024 * 1024)
    print(f"memory-bundled-en.zip — {size_mb:.2f} MB, {len(names)} files")
    if issues:
        print("Issues found:")
        for issue in issues:
            print(issue)
        return False
    print(f"  ✓ All {len(bundled_chapters)} bundled story images present")
    return True

def main():
    print("Verifying built packs...\n")
    ok_core = check_core()
    print()
    ok_bundled = check_bundled()
    print()
    if ok_core and ok_bundled:
        print("All checks passed ✓")
        sys.exit(0)
    else:
        print("Some checks failed ✗")
        sys.exit(1)

if __name__ == "__main__":
    main()
