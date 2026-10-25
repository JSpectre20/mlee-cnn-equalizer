"""Where does decision feedback help, and does a CNN still win? (improvement I5)

Conditions: SNR 14..24 dB at 31.5 km, and fiber length 20/40/50 km at 20 dB (40 GBd PAM2 IM/DD).
Per condition (1M train / 2M test symbols; 24 dB / 31.5 km reuses the frozen fp32_v1 data):
  FFE57, FFE121, FFE25+DFE2, FFE57+DFE2      closed-form LS
  CNN (vp4 L4 K9 C3, BCE)                     3 seeds
  CNN+DFE2 (same CNN + 2 feedback taps, BCE)  3 seeds
All DFE numbers use the equalizer's own decisions. Results are appended to
results/dfe_stress/results.jsonl (resumable); trained models go to results/dfe_stress/models/.

Usage: python scripts/run_dfe_stress.py --workers 6
"""
import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np
import torch

from eqsim.channels import IMDDChannel
from eqsim.data import evaluate_ber_dataset, load_dataset, save_dataset, simulate_chunks
from eqsim.dfe import CNNDFE, ber_cnn_dfe, ber_ffe_dfe, fit_ffe_dfe, train_cnn_dfe
from eqsim.equalizers import NeyCNN
from eqsim.train import train_sgd

OUT = Path("results/dfe_stress")
CNN_CFG = dict(vp=4, layers=4, kernel=9, channels=3)
CONDITIONS = [(snr, 31.5) for snr in (14, 16, 18, 20, 22, 24)] + [(20, L) for L in (20.0, 40.0, 50.0)]
BASE = Path("checkpoints/fp32_v1/imdd_data")


def cond_name(snr, L):
    return f"snr{snr}_L{L:g}"


def data_paths(snr, L):
    if (snr, L) == (24, 31.5):
        return BASE / "train.npz", BASE / "test_fresh.npz"
    d = OUT / "data"
    return d / f"{cond_name(snr, L)}_train.npz", d / f"{cond_name(snr, L)}_test.npz"


def _sim_job(job):
    snr, L, which, n, seed = job
    path = data_paths(snr, L)[0 if which == "train" else 1]
    if not path.exists():
        save_dataset(path, *simulate_chunks(IMDDChannel(snr_db=snr, length_km=L), n, seed))
    return str(path)


def _ffe_job(job):
    snr, L = job
    tr_p, te_p = data_paths(snr, L)
    tr, te = load_dataset(tr_p, 2, 2), load_dataset(te_p, 2, 2)
    tr.rx, tr.idx = tr.rx[:5], tr.idx[:5]           # 1M training symbols for every condition
    rows = []
    for taps, n_fb in ((57, 0), (121, 0), (25, 2), (57, 2)):
        w = fit_ffe_dfe(tr, taps, n_fb)
        b, n = ber_ffe_dfe(te, w, taps, n_fb)
        rows.append({"key": f"{cond_name(snr, L)}_ffe{taps}_dfe{n_fb}", "snr": snr, "L": L, "model": f"FFE{taps}" + (f"+DFE{n_fb}" if n_fb else ""),
                     "macs": taps, "seed": 0, "ber": b, "bits": n, "fb": [float(v) for v in w[taps + 1:]]})
    return rows


def _cnn_job(job):
    snr, L, kind, seed, iters = job
    torch.set_num_threads(1)
    tr_p, te_p = data_paths(snr, L)
    tr, te = load_dataset(tr_p, 2, 2), load_dataset(te_p, 2, 2)
    tr.rx, tr.idx = tr.rx[:5], tr.idx[:5]
    t0 = time.time()
    torch.manual_seed(seed)
    if kind == "cnn":
        m = NeyCNN(**CNN_CFG)
        train_sgd(m, tr, iters=iters, seed=seed, loss_type="bce")
        b, n = evaluate_ber_dataset(m, te)
        fb = []
    else:
        m = CNNDFE(n_fb=2, **CNN_CFG)
        train_cnn_dfe(m, tr, iters=iters, seed=seed)
        b, n = ber_cnn_dfe(m, te)
        fb = [float(v) for v in m.fb.detach()]
    key = f"{cond_name(snr, L)}_{kind}_s{seed}"
    (OUT / "models").mkdir(parents=True, exist_ok=True)
    torch.save({"cfg": CNN_CFG, "kind": kind, "snr": snr, "L": L, "state_dict": m.state_dict()}, OUT / "models" / f"{key}.pt")
    return [{"key": key, "snr": snr, "L": L, "model": "CNN" if kind == "cnn" else "CNN+DFE2", "macs": m.macs_per_symbol(),
             "seed": seed, "ber": b, "bits": n, "fb": fb, "train_s": round(time.time() - t0, 1)}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--iters", type=int, default=10_000)
    args = ap.parse_args()
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    res_p = OUT / "results.jsonl"
    done = {json.loads(l)["key"] for l in res_p.read_text().splitlines() if l.strip()} if res_p.exists() else set()
    ctx = mp.get_context("spawn")

    sims = [(s, L, w, n, seed) for s, L in CONDITIONS if (s, L) != (24, 31.5)
            for w, n, seed in (("train", 1_000_000, 101), ("test", 2_000_000, 102))]
    t0 = time.time()
    with ctx.Pool(args.workers) as pool:
        for p in pool.imap_unordered(_sim_job, sims):
            print(f"data {p}", flush=True)
    print(f"data ready ({time.time() - t0:.0f}s)", flush=True)

    jobs_ffe = [(s, L) for s, L in CONDITIONS if f"{cond_name(s, L)}_ffe57_dfe2" not in done]
    jobs_cnn = [(s, L, k, seed, args.iters) for s, L in CONDITIONS for k in ("cnn", "cnndfe") for seed in range(args.seeds)
                if f"{cond_name(s, L)}_{k}_s{seed}" not in done]
    with ctx.Pool(args.workers) as pool, res_p.open("a") as f:
        its = [pool.imap_unordered(_ffe_job, jobs_ffe), pool.imap_unordered(_cnn_job, jobs_cnn)]
        for it in its:
            for rows in it:
                for r in rows:
                    f.write(json.dumps(r) + "\n")
                    f.flush()
                    print(f"{r['key']:28s} {r['model']:10s} MAC {r['macs']:6.1f}  BER {r['ber']:.3e}", flush=True)
    summarize(res_p)


def summarize(res_p):
    rows = [json.loads(l) for l in res_p.read_text().splitlines() if l.strip()]
    table = {}
    for r in rows:
        table.setdefault((r["snr"], r["L"]), {}).setdefault(r["model"], []).append(r["ber"])
    models = ["FFE57", "FFE121", "FFE25+DFE2", "FFE57+DFE2", "CNN", "CNN+DFE2"]
    print("\nbest (median) BER per condition")
    print(f"{'cond':14s}" + "".join(f"{m:>22s}" for m in models))
    for (snr, L) in sorted(table, key=lambda c: (c[1], c[0])):
        cells = []
        for m in models:
            v = sorted(table[(snr, L)].get(m, []))
            cells.append(f"{v[0]:.2e} ({np.median(v):.2e})" if len(v) > 1 else (f"{v[0]:.2e}" if v else "-"))
        print(f"{cond_name(snr, L):14s}" + "".join(f"{c:>22s}" for c in cells))
    (OUT / "summary.json").write_text(json.dumps({f"{cond_name(*k)}": v for k, v in table.items()}, indent=2))


if __name__ == "__main__":
    main()
