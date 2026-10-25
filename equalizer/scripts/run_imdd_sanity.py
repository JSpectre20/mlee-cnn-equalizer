"""Sanity checks for the IM/DD channel simulator.

1. Small-signal power-fading response vs theory cos(beta2 L w^2 / 2).
2. Eye diagrams back-to-back vs after 31.5 km.
3. LS-optimal FIR BER vs SNR: a linear equalizer should hit an error floor,
   because the CD + square-law interaction is nonlinear (Ney et al. Fig. 2).

Usage:
    python scripts/run_imdd_sanity.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from eqsim.channels import IMDDChannel
from eqsim.equalizers import FIREqualizer, fit_linear_in_params_ls
from eqsim.train import evaluate_ber

OUT = Path("results/imdd_sanity")


def fading_plot(ch: IMDDChannel):
    small = IMDDChannel(**{**ch.__dict__, "mod_index": 0.05})
    _, _, it = small.simulate(40_000, np.random.default_rng(0), noise=False)
    f, pxy = signal.csd(it["drive"], it["current"], fs=it["fs_sim"], nperseg=4096)
    _, pxx = signal.welch(it["drive"], fs=it["fs_sim"], nperseg=4096)
    meas = np.abs(pxy / pxx)
    theory = np.abs(np.cos(small.beta2 * small.length_km * 1e3 * (2 * np.pi * f) ** 2 / 2))
    band = f < 25e9
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(f[band] / 1e9, 20 * np.log10(meas[band] / meas[1]), label="simulated")
    ax.plot(f[band] / 1e9, 20 * np.log10(theory[band] + 1e-6), "--", label=r"theory $|\cos(\beta_2 L \omega^2/2)|$")
    ax.axvline(small.fading_null_hz() / 1e9, color="k", ls=":", label=f"null {small.fading_null_hz() / 1e9:.1f} GHz")
    ax.set_ylim(-40, 5)
    ax.set_xlabel("frequency (GHz)")
    ax.set_ylabel("|H| (dB)")
    ax.set_title("Small-signal IM/DD response, 31.5 km SSMF")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "power_fading.png", dpi=150)


def eye_plot(ch: IMDDChannel):
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), sharey=True)
    for ax, km in zip(axes, (0.0, ch.length_km)):
        c = IMDDChannel(**{**ch.__dict__, "length_km": km, "snr_db": 30.0, "nos": 8})
        rx, _ = c(3000, np.random.default_rng(1))
        seg = rx[: (len(rx) // 16) * 16].reshape(-1, 16)
        ax.plot(np.arange(16) / 8, seg[50:450].T, color="tab:blue", alpha=0.08)
        ax.set_title(f"{km:g} km")
        ax.set_xlabel("time (symbols)")
    axes[0].set_ylabel("normalized photocurrent")
    fig.tight_layout()
    fig.savefig(OUT / "eyes.png", dpi=150)


def fir_floor(ch: IMDDChannel):
    rows = []
    for snr in (10, 14, 18, 22, 26, 30, 40):
        c = IMDDChannel(**{**ch.__dict__, "snr_db": snr})
        rx, idx = c(200_000, np.random.default_rng(3))
        row = {"snr_db": snr}
        for taps in (17, 57, 121):
            m = FIREqualizer(taps)
            fit_linear_in_params_ls(m, rx, 2.0 * idx - 1.0, crop=64)
            row[f"fir{taps}"], _ = evaluate_ber(m, c, 300_000)
        rows.append(row)
        print(row, flush=True)
    fig, ax = plt.subplots(figsize=(5, 3.5))
    for taps in (17, 57, 121):
        ax.semilogy([r["snr_db"] for r in rows], [max(r[f"fir{taps}"], 1e-6) for r in rows], "o-", label=f"FIR {taps} taps")
    ax.set_xlabel("electrical SNR (dB)")
    ax.set_ylabel("BER")
    ax.set_title("Linear FIR on 31.5 km IM/DD (40 GBd PAM2)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fir_floor.png", dpi=150)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ch = IMDDChannel()
    fading_plot(ch)
    eye_plot(ch)
    rows = fir_floor(ch)
    (OUT / "fir_floor.json").write_text(json.dumps({"channel": {k: v for k, v in ch.__dict__.items() if k != "extra"}, "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
