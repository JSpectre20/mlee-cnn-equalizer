"""Reproduce Ney et al. Fig. 4 (Proakis-B, 20 dB) and test the training objective.

Series:
  fir / volterra          closed-form least squares (MSE-optimal), as the paper's MSE recipe
  fir_ce / volterra_ce    same models refit by logistic regression (cross-entropy)
  cnn_mse                 paper's selected CNN, Adam + MSE (paper recipe), best of N seeds
  cnn_bce                 same CNN trained with binary cross-entropy
  mlse                    4-state Viterbi on the symbol-spaced samples (reference, not a candidate)

Usage:
    python scripts/run_proakis.py --iters 10000 --seeds 3
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

from eqsim.channels import ProakisBChannel
from eqsim.detectors import mlse_viterbi
from eqsim.equalizers import (FIREqualizer, NeyCNN, VolterraEqualizer, fit_linear_in_params_logistic,
                              fit_linear_in_params_ls)
from eqsim.metrics import pam_levels
from eqsim.train import evaluate_ber, train_sgd

FIR_TAPS = [3, 5, 9, 17, 25, 41, 57, 89, 121]
VOLTERRA = [(9, 3, 3), (13, 5, 3), (15, 5, 5), (25, 9, 5), (25, 9, 9), (35, 15, 9)]
CNN = dict(layers=3, kernel=9, channels=5, vp=8)  # the paper's selected model (Fig. 3)
PAPER = {"cnn": 8.4e-3, "fir_similar_complexity": 9.6e-3}


def mlse_ber(ch, n_symbols, seed=12345):
    rng = np.random.default_rng(seed)
    errs = total = 0
    for _ in range(max(1, n_symbols // 20_000)):
        rx, idx = ch(20_000, rng)
        dec = mlse_viterbi(rx[:: ch.nos], np.array(ch.h), pam_levels(ch.order))
        errs += int(np.sum(dec[64:-64] != idx[64:-64]))
        total += len(idx) - 128
    return errs / total, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=10_000)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--test-symbols", type=int, default=1_000_000)
    ap.add_argument("--fit-symbols", type=int, default=200_000)
    ap.add_argument("--snr", type=float, default=20.0)
    ap.add_argument("--out", type=Path, default=Path("results/proakis"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    ch = ProakisBChannel(snr_db=args.snr)
    rx_fit, idx_fit = ch(args.fit_symbols, np.random.default_rng(7))
    sym_fit = 2.0 * idx_fit - 1.0
    res = {"config": {k: str(v) for k, v in vars(args).items()}, "channel": ch.__dict__, "paper": PAPER}

    def run_linear(name, make, label_fn):
        rows_mse, rows_ce = [], []
        for spec in make:
            m = FIREqualizer(spec) if name == "fir" else VolterraEqualizer(*spec)
            fit_linear_in_params_ls(m, rx_fit, sym_fit, crop=64)
            b, n = evaluate_ber(m, ch, args.test_symbols)
            rows_mse.append({"spec": spec, "macs": m.macs_per_symbol(), "ber": b, "bits": n})
            m = FIREqualizer(spec) if name == "fir" else VolterraEqualizer(*spec)
            fit_linear_in_params_logistic(m, rx_fit, idx_fit, crop=64)
            b2, _ = evaluate_ber(m, ch, args.test_symbols)
            rows_ce.append({"spec": spec, "macs": m.macs_per_symbol(), "ber": b2, "bits": n})
            print(f"{label_fn(spec):>22}  MAC/sym {m.macs_per_symbol():7.1f}  BER MSE-fit {b:.3e}  CE-fit {b2:.3e}", flush=True)
        res[name], res[name + "_ce"] = rows_mse, rows_ce

    run_linear("fir", FIR_TAPS, lambda s: f"FIR {s}")
    run_linear("volterra", VOLTERRA, lambda s: f"Volterra {s}")

    for loss in ("mse", "bce"):
        runs = []
        for seed in range(args.seeds):
            torch.manual_seed(seed)  # seed the weight initialisation too, not just the data
            m = NeyCNN(**CNN)
            t0 = time.time()
            train_sgd(m, ch, iters=args.iters, seed=seed, loss_type=loss)
            b, n = evaluate_ber(m, ch, args.test_symbols)
            runs.append({"seed": seed, "ber": b, "bits": n})
            print(f"CNN {loss} seed {seed}  BER {b:.3e}  ({time.time() - t0:.0f}s)", flush=True)
            if b == min(r["ber"] for r in runs):
                torch.save(m.state_dict(), args.out / f"cnn_{loss}.pt")
        res[f"cnn_{loss}"] = {"cfg": CNN, "runs": runs, "best_ber": min(r["ber"] for r in runs),
                              "macs": NeyCNN(**CNN).macs_per_symbol(), "macs_paper_formula": NeyCNN(**CNN).macs_paper_formula()}

    b, n = mlse_ber(ch, args.test_symbols)
    res["mlse"] = {"ber": b, "symbols": n}
    print(f"MLSE reference BER {b:.3e} over {n} symbols", flush=True)

    (args.out / "results.json").write_text(json.dumps(res, indent=2, default=str))
    plot(res, args.out / "ber_vs_macs.png")


def plot(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for key, style, label in (("fir", "o--", "FIR, MSE (paper recipe)"), ("fir_ce", "o-", "FIR, cross-entropy"),
                              ("volterra", "s--", "Volterra, MSE (paper recipe)"), ("volterra_ce", "s-", "Volterra, cross-entropy")):
        rows = res[key]
        ax.plot([r["macs"] for r in rows], [max(r["ber"], 1e-6) for r in rows], style, label=label, ms=5)
    for loss, marker in (("mse", "*"), ("bce", "P")):
        r = res[f"cnn_{loss}"]
        ax.plot(r["macs"], r["best_ber"], marker, color="k", ms=12, label=f"CNN, {loss.upper()} (exact MAC/sym)")
    ax.axhline(res["paper"]["cnn"], color="gray", ls=":", label="paper's CNN, 8.4e-3")
    if res["mlse"]["ber"] > 0:
        ax.axhline(res["mlse"]["ber"], color="tab:red", ls="-.", label="MLSE reference")
    else:
        ax.annotate(f"MLSE: 0 errors in {res['mlse']['symbols']:.1e} symbols", xy=(0.02, 0.03), xycoords="axes fraction", color="tab:red", fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("MAC operations per symbol")
    ax.set_ylabel("BER")
    ax.set_title(f"Proakis-B, SNR {res['config']['snr']} dB")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


if __name__ == "__main__":
    main()
