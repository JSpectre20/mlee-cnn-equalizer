"""Design-space exploration on the simulated 40 GBd IM/DD link (Ney et al. Sec. 3.5, Fig. 2),
with every model trained both by MSE (paper recipe) and by cross-entropy.

Stages (results are appended, so an interrupted run resumes where it stopped):
  data       simulate fixed train / test sets once and cache them
  baselines  FIR and Volterra, closed-form LS (MSE) and logistic (CE) fits
  screen     all 135 CNN configs x {mse, bce}, 1 seed
  refine     Pareto-optimal screened configs, extra seeds

Usage:
    python scripts/run_imdd_dse.py --stage all --workers 6
    python scripts/run_imdd_dse.py --stage refine --seeds 3
"""
import argparse
import itertools
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np
import torch

from eqsim.channels import IMDDChannel
from eqsim.data import evaluate_ber_dataset, load_dataset, save_dataset, simulate_chunks
from eqsim.equalizers import FIREqualizer, NeyCNN, VolterraEqualizer, fit_linear_in_params_logistic, fit_linear_in_params_ls
from eqsim.train import train_sgd

GRID = dict(vp=[1, 2, 4, 8, 16], layers=[3, 4, 5], kernel=[9, 15, 21], channels=[3, 4, 5])  # 135 configs, as in the paper
FIR_TAPS = [3, 5, 9, 17, 25, 41, 57, 89, 121, 185, 249]
VOLTERRA = [(9, 3, 3), (13, 5, 3), (15, 5, 5), (25, 9, 5), (25, 9, 9), (35, 15, 9), (55, 25, 9)]


def channel(args) -> IMDDChannel:
    return IMDDChannel(snr_db=args.snr)


def data_paths(out: Path):
    return out / "train.npz", out / "test.npz"


def stage_data(args):
    train_p, test_p = data_paths(args.out)
    for path, n, seed in ((train_p, args.train_symbols, 1), (test_p, args.test_symbols, 2)):
        if path.exists():
            print(f"{path.name} exists, skipping", flush=True)
            continue
        t0 = time.time()
        save_dataset(path, *simulate_chunks(channel(args), n, seed))
        print(f"simulated {path.name}: {n} symbols in {time.time() - t0:.0f}s", flush=True)


def stage_baselines(args):
    train_p, test_p = data_paths(args.out)
    tr, te = load_dataset(train_p, 2, 2), load_dataset(test_p, 2, 2)
    rows = []
    for kind, specs in (("fir", FIR_TAPS), ("volterra", VOLTERRA)):
        for spec in specs:
            for loss in ("mse", "bce"):
                m = FIREqualizer(spec) if kind == "fir" else VolterraEqualizer(*spec)
                if loss == "mse":  # LS uses the whole training set (normal equations per chunk)
                    fit_linear_in_params_ls(m, tr.rx, [2.0 * i - 1.0 for i in tr.idx], crop=64)
                else:  # full-batch LBFGS: cap the data so the largest Volterra fits in RAM
                    k = len(tr.rx) if kind == "fir" else 2
                    fit_linear_in_params_logistic(m, tr.rx[:k], tr.idx[:k], crop=64)
                b, n = evaluate_ber_dataset(m, te)
                rows.append({"kind": kind, "spec": spec, "loss": loss, "macs": m.macs_per_symbol(), "ber": b, "bits": n})
                print(f"{kind} {spec} {loss}: MAC {m.macs_per_symbol():.0f}  BER {b:.3e}", flush=True)
    (args.out / "baselines.json").write_text(json.dumps(rows, indent=2))


def _key(cfg, loss, seed):
    return f"vp{cfg['vp']}_L{cfg['layers']}_K{cfg['kernel']}_C{cfg['channels']}_{loss}_s{seed}"


def _train_job(job):
    cfg, loss, seed, iters, out, *rest = job
    test_name = rest[0] if rest else None  # confirm stage: fresh test set + saved weights
    torch.set_num_threads(1)
    train_p, test_p = data_paths(Path(out))
    if test_name:
        test_p = Path(out) / test_name
    tr, te = load_dataset(train_p, 2, 2), load_dataset(test_p, 2, 2)
    torch.manual_seed(seed)
    m = NeyCNN(**cfg)
    t0 = time.time()
    n_sym = 512 if cfg["vp"] <= 8 else 1024
    train_sgd(m, tr, iters=iters, n_sym=n_sym, seed=seed, loss_type=loss)
    b, n = evaluate_ber_dataset(m, te)
    if test_name:
        (Path(out) / "models").mkdir(exist_ok=True)
        torch.save({"cfg": cfg, "state_dict": m.state_dict()}, Path(out) / "models" / f"{_key(cfg, loss, seed)}.pt")
    return {"key": _key(cfg, loss, seed), **cfg, "loss": loss, "seed": seed, "iters": iters, "ber": b, "bits": n,
            "macs": m.macs_per_symbol(), "macs_paper_formula": m.macs_paper_formula(), "train_s": round(time.time() - t0, 1)}


