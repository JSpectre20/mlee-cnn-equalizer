"""Freeze arbitrary project artifacts into a versioned, read-only checkpoint folder.

Copies every given file or directory (paths relative to equalizer/, structure kept) into
checkpoints/<tag>/, writes MANIFEST.json (path, size, SHA-256 per file, note) and marks the
copies read-only. Refuses to overwrite an existing tag (same rule as freeze_checkpoints.py).

Usage:
    python scripts/freeze_artifacts.py --tag quant_v1 --note "..." results/quant rtl/gen
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("paths", nargs="+")
    args = ap.parse_args()
    dst = Path("checkpoints") / args.tag
    if dst.exists():
        raise SystemExit(f"{dst} already exists; refusing to overwrite (use a new tag)")
    files = []
    for p in map(Path, args.paths):
        if not p.exists():
            raise SystemExit(f"missing: {p}")
        files += [f for f in p.rglob("*") if f.is_file()] if p.is_dir() else [p]
    entries = []
    for f in sorted(files):
        out = dst / f
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        entries.append({"path": f.as_posix(), "bytes": f.stat().st_size, "sha256": sha256(out)})
    manifest = {"tag": args.tag, "created": datetime.datetime.now().isoformat(timespec="seconds"),
                "note": args.note, "sources": args.paths, "files": entries}
    (dst / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    for f in dst.rglob("*"):
        if f.is_file():
            os.chmod(f, stat.S_IREAD)
    print(f"froze {len(entries)} files into {dst}")


if __name__ == "__main__":
    main()
