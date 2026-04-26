# jotspace-memory-content

Content pack delivery repo for **JotSpace Memory Kids Trainer** plugin.

## What this repo does

Hosts the illustrations, text, and audio for Memory Kids Trainer as
versioned GitHub Releases. The JotSpace Android app downloads these
release assets on-demand at runtime.

This repo is **public** so GitHub Releases asset downloads are
unmetered for app users. Content is curated from sources with
explicit redistribution licenses (see `LICENSES.md`).

## Quick start (build a release)

```bash
# 1. Install Python 3.10+ and dependencies
pip install -r tools/requirements.txt

# 2. Run the builder. It fetches OBS assets, processes them, and
#    writes zip files to packs/.
python tools/fetch_and_build.py

# 3. Verify the output
ls -la packs/
# memory-core-en.zip       (~40 MB)
# memory-text-en.zip       (~50 KB)
# manifest-v1.json

# 4. Create a release on GitHub and upload packs/*.zip + manifest-v1.json
#    Tag: v1
#    Title: Content Pack v1
#    Body: paste contents of LICENSES.md
```

## Repo layout

```
.
├── README.md
├── LICENSES.md             ← consolidated license text for every source
├── manifest-v1.json        ← live manifest (also in each release)
├── tools/
│   ├── requirements.txt    ← Python deps (Pillow for resize)
│   ├── fetch_and_build.py  ← MAIN: fetch + process + zip
│   └── verify_pack.py      ← sanity-check a built pack
├── source/                 ← raw downloaded assets (gitignored)
│   ├── obs/
│   └── _staging/
└── packs/                  ← built zip files (gitignored)
```

## Why GitHub Releases?

- **Free**: unmetered egress for public repos. Indie-app friendly.
- **Stable**: tagged releases never disappear unless deleted.
- **Auditable**: anyone can inspect the source content.
- **Versioned**: app supports multiple manifest versions, cleanly upgrades.

## Updating content

Bump the version (v2, v3, ...). Re-run `fetch_and_build.py` with the
new version. Upload as a new release. The app's manifest poll will
detect the new version and prompt the user to update.

## Languages

Phase 1: English only.
Phase 2 (planned): Hindi (`hi`), Malayalam (`ml`).
Phase 3 (planned): Audio narration in `en`/`hi`/`ml`.

To add a new language to the build, see comments in `fetch_and_build.py`.

## License of THIS repo

The build scripts and manifest format are MIT.
The CONTENT in releases is governed by the upstream sources'
licenses — see `LICENSES.md` per asset.