def _run_jobs(jobs, path: Path, workers: int):
    done = set()
    if path.exists():
        done = {json.loads(line)["key"] for line in path.read_text().splitlines() if line.strip()}
    jobs = [j for j in jobs if _key(j[0], j[1], j[2]) not in done]
    print(f"{len(jobs)} jobs to run ({len(done)} already done) on {workers} workers", flush=True)
    with mp.get_context("spawn").Pool(workers) as pool, path.open("a") as f:
        for k, r in enumerate(pool.imap_unordered(_train_job, jobs), 1):
            f.write(json.dumps(r) + "\n")
            f.flush()
            print(f"[{k}/{len(jobs)}] {r['key']}  MAC {r['macs']:.1f}  BER {r['ber']:.3e}  ({r['train_s']:.0f}s)", flush=True)


def stage_screen(args):
    cfgs = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    jobs = [(c, loss, 0, args.iters, str(args.out)) for c in cfgs for loss in ("mse", "bce")]
    _run_jobs(jobs, args.out / "screen.jsonl", args.workers)


def pareto(rows):
    """Rows not dominated in (macs, ber)."""
    rows = sorted(rows, key=lambda r: (r["macs"], r["ber"]))
    front, best = [], float("inf")
    for r in rows:
        if r["ber"] < best:
            front.append(r)
            best = r["ber"]
    return front


def stage_refine(args):
    rows = [json.loads(l) for l in (args.out / "screen.jsonl").read_text().splitlines() if l.strip()]
    jobs = []
    for loss in ("mse", "bce"):
        front = pareto([r for r in rows if r["loss"] == loss])
        for r in front:
            cfg = {k: r[k] for k in GRID}
            jobs += [(cfg, loss, s, args.iters, str(args.out)) for s in range(1, args.seeds)]
    _run_jobs(jobs, args.out / "refine.jsonl", args.workers)


CONFIRM_CFGS = [  # the paper's pick + the best CNNs within its 40 GBd budget from the screen/refine stages
    dict(vp=8, layers=3, kernel=9, channels=5),
    dict(vp=4, layers=3, kernel=15, channels=3),
    dict(vp=4, layers=4, kernel=9, channels=3),
]


def stage_confirm(args):
    """Retrain selected configs with both losses and score them on a fresh test set (no selection bias)."""
    fresh = args.out / "test_fresh.npz"
    if not fresh.exists():
        save_dataset(fresh, *simulate_chunks(channel(args), 4_000_000, seed=3))
        print("simulated test_fresh.npz: 4M symbols", flush=True)
    baseline_rows = []
    te = load_dataset(fresh, 2, 2)
    tr = load_dataset(data_paths(args.out)[0], 2, 2)
    for taps in (57, 121):
        for loss in ("mse", "bce"):
            m = FIREqualizer(taps)
            if loss == "mse":
                fit_linear_in_params_ls(m, tr.rx, [2.0 * i - 1.0 for i in tr.idx], crop=64)
            else:
                fit_linear_in_params_logistic(m, tr.rx, tr.idx, crop=64)
            b, n = evaluate_ber_dataset(m, te)
            baseline_rows.append({"kind": "fir", "spec": taps, "loss": loss, "macs": taps, "ber": b, "bits": n})
            print(f"fresh test: FIR {taps} {loss} BER {b:.3e}", flush=True)
    (args.out / "confirm_baselines.json").write_text(json.dumps(baseline_rows, indent=2))
    jobs = [(c, loss, s, args.iters, str(args.out), fresh.name) for c in CONFIRM_CFGS for loss in ("mse", "bce") for s in range(args.seeds)]
    _run_jobs(jobs, args.out / "confirm.jsonl", args.workers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["data", "baselines", "screen", "refine", "confirm", "all"], default="all")
    ap.add_argument("--iters", type=int, default=10_000)
    ap.add_argument("--seeds", type=int, default=3, help="total seeds per config in the refine stage")
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 0))
    ap.add_argument("--snr", type=float, default=24.0)
    ap.add_argument("--train-symbols", type=int, default=2_000_000)
    ap.add_argument("--test-symbols", type=int, default=2_000_000)
    ap.add_argument("--out", type=Path, default=Path("results/imdd_dse"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "config.json").write_text(json.dumps({k: str(v) for k, v in vars(args).items()} | {"channel": {k: v for k, v in channel(args).__dict__.items() if k != "extra"}}, indent=2))
    stages = ["data", "baselines", "screen", "refine"] if args.stage == "all" else [args.stage]
    for s in stages:
        print(f"=== stage {s} ===", flush=True)
        globals()[f"stage_{s}"](args)


if __name__ == "__main__":
    main()
