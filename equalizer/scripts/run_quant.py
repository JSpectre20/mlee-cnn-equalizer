"""Bit-width sweep: PTQ and QAT of the frozen FP32 CNNs, scored with the integer golden model.

Loads from checkpoints/fp32_v1 (read-only) and writes only to results/quant/.
For each model and bit width b (weights = activations = input = b bits):
  PTQ  calibrate step sizes on a training batch, no training
  QAT  LSQ fine-tuning from the calibrated model (Adam, --iters)
and reports the BER of the *integer* model (exact RTL arithmetic) on the fresh test set.

Usage:
    python scripts/run_quant.py --bits 8 6 5 4 --iters 4000 --workers 6
"""
import argparse
import json
import multiprocessing as mp
import pickle
import time
from pathlib import Path

import numpy as np
import torch

from eqsim.data import load_dataset
from eqsim.equalizers import NeyCNN
from eqsim.quant import QuantNeyCNN, export_integer, integer_ber
from eqsim.train import train_sgd

CK = Path("checkpoints/fp32_v1")
MODELS = {  # best seed per (config, loss) on the fresh test set, from checkpoints/fp32_v1/MANIFEST.json
    "paper_mse": "vp8_L3_K9_C5_mse_s1",
    "paper_bce": "vp8_L3_K9_C5_bce_s1",
    "ours_mse": "vp4_L4_K9_C3_mse_s2",
    "ours_bce": "vp4_L4_K9_C3_bce_s2",
}


def job(args):
    name, bits, iters, out = args
    torch.set_num_threads(1)
    torch.manual_seed(0)
    key = MODELS[name]
    loss = "bce" if "bce" in name else "mse"
    ck = torch.load(CK / "imdd" / f"{key}.pt")
    fp = NeyCNN(**ck["cfg"])
    fp.load_state_dict(ck["state_dict"])
    fp.eval()
    tr = load_dataset(CK / "imdd_data" / "train.npz", 2, 2)
    te = load_dataset(CK / "imdd_data" / "test_fresh.npz", 2, 2)
    q = QuantNeyCNN(fp, bits, bits, bits)
    q.calibrate(torch.from_numpy(np.stack([tr.rx[0][:65536], tr.rx[1][:65536]])))
    ptq_ber, _ = integer_ber(export_integer(q), te)
    t0 = time.time()
    train_sgd(q, tr, iters=iters, lr=2e-4, seed=0, loss_type=loss)
    q.eval()
    im = export_integer(q)
    qat_ber, n = integer_ber(im, te)
    acc_bits = im.acc_bits_needed([im.quantize_input(r.astype(np.float64)) for r in te.rx[:3]])
    d = Path(out) / f"{name}_w{bits}"
    d.mkdir(parents=True, exist_ok=True)
    torch.save({"cfg": ck["cfg"], "bits": bits, "state_dict": q.state_dict(), "source": key}, d / "qat_model.pt")
    with open(d / "integer_model.pkl", "wb") as f:
        pickle.dump(im, f)
    row = {"name": name, "source": key, "loss": loss, "bits": bits, "ptq_ber": ptq_ber, "qat_ber": qat_ber,
           "bits_tested": n, "acc_bits_needed": acc_bits, "qat_s": round(time.time() - t0, 1),
           "requant_shifts": [s.tolist() for s in im.S]}
    (d / "metrics.json").write_text(json.dumps(row, indent=2))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits", type=int, nargs="+", default=[8, 6, 5, 4])
    ap.add_argument("--iters", type=int, default=4000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=Path("results/quant"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((CK / "MANIFEST.json").read_text())
    fp32 = {e["key"]: e.get("ber_fresh_test") for e in manifest["files"] if "key" in e}
    jobs = [(n, b, args.iters, str(args.out)) for n in MODELS for b in args.bits]
    rows = []
    with mp.get_context("spawn").Pool(args.workers) as pool:
        for r in pool.imap_unordered(job, jobs):
            r["fp32_ber"] = fp32.get(r["source"])
            rows.append(r)
            print(f"{r['name']:10s} W{r['bits']}A{r['bits']}  fp32 {r['fp32_ber']:.2e}  PTQ {r['ptq_ber']:.2e}  QAT {r['qat_ber']:.2e}  acc bits {r['acc_bits_needed']}", flush=True)
    rows.sort(key=lambda r: (r["name"], -r["bits"]))
    (args.out / "summary.json").write_text(json.dumps(rows, indent=2))
    plot(rows, args.out / "ber_vs_bits.png")


def plot(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4))
    for name, style in (("paper_mse", "o--"), ("paper_bce", "o-"), ("ours_mse", "s--"), ("ours_bce", "s-")):
        rs = sorted([r for r in rows if r["name"] == name], key=lambda r: r["bits"])
        if not rs:
            continue
        line, = ax.plot([r["bits"] for r in rs], [max(r["qat_ber"], 1e-7) for r in rs], style, label=f"{name} (QAT, integer)")
        ax.axhline(rs[0]["fp32_ber"], color=line.get_color(), ls=":", lw=1)
    ax.set_yscale("log")
    ax.set_xlabel("bits (weights = activations = input)")
    ax.set_ylabel("BER (integer model, fresh test set)")
    ax.set_title("Quantization: dotted = FP32 reference")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


if __name__ == "__main__":
    main()
