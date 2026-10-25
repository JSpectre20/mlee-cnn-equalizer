"""Freeze the trained FP32 models into a versioned, read-only checkpoint folder.

Copies results/imdd_dse/models/*.pt (and the Proakis-B CNNs) into
checkpoints/<tag>/, writes a manifest with config, loss, seed, fresh-test BER
and SHA-256 of every file, and marks the files read-only. Later steps
(quantization, HLS/RTL export) must load from here and write new files
elsewhere, never overwrite these.

Usage:
    python scripts/freeze_checkpoints.py --tag fp32_v1
"""
import argparse
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
    ap.add_argument("--tag", default="fp32_v1")
    args = ap.parse_args()
    dst = Path("checkpoints") / args.tag
    if dst.exists():
        raise SystemExit(f"{dst} already exists; pick a new tag instead of overwriting a frozen set")
    dst.mkdir(parents=True)

    confirm = {}
    p = Path("results/imdd_dse/confirm.jsonl")
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            confirm[r["key"]] = r

    entries = []
    for src in sorted(Path("results/imdd_dse/models").glob("*.pt")):
        out = dst / "imdd" / src.name
        out.parent.mkdir(exist_ok=True)
        shutil.copy2(src, out)
        r = confirm.get(src.stem, {})
        entries.append({"file": str(out.relative_to(dst)), "channel": "imdd_40GBd_31.5km_snr24", "key": src.stem,
                        "cfg": {k: r.get(k) for k in ("vp", "layers", "kernel", "channels")}, "loss": r.get("loss"),
                        "seed": r.get("seed"), "ber_fresh_test": r.get("ber"), "macs_per_symbol": r.get("macs"),
                        "sha256": sha256(out)})
    for src in sorted(Path("results/proakis").glob("cnn_*.pt")):
        out = dst / "proakis" / src.name
        out.parent.mkdir(exist_ok=True)
        shutil.copy2(src, out)
        entries.append({"file": str(out.relative_to(dst)), "channel": "proakis_b_snr20", "key": src.stem, "sha256": sha256(out)})
    for data in ("train.npz", "test.npz", "test_fresh.npz", "config.json"):
        src = Path("results/imdd_dse") / data
        if src.exists():
            out = dst / "imdd_data" / data
            out.parent.mkdir(exist_ok=True)
            shutil.copy2(src, out)
            entries.append({"file": str(out.relative_to(dst)), "kind": "dataset", "sha256": sha256(out)})

    manifest = {"tag": args.tag, "note": "FP32 models before any quantization. Read-only; do not modify.", "files": entries}
    (dst / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    for f in dst.rglob("*"):
        if f.is_file():
            os.chmod(f, stat.S_IREAD)
    print(f"froze {len(entries)} files into {dst}")


if __name__ == "__main__":
    main()
