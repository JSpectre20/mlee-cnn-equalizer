"""Seed-variance study for the paper's CNN on Proakis-B (20 dB): N seeds x {MSE, BCE}.

Answers whether cross-entropy helps the CNN beyond seed-to-seed noise, and how
much the paper's best-of-3 selection matters. Runs seeds in parallel processes.

Usage:
    python scripts/run_proakis_seeds.py --seeds 10 --workers 6
"""
import argparse
import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
import torch

from eqsim.channels import ProakisBChannel
from eqsim.equalizers import NeyCNN
from eqsim.train import evaluate_ber, train_sgd

CNN = dict(layers=3, kernel=9, channels=5, vp=8)


def job(args):
    seed, loss, iters = args
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    m = NeyCNN(**CNN)
    ch = ProakisBChannel()
    train_sgd(m, ch, iters=iters, seed=seed, loss_type=loss)
    b, n = evaluate_ber(m, ch, 1_000_000)
    return {"seed": seed, "loss": loss, "ber": b, "bits": n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--iters", type=int, default=10_000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=Path("results/proakis"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [(s, l, args.iters) for s in range(args.seeds) for l in ("mse", "bce")]
    with mp.get_context("spawn").Pool(args.workers) as pool:
        rows = []
        for r in pool.imap_unordered(job, jobs):
            rows.append(r)
            print(r, flush=True)
    stats = {}
    for loss in ("mse", "bce"):
        b = np.array(sorted(r["ber"] for r in rows if r["loss"] == loss))
        rng = np.random.default_rng(0)
        best3 = [rng.choice(b, 3, replace=False).min() for _ in range(2000)]
        stats[loss] = {"all": b.tolist(), "median": float(np.median(b)), "min": float(b.min()), "max": float(b.max()),
                       "expected_best_of_3": float(np.mean(best3))}
    (args.out / "seeds.json").write_text(json.dumps({"rows": rows, "stats": stats}, indent=2))
    print(json.dumps(stats, indent=2))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    for k, loss in enumerate(("mse", "bce")):
        b = stats[loss]["all"]
        ax.scatter(np.full(len(b), k) + np.random.default_rng(k).uniform(-0.08, 0.08, len(b)), b, alpha=0.7)
        ax.hlines(stats[loss]["median"], k - 0.2, k + 0.2, color="k")
    ax.axhline(8.4e-3, color="gray", ls=":", label="paper 8.4e-3")
    ax.set_xticks([0, 1], ["MSE (paper)", "cross-entropy"])
    ax.set_yscale("log")
    ax.set_ylabel("BER")
    ax.set_title(f"Paper's CNN on Proakis-B, {args.seeds} seeds")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(args.out / "seeds.png", dpi=150)


if __name__ == "__main__":
    main()
