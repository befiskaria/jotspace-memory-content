# Quickstart

You just cloned `jotspace-memory-content`. Here's what to do next.

## What you'll end up with

After running 2 commands, you'll have:

- `packs/memory-core-en.zip` (~12 MB) — upload to GitHub Releases v1
- `packs/memory-bundled-en.zip` (~3 MB) — extract into the JotSpace
  Android project's assets folder

That's it. The JotSpace app downloads the first zip from GitHub at
runtime; the second is bundled into the APK so the app works offline.

## Step 1 — One-time setup

Open a terminal in this repo:

```bash
# Install Python dependencies
pip install -r tools/requirements.txt
```

You need Python 3.10+. On Windows, run from PowerShell after installing
Python from python.org.

## Step 2 — Build the packs

```bash
python tools/fetch_and_build.py
```

This:
1. Downloads ~35 MB of OBS images from `cdn.door43.org` (cached after
   first run)
2. Extracts the 50 story illustrations
3. Resizes + converts to WebP
4. Writes 2 zip files to `packs/`
5. Updates `manifest-v1.json` with file sizes and SHA256 checksums

Expected runtime: 2-5 minutes (mostly the download).

## Step 3 — Verify

```bash
python tools/verify_pack.py
```

Should print "All checks passed ✓".

## Step 4 — Replace placeholders

Open `manifest-v1.json` and replace `REPLACE_OWNER` with your GitHub
username (e.g., `befin`). The URLs become:

```
https://github.com/befin/jotspace-memory-content/releases/download/v1/memory-core-en.zip
```

Same for `LICENSES.md` if linked from the manifest.

(I'll add a Python helper in a later release to auto-detect the GitHub
owner from `git remote get-url origin`. For now, manual edit is fine
— it's two strings.)

## Step 5 — Commit + push

```bash
git add manifest-v1.json
git commit -m "v1 manifest with pack sizes and SHA256"
git push origin main
```

## Step 6 — Create the GitHub release

1. Go to your repo on GitHub
2. Click **Releases → Draft a new release**
3. **Tag:** `v1`
4. **Title:** `Content Pack v1`
5. **Description:** paste the contents of `LICENSES.md`
6. **Attachments:** drag in `packs/memory-core-en.zip`
7. Click **Publish release**

After publishing, the URL in your manifest is live and downloadable
without authentication.

## Step 7 — Bundle into JotSpace

Extract `packs/memory-bundled-en.zip` into the JotSpace Android
project at:

```
app/src/main/assets/memory_kids_bundled/
```

This becomes part of the APK. The Memory Kids Trainer plugin reads
from this path on first launch so it has 12 stories ready even if
the user never downloads anything.

```bash
# In your JotSpace Android project:
mkdir -p app/src/main/assets/memory_kids_bundled
cd app/src/main/assets/memory_kids_bundled
unzip /path/to/jotspace-memory-content/packs/memory-bundled-en.zip
```

## Updating later (v2, v3, ...)

When you want to ship updated content:

1. Bump version everywhere:
   - `manifest-v1.json` → `manifest-v2.json`
   - `release_tag` field inside the manifest → `"v2"`
   - All URLs in the manifest → `releases/download/v2/...`

2. Re-run `python tools/fetch_and_build.py`
3. Create a new GitHub release tagged `v2` with the rebuilt zip
4. Ship a JotSpace app update that points to the new manifest version

The app handles version migration: it polls the manifest, sees the new
version, prompts the user to update content.

## Troubleshooting

**Build script can't download the OBS zip**

Check that `https://cdn.door43.org/obs/jpg/obs-images-360px.zip` is
reachable from your machine. Sometimes corporate networks block CDN
domains. Try from a personal connection.

**Pillow install fails on Windows**

Install Python from python.org (not the Microsoft Store version), then
reopen PowerShell and try `pip install -r tools/requirements.txt`.

**Zip is empty or wrong size**

Delete `source/obs/obs-images-360px.zip` and re-run. The download may
have been corrupted.

**Image filenames don't match the script's regex**

The script expects filenames like `obs-en-01-01.jpg` inside the bulk
zip. If unfoldingWord renames their format, the regex in
`extract_first_frames` needs updating. Inspect with:

```bash
unzip -l source/obs/obs-images-360px.zip | head -20
```
