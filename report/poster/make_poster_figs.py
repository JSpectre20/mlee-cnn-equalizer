r"""Poster figures, drawn at their printed size on the A0 poster (column text width ~37 cm) so labels print at
22-30 pt. Numbers are read from the result files (same sources as the report).

Run from Project/:  $env:PYTHONPATH="equalizer"; D:\venvs\mlee-eq\Scripts\python.exe report\poster\make_poster_figs.py
Writes report/poster/fig_result1, fig_result2, fig_background (.pdf used by the poster, .png previews).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "equalizer" / "results"
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "equalizer"))

NAVY, BLUE, GREEN, GRAY, LGRAY, ORANGE, RED = "#1F3864", "#2E75B6", "#2E8B57", "#7F7F7F", "#BFBFBF", "#C55A11", "#C00000"
CM = 1 / 2.54
plt.rcParams.update({
    "font.family": "Arial", "font.size": 24, "axes.titlesize": 26, "axes.labelsize": 24, "xtick.labelsize": 22,
    "ytick.labelsize": 22, "legend.fontsize": 22, "mathtext.fontset": "custom", "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold", "axes.spines.top": False,
    "axes.spines.right": False, "axes.linewidth": 1.6, "xtick.major.width": 1.6, "ytick.major.width": 1.6,
    "xtick.major.size": 7, "ytick.major.size": 7, "grid.linewidth": 1.0, "grid.alpha": 0.35, "legend.frameon": False,
    "savefig.dpi": 200,
})


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def save(fig, name):
    for ext in (".pdf", ".png"):
        fig.savefig(OUT / f"{name}{ext}", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("wrote", name)


def sci(x):
    """4.5e-04 -> 4.5 x 10^-4 in mathtext, typeset in Arial (mathtext.fontset = custom)."""
    m, e = f"{x:.1e}".split("e")
    return rf"${m}\times10^{{{int(e)}}}$"


# ------------------------------------------------------------------ hero: BER at the same budget, then deployable
def hero():
    conf = jl(RES / "imdd_dse" / "confirm.jsonl")
    best = defaultdict(lambda: 1.0)
    for c in conf:
        k = (c["vp"], c["layers"], c["kernel"], c["channels"], c["loss"])
        best[k] = min(best[k], c["ber"])
    fir121 = [b["ber"] for b in json.load(open(RES / "imdd_dse" / "confirm_baselines.json"))
              if b["spec"] == 121 and b["loss"] == "mse"][0]
    paper_fp, ours_fp = best[(8, 3, 9, 5, "mse")], best[(4, 4, 9, 3, "bce")]
    q = json.load(open(RES / "quant" / "summary.json"))
    paper_w8 = [r["qat_ber"] for r in q if r["name"] == "paper_mse" and r["bits"] == 8][0]
    ours_w6 = [r["qat_ber"] for r in q if r["name"] == "ours_bce" and r["bits"] == 6][0]
    dfe_w8 = json.load(open(RES / "quant" / "ours_bce_dfe_w8" / "metrics.json"))["qat_ber"]

    rows = [  # label, value, colour, ratio note
        ("FIR equalizer, 121 taps", fir121, LGRAY, ""),
        ("Paper's CNN (MSE)", paper_fp, GRAY, ""),
        ("Ours: CNN, cross-entropy", ours_fp, BLUE, f"{paper_fp / ours_fp:.0f}× lower"),
        ("Paper's CNN, 8 bit", paper_w8, GRAY, ""),
        ("Ours: CNN, 6 bit", ours_w6, BLUE, f"{paper_w8 / ours_w6:.0f}× lower"),
        ("Ours: CNN + DFE, 8 bit", dfe_w8, GREEN, "≈ 1000× lower"),
    ]
    y = [7.0, 6.0, 5.0, 2.6, 1.6, 0.6]
    fig, ax = plt.subplots(figsize=(36 * CM, 17 * CM))
    ax.barh(y, [r[1] for r in rows], color=[r[2] for r in rows], height=0.72, left=1e-7)
    for yy, (lab, v, c, note) in zip(y, rows):
        ax.text(v * 1.35, yy, sci(v), va="center", fontsize=24, color="#222222")
        if note:
            ax.text(4e-3, yy, note, va="center", fontsize=26, color=c, fontweight="bold")
    ax.set_yticks(y, [r[0] for r in rows])
    ax.tick_params(axis="y", length=0, labelsize=24)
    ax.text(1.1e-7, 8.05, "Floating point, within the paper's budget (≤ 147 multiplications / symbol)", fontsize=24,
            color=NAVY, fontweight="bold", va="center")
    ax.text(1.1e-7, 3.65, "Integer models as deployed on the FPGA", fontsize=24, color=NAVY, fontweight="bold", va="center")
    ax.axhline(4.3, color=LGRAY, lw=1.5)
    ax.set_xscale("log")
    ax.set_xlim(1e-7, 1e-1)
    ax.set_ylim(0, 8.6)
    ax.grid(True, axis="x", which="major")
    ax.set_xlabel("bit error rate (fresh 4M-symbol test set, 24 dB)   ← better")
    save(fig, "fig_result1")


# ------------------------------------------------------------------ background: CD power fading
def fading():
    from scipy import signal
    from eqsim.channels import IMDDChannel

    ch = IMDDChannel(snr_db=24.0)
    small = IMDDChannel(**{**ch.__dict__, "mod_index": 0.05})
    _, _, it = small.simulate(40_000, np.random.default_rng(0), noise=False)
    f, pxy = signal.csd(it["drive"], it["current"], fs=it["fs_sim"], nperseg=4096)
    _, pxx = signal.welch(it["drive"], fs=it["fs_sim"], nperseg=4096)
    meas = np.abs(pxy / pxx)
    band = f < 24e9
    fig, ax = plt.subplots(figsize=(17 * CM, 11 * CM))
    ax.axvspan(0, 20, color="#D9E2F3", alpha=0.5, lw=0)
    ax.plot(f[band] / 1e9, 20 * np.log10(meas[band] / meas[1]), color=BLUE, lw=3.2)
    for k in (0, 1):
        fn = small.fading_null_hz(k) / 1e9
        ax.axvline(fn, color=RED, ls=":", lw=2)
        ax.text(fn, 3.5, f"{fn:.1f} GHz", ha="center", va="bottom", fontsize=21, color=RED, fontweight="bold")
    ax.text(0.6, -33, "signal band", fontsize=21, color=NAVY)
    ax.set_ylim(-36, 8)
    ax.set_xlim(0, 24)
    ax.set_xlabel("frequency (GHz)")
    ax.set_ylabel("|H| (dB)")
    save(fig, "fig_background")


# ------------------------------------------------------------------ result 2: where decision feedback helps
def stress():
    rows = jl(RES / "dfe_stress" / "results.jsonl")
    models = ["FFE121", "FFE57+DFE2", "CNN", "CNN+DFE2"]
    heads = ["FFE-121\n(121)", "FFE-57+DFE\n(59)", "CNN\n(121.5)", "CNN+DFE\n(121.5)"]
    conds = [(20, 20.0), (14, 31.5), (16, 31.5), (18, 31.5), (20, 31.5), (22, 31.5), (24, 31.5), (20, 40.0), (20, 50.0)]
    M = np.array([[min(r["ber"] for r in rows if r["snr"] == s and r["L"] == L and r["model"] == m) for m in models]
                  for s, L in conds])
    Z = np.log10(np.maximum(M, 1e-7))
    fig, ax = plt.subplots(figsize=(36 * CM, 19 * CM))
    ax.imshow(Z, cmap="YlGnBu_r", vmin=-7, vmax=-1.5, aspect="auto")
    for i in range(len(conds)):
        bi = int(np.argmin(np.where(M[i] == 0, 1e-12, M[i])))
        for j in range(len(models)):
            v = M[i, j]
            txt = "0 errors" if v == 0 else f"{v:.1e}".replace("e-0", "e-")
            ax.text(j, i, txt, ha="center", va="center", fontsize=22, color="white" if Z[i, j] < -4.6 else "#1a1a1a",
                    fontweight="bold" if j == bi else "normal")
        ax.add_patch(Rectangle((bi - 0.5, i - 0.5), 1, 1, fill=False, ec=ORANGE, lw=4))
    ax.set_xticks(range(len(models)), heads, fontsize=22)
    ax.set_yticks(range(len(conds)), [f"{L:g} km, {s} dB" for s, L in conds], fontsize=22)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    for yy in (0.5, 6.5):
        ax.axhline(yy, color="white", lw=5)
    ax.axvline(1.5, color="white", lw=5)
    save(fig, "fig_result2")


if __name__ == "__main__":
    hero()
    fading()
    stress()
