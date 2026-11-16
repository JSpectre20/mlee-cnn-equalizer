"""All report figures (one consistent style). Run from Project/ with the eqsim venv:
    $env:PYTHONPATH = "equalizer"; D:\venvs\mlee-eq\Scripts\python.exe report/figures/make_figures.py
Writes report/figures/figNN_*.png (300 dpi, sized for the 15.9 cm text width of the template).
Data come only from equalizer/results/, equalizer/rtl/ reports and the numbers recorded in PROGRESS.md.
"""
import glob
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[2]
EQ = ROOT / "equalizer"
RES = EQ / "results"
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(EQ))

# ----------------------------------------------------------------------------- style
NAVY, BLUE, LIGHT, PALE = "#1F3864", "#2E75B6", "#D9E2F3", "#EAF1FB"
ORANGE, GREEN, GRAY, LGRAY, PURPLE, RED, GOLD = "#C55A11", "#2E8B57", "#7F7F7F", "#BFBFBF", "#7030A0", "#C00000", "#BF9000"
TEXTW = 6.26  # inches (15.9 cm)
plt.rcParams.update({
    "font.family": "Arial", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.8, "mathtext.fontset": "cm",
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "grid.linewidth": 0.4, "grid.alpha": 0.35,
    "savefig.dpi": 300, "legend.frameon": False,
})


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print("wrote", name)


def canvas(w, h, W=100.0, H=None):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    H = H if H is not None else W * h / w
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    return fig, ax, H


def box(ax, x, y, w, h, title, sub=None, fc=PALE, ec=BLUE, tc=NAVY, fs=7.2, sfs=5.9, lw=0.9, bold=True, r=1.2, ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw))
    tx = x + w / 2 if ha == "center" else x + 1.2
    if sub:
        ax.text(tx, y + h * 0.66, title, ha=ha, va="center", fontsize=fs, color=tc, fontweight="bold" if bold else "normal")
        ax.text(tx, y + h * 0.30, sub, ha=ha, va="center", fontsize=sfs, color="#333333", linespacing=1.15)
    else:
        ax.text(tx, y + h / 2, title, ha=ha, va="center", fontsize=fs, color=tc, fontweight="bold" if bold else "normal", linespacing=1.15)


def arrow(ax, p0, p1, color=NAVY, lw=0.9, style="-|>", ms=7, cs="arc3", ls="-", text=None, tfs=5.8, toff=(0, 1.2)):
    a = FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=ms, color=color, lw=lw, connectionstyle=cs, linestyle=ls,
                        shrinkA=0, shrinkB=0)
    ax.add_patch(a)
    if text:
        ax.text((p0[0] + p1[0]) / 2 + toff[0], (p0[1] + p1[1]) / 2 + toff[1], text, ha="center", va="bottom", fontsize=tfs, color=color)


def label(ax, x, y, s, **kw):
    kw.setdefault("fontsize", 8)
    kw.setdefault("fontweight", "bold")
    kw.setdefault("color", NAVY)
    ax.text(x, y, s, **kw)


def jl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


# ===================================================================== Fig 1: pipeline
def fig_pipeline():
    fig, ax, H = canvas(TEXTW, 2.85)
    # lanes
    ax.add_patch(Rectangle((0.3, H * 0.53), 99.4, H * 0.45, fc="#F6F9FD", ec=LIGHT, lw=0.8))
    ax.add_patch(Rectangle((0.3, H * 0.02), 99.4, H * 0.47, fc="#FDF6F1", ec="#F2D3BF", lw=0.8))
    ax.text(1.3, H * 0.955, "Algorithm and learning  (Python 3.14, PyTorch 2.14, package eqsim)", fontsize=6.8, color=BLUE, fontweight="bold", va="top")
    ax.text(1.3, H * 0.465, "Hardware  (SystemVerilog, Vivado / xsim 2025.2, PYNQ-Z2 XC7Z020)", fontsize=6.8, color=ORANGE, fontweight="bold", va="top")
    top = [("Channel models", "IM/DD 40 GBd, 31.5 km\nProakis-B (paper Sec. 2.2)"),
           ("Fixed datasets", "train 2M / test 2M\nfresh test 4M symbols"),
           ("Equalizers", "FIR, Volterra (LS, logistic)\nCNN: 135 configs x MSE/CE"),
           ("Decision feedback", "FFE+DFE, CNN+DFE\n9 channel conditions"),
           ("QAT + integer model", "LSQ, BN folding, M/2^S\nrequant, exact golden")]
    bot = [("RTL export", "package, params.mem,\ntest vectors"),
           ("Streaming engine", "conv1d_stream x L,\nDFE, AXI-Lite/Stream"),
           ("Verification", "unit + full model +\nmutation + gate level"),
           ("Implementation", "OOC P&R, 4 passes,\n200 MHz closure"),
           ("PYNQ-Z2 system", "PS7 + DMA, 2 clocks\npower from SAIF")]
    w, h, gap = 17.2, H * 0.27, 2.45
    y1, y2 = H * 0.585, H * 0.085
    for i, (t, s) in enumerate(top):
        x = 1.6 + i * (w + gap)
        box(ax, x, y1, w, h, t, s, fc="white", ec=BLUE)
        if i:
            arrow(ax, (x - gap, y1 + h / 2), (x, y1 + h / 2), color=BLUE)
    for i, (t, s) in enumerate(bot):
        x = 1.6 + i * (w + gap)
        box(ax, x, y2, w, h, t, s, fc="white", ec=ORANGE, tc="#7F3A0B")
        if i:
            arrow(ax, (x - gap, y2 + h / 2), (x, y2 + h / 2), color=ORANGE)
    # golden model feeds export (down-left) and verification (bit-exact)
    xg = 1.6 + 4 * (w + gap) + w / 2
    arrow(ax, (xg, y1), (1.6 + w / 2, y2 + h), color=NAVY, cs="arc3,rad=-0.08", lw=0.8)
    ax.text(48, H * 0.505, "weights, biases, M/S, feedback taps  +  expected outputs (bit-exact reference)", fontsize=5.8, color=NAVY, ha="center",
            bbox=dict(fc="white", ec="none", pad=0.4))
    arrow(ax, (xg - 3, y1), (1.6 + 2 * (w + gap) + w / 2, y2 + h), color=NAVY, cs="arc3,rad=-0.05", lw=0.6, ls="--")
    save(fig, "fig01_pipeline.png")


# ===================================================================== Fig 2: link model
def fig_link():
    from scipy import signal
    from eqsim.channels import IMDDChannel

    fig = plt.figure(figsize=(TEXTW, 3.9))
    gs = fig.add_gridspec(2, 3, height_ratios=[0.78, 1.45], width_ratios=[1.35, 1, 1], hspace=0.42, wspace=0.28,
                          left=0.07, right=0.995, top=0.995, bottom=0.11)
    ax0 = fig.add_subplot(gs[0, :])
    ax0.set_xlim(0, 100)
    ax0.set_ylim(0, 14)
    ax0.axis("off")
    chain = [("PRBS\nPAM2", "40 GBd"), ("RRC", r"$\beta=0.2$"), ("MZM", "quadrature\n$m=0.8$"), ("SSMF", "31.5 km\n16 ps/nm/km"),
             ("PIN PD", r"$|E|^2$"), ("Bessel", "4th order\n40 GHz"), ("AWGN", "SNR"), ("ADC", r"$N_{os}=2$"), ("Equalizer", "FIR / CNN\n(+DFE)")]
    n = len(chain)
    w = 9.0
    gap = (100 - n * w) / (n - 1)
    for i, (t, s) in enumerate(chain):
        x = i * (w + gap)
        optical = 2 <= i <= 3
        box(ax0, x, 2.2, w, 9.5, t, s, fc="#FFF4E8" if optical else ("white" if i < 8 else PALE), ec=ORANGE if optical else BLUE,
            tc="#7F3A0B" if optical else NAVY, fs=6.6, sfs=5.4)
        if i:
            arrow(ax0, (x - gap, 7), (x, 7), color=ORANGE if i in (3, 4) else NAVY, lw=1.0)
    ax0.text(0, 0.2, "(a) Simulated 40 GBd IM/DD link (8 samples/symbol internally; optical path in orange)", fontsize=6.6, color=NAVY)

    ch = IMDDChannel(snr_db=24.0)
    small = IMDDChannel(**{**ch.__dict__, "mod_index": 0.05})
    _, _, it = small.simulate(40_000, np.random.default_rng(0), noise=False)
    f, pxy = signal.csd(it["drive"], it["current"], fs=it["fs_sim"], nperseg=4096)
    _, pxx = signal.welch(it["drive"], fs=it["fs_sim"], nperseg=4096)
    meas = np.abs(pxy / pxx)
    theory = np.abs(np.cos(small.beta2 * small.length_km * 1e3 * (2 * np.pi * f) ** 2 / 2))
    band = f < 25e9
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.plot(f[band] / 1e9, 20 * np.log10(meas[band] / meas[1]), color=BLUE, lw=1.0, label="simulated link")
    ax1.plot(f[band] / 1e9, 20 * np.log10(theory[band] + 1e-6), "--", color=ORANGE, lw=0.9, label=r"$|\cos(\beta_2 L\,\omega^2/2)|$")
    for k in (0, 1):
        fn = small.fading_null_hz(k) / 1e9
        ax1.axvline(fn, color=GRAY, ls=":", lw=0.7)
        ax1.text(fn + 0.3, -36, f"{fn:.1f} GHz", fontsize=6, color=GRAY, rotation=90, va="bottom")
    ax1.axvspan(0, 20, color=LIGHT, alpha=0.35, lw=0)
    ax1.text(1, 2.5, "signal band (20 GHz)", fontsize=6, color=NAVY)
    ax1.set_ylim(-40, 6)
    ax1.set_xlim(0, 25)
    ax1.set_xlabel("frequency (GHz)")
    ax1.set_ylabel("small-signal |H| (dB)")
    ax1.legend(loc="lower left", fontsize=6)
    ax1.set_title("(b) CD power fading: spectral nulls in band", loc="left", color=NAVY)
    for j, km in enumerate((0.0, ch.length_km)):
        ax = fig.add_subplot(gs[1, 1 + j])
        c = IMDDChannel(**{**ch.__dict__, "length_km": km, "snr_db": 30.0, "nos": 8})
        rx, _ = c(3000, np.random.default_rng(1))
        seg = rx[: (len(rx) // 16) * 16].reshape(-1, 16)
        t = np.arange(16) / 8
        ax.plot(t, seg[50:650].T, color=BLUE if km == 0 else ORANGE, alpha=0.06, lw=0.6)
        ax.set_xlabel("time (symbols)")
        if j == 0:
            ax.set_ylabel("received (normalized)")
        else:
            ax.set_yticklabels([])
        ax.set_title(f"({'c' if j == 0 else 'd'}) eye, {'back-to-back' if km == 0 else '31.5 km'}", loc="left", color=NAVY)
        ax.set_xlim(0, 1.875)
    save(fig, "fig02_link.png")


# ===================================================================== Fig 3: CNN architectures
def fig_cnn():
    fig, ax, H = canvas(TEXTW, 2.55)

    def row(y, name, layers, out, dfe, col):
        ax.text(0.5, y + 6.2, name, fontsize=7.2, fontweight="bold", color=col, va="center")
        x = 0.5
        box(ax, x, y - 1, 9.5, 9, "input", "2048 x 1\nsamples", fc="white", ec=GRAY, tc="#404040", fs=6.4, sfs=5.4)
        x += 9.5
        for i, (t, s) in enumerate(layers):
            arrow(ax, (x, y + 3.5), (x + 2.2, y + 3.5), color=col)
            x += 2.2
            wd = 13.0
            box(ax, x, y - 1, wd, 9, t, s, fc=PALE if col == BLUE else "#F2F2F2", ec=col, tc=NAVY if col == BLUE else "#404040", fs=6.1, sfs=5.3)
            x += wd
        arrow(ax, (x, y + 3.5), (x + 2.2, y + 3.5), color=col)
        x += 2.2
        box(ax, x, y - 1, 10.5, 9, "reshape", out, fc="white", ec=col, tc=NAVY, fs=6.2, sfs=5.3)
        x += 10.5
        arrow(ax, (x, y + 3.5), (x + 2.2, y + 3.5), color=col)
        x += 2.2
        if dfe:
            box(ax, x, y - 1, 11, 9, "+ DFE", "2 taps on past\ndecisions", fc="#E8F5EE", ec=GREEN, tc="#1D5C3A", fs=6.3, sfs=5.3)
            x += 11
            arrow(ax, (x, y + 3.5), (x + 2.2, y + 3.5), color=GREEN)
            x += 2.2
        box(ax, x, y - 1, 9, 9, "decide", r"$\hat b = [z>0]$", fc="white", ec=GRAY, tc="#404040", fs=6.3, sfs=6.2)

    row(H - 15, "Ours  (V_p = 4, L = 4, K = 9, C = 3)   121.5 MAC/symbol", [
        ("Conv 1→3", "K9, stride 4\nReLU · 512x3"), ("Conv 3→3", "K9, stride 1\nReLU · 512x3"),
        ("Conv 3→3", "K9, stride 1\nReLU · 512x3"), ("Conv 3→4", "K9, stride 2\n256x4")], "256 x 4\n→ 1024 symbols", True, BLUE)
    row(H - 33.5, "Paper's selected CNN  (V_p = 8, L = 3, K = 9, C = 5)   112.5 MAC/symbol", [
        ("Conv 1→5", "K9, stride 8\nReLU · 256x5"), ("Conv 5→5", "K9, stride 1\nReLU · 256x5"),
        ("Conv 5→8", "K9, stride 2\n128x8")], "128 x 8\n→ 1024 symbols", False, GRAY)
    ax.text(0.5, 0.8, "Shapes are positions x channels for one 1024-symbol frame at N_os = 2 (2048 samples). The first layer's stride V_p and the last layer's"
                      " stride N_os give V_p output symbols per position; zero padding K/2 per frame edge.", fontsize=5.8, color="#404040")
    save(fig, "fig03_cnn.png")


# ===================================================================== Fig 4: Proakis-B
def fig_proakis():
    r = json.load(open(RES / "proakis" / "results.json"))
    seeds = json.load(open(RES / "proakis" / "seeds.json"))["rows"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(TEXTW, 2.55), gridspec_kw=dict(width_ratios=[1.55, 1], wspace=0.28))
    m = lambda k: (np.array([e["macs"] for e in r[k]]), np.array([e["ber"] for e in r[k]]))
    a.plot(*m("fir"), "-o", color=GRAY, ms=2.5, lw=0.9, label="FIR (LS)")
    a.plot(*m("volterra"), "--s", color=PURPLE, ms=2.5, lw=0.9, mfc="white", label="Volterra, MSE fit")
    a.plot(*m("volterra_ce"), "-s", color=PURPLE, ms=2.5, lw=0.9, label="Volterra, cross-entropy fit")
    sm = [s["ber"] for s in seeds if s["loss"] == "mse"]
    sb = [s["ber"] for s in seeds if s["loss"] == "bce"]
    a.scatter([112.5] * len(sm), sm, s=12, marker="o", facecolors="white", edgecolors=BLUE, lw=0.8, label="CNN, MSE (10 seeds)", zorder=3)
    a.scatter([118] * len(sb), sb, s=12, marker="o", color=ORANGE, lw=0, label="CNN, cross-entropy (10 seeds)", zorder=3)
    a.scatter([112.5], [8.4e-3], marker="*", s=70, color="black", zorder=4, label="paper: CNN 8.4e-3")
    a.scatter([57], [9.6e-3], marker="*", s=45, color=GRAY, zorder=4, label="paper: FIR 9.6e-3")
    a.annotate("MLSE (4-state Viterbi):\n0 errors in 9.9e5 symbols", xy=(300, 9e-4), xytext=(170, 1.1e-3), fontsize=6, color=GREEN)
    a.set_xscale("log")
    a.set_yscale("log")
    a.set_ylim(5e-4, 8e-2)
    a.set_xlabel("multiplications per symbol (exact)")
    a.set_ylabel("BER")
    a.grid(True, which="major")
    a.legend(loc="upper right", fontsize=5.8, ncol=1)
    a.set_title("(a) Proakis-B at 20 dB: BER vs complexity", loc="left", color=NAVY)
    rng = np.random.default_rng(3)
    for i, (v, c, lab) in enumerate(((sm, BLUE, "MSE\n(paper recipe)"), (sb, ORANGE, "cross-\nentropy"))):
        v = np.array(v)
        b.scatter(i + rng.uniform(-0.09, 0.09, len(v)), v, s=14, color=c, alpha=0.85, lw=0)
        b.hlines(np.median(v), i - 0.22, i + 0.22, color=c, lw=1.5)
        b.text(i + 0.25, np.median(v), f"median\n{np.median(v):.2e}", fontsize=5.8, color=c, va="center")
    b.set_xticks([0, 1], ["MSE\n(paper recipe)", "cross-\nentropy"])
    b.set_yscale("log")
    b.set_xlim(-0.5, 1.9)
    b.set_ylabel("BER (CNN, 10 seeds)")
    b.text(0.5, 0.97, "one-sided Mann-Whitney p = 0.011", transform=b.transAxes, ha="center", va="top", fontsize=6.2, color=NAVY)
    b.grid(True, axis="y", which="major")
    b.set_title("(b) seed spread of the paper's CNN", loc="left", color=NAVY)
    save(fig, "fig04_proakis.png")


# ===================================================================== Fig 5: DSE
def fig_dse():
    scr = jl(RES / "imdd_dse" / "screen.jsonl")
    summ = json.load(open(RES / "imdd_dse" / "summary.json"))
    base = json.load(open(RES / "imdd_dse" / "baselines.json"))
    conf = jl(RES / "imdd_dse" / "confirm.jsonl")
    fig, ax = plt.subplots(figsize=(TEXTW, 3.05))
    floor = 3e-7
    for loss, c, lab, mk in (("mse", GRAY, "CNN, MSE (paper recipe)", "o"), ("bce", BLUE, "CNN, cross-entropy (ours)", "o")):
        xs = np.array([e["macs"] for e in scr if e["loss"] == loss])
        ys = np.array([max(e["ber"], floor) for e in scr if e["loss"] == loss])
        if loss == "mse":
            ax.scatter(xs, ys, s=9, facecolors="none", edgecolors=c, lw=0.6, label=lab + ", 135 configs", alpha=0.8)
        else:
            ax.scatter(xs, ys, s=8, color=c, lw=0, alpha=0.75, label=lab + ", 135 configs")
    for k, c, ls, lab in (("pareto_mse", GRAY, "--", "Pareto front, MSE (3 seeds)"), ("pareto_bce", BLUE, "-", "Pareto front, cross-entropy (3 seeds)")):
        p = np.array(summ[k])
        ax.step(p[:, 0], np.maximum(p[:, 1], floor), where="post", color=c, ls=ls, lw=1.2, label=lab)
    fir = sorted([(e["macs"], e["ber"]) for e in base if e["kind"] == "fir" and e["loss"] == "mse"])
    fir = np.array(fir)
    ax.plot(fir[:, 0], fir[:, 1], "-", color="black", lw=0.9, label="FIR (LS)")
    ax.axvline(147, color=RED, ls=":", lw=1.0)
    ax.text(150, 0.12, "paper's 40 GBd hardware\nbudget: 147 MAC/symbol", color=RED, fontsize=6.2, va="top")
    pm = [e["ber"] for e in conf if e["key"].startswith("vp8_L3_K9_C5_mse")]
    ob = [e["ber"] for e in conf if e["key"].startswith("vp4_L4_K9_C3_bce")]
    ax.scatter([112.5], [min(pm)], marker="*", s=110, color="black", zorder=5, label=f"paper's CNN (fresh test) {min(pm):.1e}")
    ax.scatter([121.5], [min(ob)], marker="D", s=40, color=ORANGE, edgecolor="black", lw=0.5, zorder=5, label=f"ours vp4 L4 K9 C3 (fresh test) {min(ob):.1e}")
    ax.annotate("", xy=(121.5, min(ob) * 1.25), xytext=(112.5, min(pm) * 0.8), arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.0))
    ax.text(70, 7e-5, "~16x lower BER\nat equal cost", color=ORANGE, fontsize=6.8, fontweight="bold", ha="center")
    ax.axhline(floor, color=LGRAY, lw=0.5)
    ax.text(3.2, floor * 1.25, "0 errors in 2M bits (plotted at 3e-7)", fontsize=5.8, color=GRAY)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(3, 4000)
    ax.set_ylim(2e-7, 0.5)
    ax.set_xlabel("multiplications per symbol (exact; the paper's formula counts half)")
    ax.set_ylabel("BER (IM/DD, 24 dB)")
    ax.grid(True, which="major")
    ax.legend(loc="lower left", fontsize=5.9, ncol=2, bbox_to_anchor=(0.0, 0.07))
    save(fig, "fig05_dse.png")


# ===================================================================== Fig 6: DFE stress heatmap
def fig_dfe_heatmap():
    rows = jl(RES / "dfe_stress" / "results.jsonl")
    models = ["FFE57", "FFE121", "FFE25+DFE2", "FFE57+DFE2", "CNN", "CNN+DFE2"]
    heads = ["FFE-57", "FFE-121", "FFE-25\n+ DFE2", "FFE-57\n+ DFE2", "CNN", "CNN\n+ DFE2"]
    macs = ["57", "121", "27", "59", "121.5", "121.5"]
    conds = [(20, 20.0), (14, 31.5), (16, 31.5), (18, 31.5), (20, 31.5), (22, 31.5), (24, 31.5), (20, 40.0), (20, 50.0)]
    M = np.full((len(conds), len(models)), np.nan)
    med = np.full_like(M, np.nan)
    for i, (s, L) in enumerate(conds):
        for j, m in enumerate(models):
            v = sorted(r["ber"] for r in rows if r["snr"] == s and r["L"] == L and r["model"] == m)
            if v:
                M[i, j] = v[0]
                med[i, j] = np.median(v)
    floor = 1e-7
    Z = np.log10(np.maximum(M, floor))
    fig, ax = plt.subplots(figsize=(TEXTW, 3.15))
    im = ax.imshow(Z, cmap="YlGnBu_r", vmin=-7, vmax=-1.5, aspect="auto")
    for i in range(len(conds)):
        best = np.nanargmin(np.where(M[i] == 0, 1e-12, M[i]))
        for j in range(len(models)):
            v = M[i, j]
            txt = "0 errors" if v == 0 else f"{v:.1e}"
            if j >= 4 and not np.isnan(med[i, j]) and v > 0:
                txt += f"\n({med[i, j]:.1e})"
            dark = Z[i, j] < -4.6
            ax.text(j, i, txt, ha="center", va="center", fontsize=5.7, color="white" if dark else "#1a1a1a",
                    fontweight="bold" if j == best else "normal")
        ax.add_patch(Rectangle((best - 0.5, i - 0.5), 1, 1, fill=False, ec=ORANGE, lw=1.6))
    ax.set_xticks(range(len(models)), [f"{h}\n{m} MAC" for h, m in zip(heads, macs)], fontsize=6.3)
    ax.set_yticks(range(len(conds)), [f"{L:g} km, {s} dB" for s, L in conds], fontsize=6.5)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.axhline(0.5, color="white", lw=2)
    ax.axhline(6.5, color="white", lw=2)
    ax.axvline(3.5, color="white", lw=2)
    ax.xaxis.tick_top()
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015)
    cb.set_label(r"$\log_{10}$ BER (best of 3 seeds)", fontsize=6.5)
    cb.ax.tick_params(labelsize=6)
    ax.text(1.5, 9.05, "linear FFE (closed-form LS) + decision feedback", ha="center", fontsize=6.2, color=GRAY)
    ax.text(4.5, 9.05, "CNN (cross-entropy); CNN cells: best (median)", ha="center", fontsize=6.2, color=GRAY)
    save(fig, "fig06_dfe_heatmap.png")


# ===================================================================== Fig 7: quantization
def fig_quant():
    q = json.load(open(RES / "quant" / "summary.json"))
    dfe = {b: json.load(open(RES / "quant" / f"ours_bce_dfe_w{b}" / "metrics.json")) for b in (6, 7, 8)}
    fig, ax = plt.subplots(figsize=(TEXTW * 0.78, 2.55))
    style = {"paper_mse": (GRAY, "o--", "paper's CNN, MSE (paper recipe)"), "paper_bce": (GRAY, "o-", "paper's CNN, cross-entropy"),
             "ours_mse": (BLUE, "s--", "ours, MSE"), "ours_bce": (BLUE, "s-", "ours, cross-entropy")}
    for name, (c, st, lab) in style.items():
        rs = sorted([r for r in q if r["name"] == name], key=lambda r: r["bits"])
        line, = ax.plot([r["bits"] for r in rs], [r["qat_ber"] for r in rs], st, color=c, ms=3.2, lw=1.0, label=lab, mfc="white" if "--" in st else c)
        ax.axhline(rs[0]["fp32_ber"], color=c, ls=":", lw=0.6)
    bits = [6, 7, 8]
    ax.plot(bits, [dfe[b]["qat_ber"] for b in bits], "D-", color=GREEN, ms=3.8, lw=1.3, label="ours + DFE2 (cross-entropy)")
    ax.annotate("deployed:\nW8 CNN+DFE2\n5.0e-7", xy=(8, 5e-7), xytext=(6.9, 1.6e-7), fontsize=6, color=GREEN, arrowprops=dict(arrowstyle="-", color=GREEN, lw=0.6))
    ax.annotate("W6 CNN\n2.2e-5", xy=(6, 2.18e-5), xytext=(4.25, 1.2e-5), fontsize=6, color=BLUE, arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.6))
    ax.annotate("paper W8\n5.0e-4", xy=(8, 4.96e-4), xytext=(7.0, 2.1e-3), fontsize=6, color="#404040", arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.6))
    ax.set_yscale("log")
    ax.set_xlabel("bits (weights = activations = input)")
    ax.set_ylabel("BER of the integer model\n(fresh 4M-symbol test set)")
    ax.set_xticks([3, 4, 5, 6, 7, 8])
    ax.set_ylim(1e-7, 0.3)
    ax.grid(True, which="major")
    ax.legend(loc="upper right", fontsize=5.9)
    ax.text(3.05, 2.2e-7, "dotted lines: FP32 reference of each model", fontsize=5.8, color=GRAY)
    save(fig, "fig07_quant.png")


# ===================================================================== Fig 8: RTL microarchitecture
def fig_rtl():
    fig, ax, H = canvas(TEXTW, 3.75)
    label(ax, 0.5, H - 2.3, "(a) cnn_eq_top: layer chain (ours_bce_dfe_w8)", fontsize=7)
    y = H - 15
    chain = [("AXIS in", "8-bit samples\nTLAST = frame end", "white", GRAY), ("layer 0", "1→3, K9, s4\nPACK, FOLD 2", PALE, BLUE),
             ("layer 1", "3→3, K9, s1\nPACK, FOLD 2", PALE, BLUE), ("layer 2", "3→3, K9, s1\nPACK, FOLD 2", PALE, BLUE),
             ("layer 3", "3→4, K9, s2\nPACK, FOLD 4", PALE, BLUE), ("serializer", "4 lanes →\n1 symbol/beat", "white", BLUE),
             ("DFE", "look-ahead\n2 taps", "#E8F5EE", GREEN), ("AXIS out", "16-bit soft value\nbit = (u > 0)", "white", GRAY)]
    w, gap = 10.6, 1.85
    for i, (t, s, fc, ec) in enumerate(chain):
        x = 0.5 + i * (w + gap)
        box(ax, x, y, w, 9.5, t, s, fc=fc, ec=ec, tc=NAVY if ec != GREEN else "#1D5C3A", fs=6.4, sfs=5.2)
        if i:
            arrow(ax, (x - gap, y + 4.75), (x, y + 4.75), color=NAVY, lw=0.8)
    ax.add_patch(FancyBboxPatch((13.0, y + 11.3), 61.5, 3.0, boxstyle="round,pad=0,rounding_size=0.8", fc="#FFF4E8", ec=ORANGE, lw=0.7))
    ax.text(43.7, y + 12.8, "AXI-Lite: parameter memory (336 words: weights, biases, M, S, feedback taps) + control / counters",
            ha="center", va="center", fontsize=5.6, color="#7F3A0B")
    for i in range(1, 7):
        x = 0.5 + i * (w + gap) + w / 2
        if x < 74:
            arrow(ax, (x, y + 11.3), (x, y + 9.5), color=ORANGE, lw=0.6, ms=5)
    label(ax, 0.5, y - 4.5, "(b) inside one conv1d_stream layer", fontsize=7)
    y2 = y - 21
    blocks = [("window", "K x IC shift reg.\nzero pad / flush", "white"), ("pend → job", "held-back job\n(frame-end flag)", "white"),
              ("operand mux", "fold phase f\ntaps f·NM+m", "white"), ("DSP48E1 x NM", "2 channels / DSP\n(pre-adder pack)", PALE),
              ("adder trees", "per lane, growing\nwidth + borrow cnt", "white"), ("fold acc.", "sum FOLD\npartials", "white"),
              ("pair ser.", "lane 0, lane 1\n→ 1 ch / cycle", "white"), ("bias + requant", "(acc+b)·M + 2^(S-1)\n>>> S, clamp", "white"),
              ("collector", "OC channels →\noutput FIFO (16)", "white")]
    w2, gap2 = 9.4, 1.6
    for i, (t, s, fc) in enumerate(blocks):
        x = 0.5 + i * (w2 + gap2)
        box(ax, x, y2, w2, 11, t, s, fc=fc, ec=BLUE, fs=5.9, sfs=4.9)
        if i:
            arrow(ax, (x - gap2, y2 + 5.5), (x, y2 + 5.5), color=NAVY, lw=0.8)
    xe = 0.5 + 2 * (w2 + gap2)
    xf = 0.5 + 8 * (w2 + gap2) + w2 / 2
    arrow(ax, (xf, y2), (xe + w2 / 2, y2), color=RED, lw=0.8, cs="arc3,rad=0.18", ls="--")
    ax.text((xf + xe) / 2 + 3, y2 - 7.2, "credit: start a job only if OUT_DEPTH - occupancy - in flight > 0  (no overflow, no stall of the datapath)",
            ha="center", fontsize=5.5, color=RED)
    xa = 0.5 + 1 * (w2 + gap2) + w2 / 2
    arrow(ax, (xa, y2 + 11), (0.5 + w2 / 2, y2 + 11), color=GRAY, lw=0.7, cs="arc3,rad=-0.6", ls="--")
    ax.text(xa - 5, y2 + 15.2, "back-pressure (s_ready)", fontsize=5.3, color=GRAY, ha="center")
    ax.text(0.5, 1.0, "Every stage is registered; one output channel (or channel pair) is issued per cycle, so each layer sustains 1 input sample per clock.",
            fontsize=5.8, color="#404040")
    save(fig, "fig08_rtl.png")


# ===================================================================== Fig 9: DSP packing + DFE look-ahead
def fig_pack_dfe():
    fig, ax, H = canvas(TEXTW, 2.45)
    label(ax, 0.5, H - 2.5, "(a) two output channels in one DSP48E1", fontsize=7)
    ox, oy = 1.5, H - 15

    def field(x, y, w, h, txt, fc, ec=NAVY, fs=5.6):
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=0.7))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs)

    ax.text(ox, oy + 6.2, "A + D (pre-adder, 19 bit)", fontsize=5.8, color=NAVY)
    field(ox, oy, 15, 4.5, r"$w_{hi}\cdot 2^{PW}$", PALE)
    field(ox + 15, oy, 12, 4.5, r"$+\;w_{lo}$", "#FFF4E8")
    ax.text(ox + 29, oy + 2.2, r"$\times$", fontsize=10, va="center")
    field(ox + 32, oy, 10, 4.5, r"$a$  (B port)", "white")
    ax.text(ox, oy - 4.0, "P (product)", fontsize=5.8, color=NAVY)
    field(ox, oy - 10.5, 21, 4.5, r"$w_{hi}\cdot a\;-\;$borrow", PALE)
    field(ox + 21, oy - 10.5, 21, 4.5, r"$w_{lo}\cdot a$  (exact)", "#FFF4E8")
    ax.text(ox, oy - 15.5, "low field = PW bits, exact since |w_lo·a| < 2^(PW-1); high field reads one too low when the low\n"
                           "field is negative: the borrows are counted by a small adder tree and added once per sum.", fontsize=5.3, color="#404040")
    ax.text(ox, oy - 21.5, "Result: 136 → 45 DSP slices for the 6-bit model, < 1 % throughput cost.", fontsize=5.8, color=ORANGE, fontweight="bold")
    # DFE look-ahead
    label(ax, 52, H - 2.5, "(b) decision feedback, 1 symbol per clock", fontsize=7)
    bx, by = 52, H - 20
    box(ax, bx, by + 3, 7, 6, r"$z[n]$", fc="white", ec=GRAY, tc="#404040", fs=7)
    cands = [r"$z{+}f_1{+}f_2$", r"$z{+}f_1{-}f_2$", r"$z{-}f_1{+}f_2$", r"$z{-}f_1{-}f_2$"]
    for k, c in enumerate(cands):
        yy = by + 12 - k * 4.6
        box(ax, bx + 10.5, yy - 1.4, 12.5, 3.6, c, fc=PALE, ec=BLUE, fs=6.2, r=0.6)
        arrow(ax, (bx + 7, by + 6), (bx + 10.5, yy + 0.4), color=NAVY, lw=0.5, ms=4)
        arrow(ax, (bx + 23, yy + 0.4), (bx + 27.5, by + 6), color=NAVY, lw=0.5, ms=4)
    ax.add_patch(Polygon([(bx + 27.5, by - 1), (bx + 27.5, by + 13), (bx + 31.5, by + 10), (bx + 31.5, by + 2)], closed=True, fc="white", ec=NAVY, lw=0.8))
    ax.text(bx + 29.5, by + 6, "4:1", ha="center", va="center", fontsize=5.8)
    box(ax, bx + 34, by + 3, 8.5, 6, r"$u[n]$", r"$d=\mathrm{sgn}(u)$", fc="#E8F5EE", ec=GREEN, tc="#1D5C3A", fs=6.5, sfs=5.4)
    arrow(ax, (bx + 31.5, by + 6), (bx + 34, by + 6), color=NAVY, lw=0.8)
    arrow(ax, (bx + 38.25, by + 3), (bx + 29.5, by + 0.2), color=GREEN, lw=0.9, cs="arc3,rad=-0.5")
    ax.text(bx + 37, by - 4.2, "history (d[n-1], d[n-2]) selects", fontsize=5.4, color=GREEN, ha="center")
    ax.text(bx, by - 9.5, r"$u[n]=z[n]+f_{v,1}\,d[n{-}1]+f_{v,2}\,d[n{-}2]$, lane $v=n \bmod V_p$; candidates and their" "\n"
                          r"$>0$ flags are computed one stage early, so the loop is a 4:1 mux of 1-bit flags.", fontsize=5.6, color="#404040")
    ax.text(bx, by - 15.5, "Taps are integers fb/out_scale per lane; d = -1 before every frame.", fontsize=5.6, color="#404040")
    save(fig, "fig09_pack_dfe.png")


# ===================================================================== Fig 10: optimization journey
def fig_journey():
    revs = ["r1", "r2", "r3", "r4", "r4*", "r5", "r6", "r7", "r7b"]
    lut_f = [139.0, 182.3, np.nan, 199.2, 200.3, 201.7, 200.0, 200.0, 200.0]
    dsp_f = [np.nan, 174.0, 156.1, 198.7, 201.4, 200.4, 200.3, 204.8, 207.2]
    notes = ["one-step\nrequant", "split\nrequant", "rem calc\n(regressed)", "jobs-owed\ncounter", "timing\ndirectives",
             "no job FIFO,\nnarrow datapath", "fold + 1-stage\nmultipliers", "2 ch / DSP\n(attr. bug)", "attribute\nfix"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(TEXTW, 2.7), gridspec_kw=dict(width_ratios=[1.45, 1], wspace=0.32))
    x = np.arange(len(revs))
    a.axhline(200, color=RED, ls="--", lw=0.8)
    a.text(-0.3, 201.5, "200 MHz target", color=RED, fontsize=6)
    a.plot(x, lut_f, "o-", color=BLUE, ms=3.5, lw=1.1, label="ours W6, LUT multipliers")
    a.plot(x, dsp_f, "s-", color=ORANGE, ms=3.5, lw=1.1, label="ours W6, DSP multipliers")
    dx = np.array([6.6, 7.6, 8.6])
    a.plot(dx, [153.3, 195.6, 202.4], "D-", color=GREEN, ms=3.5, lw=1.1, label="ours W8 + DFE (r8, r8b, r8c)")
    for xx, v, t in zip(dx, [153.3, 195.6, 202.4], ["r8", "r8b", "r8c"]):
        a.text(xx + 0.12, v - 4, t, fontsize=5.5, color=GREEN)
    for i, n in enumerate(notes):
        a.text(i, 128, n, fontsize=4.7, ha="center", va="bottom", color="#404040", rotation=90)
    a.set_xticks(x, revs)
    a.set_ylim(125, 215)
    a.set_xlim(-0.5, 9.2)
    a.set_ylabel("Fmax (MHz), XC7Z020-1, OOC")
    a.set_xlabel("RTL revision  (* = with timing directives)")
    a.grid(True, axis="y")
    a.legend(loc="lower right", fontsize=5.7, bbox_to_anchor=(1.0, 0.25))
    a.set_title("(a) timing closure, revision by revision", loc="left", color=NAVY)
    rv = ["r4*", "r5", "r6", "r7b"]
    lut = [8592, 7316, 6464, 6580]
    dsp = [136, 136, 117, 45]
    xb = np.arange(len(rv))
    b.bar(xb - 0.2, np.array(lut) / 1000, 0.38, color=BLUE, label="LUT build: kLUTs")
    b2 = b.twinx()
    b2.bar(xb + 0.2, dsp, 0.38, color=ORANGE, label="DSP build: DSP slices")
    for i in range(len(rv)):
        b.text(xb[i] - 0.2, lut[i] / 1000 + 0.12, f"{lut[i] / 1000:.1f}", ha="center", fontsize=5.6, color=BLUE)
        b2.text(xb[i] + 0.2, dsp[i] + 2, f"{dsp[i]}", ha="center", fontsize=5.6, color=ORANGE)
    b.set_xticks(xb, rv)
    b.set_ylim(0, 10.5)
    b2.set_ylim(0, 160)
    b.set_ylabel("kLUT (LUT build)", color=BLUE)
    b2.set_ylabel("DSP slices (DSP build)", color=ORANGE)
    b2.spines["right"].set_visible(True)
    b.text(1.5, 9.8, "-23 % LUT, -67 % DSP", ha="center", fontsize=6.8, fontweight="bold", color=NAVY)
    b.set_title("(b) optimisation passes, 6-bit model", loc="left", color=NAVY)
    save(fig, "fig10_journey.png")


# ===================================================================== Fig 11: PYNQ-Z2 system
def fig_system():
    fig, ax, H = canvas(TEXTW, 2.95)
    ax.add_patch(FancyBboxPatch((0.5, 3), 24, H - 6, boxstyle="round,pad=0,rounding_size=1.5", fc="#F2F2F2", ec=GRAY, lw=0.9))
    ax.text(12.5, H - 5.2, "Zynq PS7 (ARM Cortex-A9)", ha="center", fontsize=6.8, fontweight="bold", color="#404040")
    box(ax, 3, H - 17, 19, 8, "DDR3 512 MB", "frames in / symbols out\n(PYNQ allocate)", fc="white", ec=GRAY, tc="#404040", fs=6, sfs=5.2)
    box(ax, 3, H - 29, 19, 8, "HP0 (64-bit)", "DMA data", fc="white", ec=ORANGE, tc="#7F3A0B", fs=6.2, sfs=5.2)
    box(ax, 3, H - 41, 19, 8, "GP0 (AXI master)", "control, weights", fc="white", ec=BLUE, tc=NAVY, fs=6.2, sfs=5.2)
    ax.text(12.5, 5.5, "FCLK0 100 MHz, FCLK1 200 MHz", ha="center", fontsize=5.6, color="#404040")
    # clock domains
    ax.add_patch(FancyBboxPatch((27, 3), 33, H - 6, boxstyle="round,pad=0,rounding_size=1.5", fc="#F6F9FD", ec=BLUE, lw=0.8, ls="--"))
    ax.text(43.5, H - 5.2, "FCLK0 = 100 MHz domain", ha="center", fontsize=6.4, fontweight="bold", color=BLUE)
    ax.add_patch(FancyBboxPatch((62, 3), 37.5, H - 6, boxstyle="round,pad=0,rounding_size=1.5", fc="#FDF6F1", ec=ORANGE, lw=0.8, ls="--"))
    ax.text(80.75, H - 5.2, "FCLK1 = 200 MHz domain", ha="center", fontsize=6.4, fontweight="bold", color=ORANGE)
    box(ax, 29, H - 21, 13, 12, "AXI\ninterconnect", None, fc="white", ec=BLUE, fs=5.8)
    box(ax, 44, H - 21, 14, 12, "AXI DMA", "MM2S / S2MM\n32-bit streams\n64-bit memory", fc="white", ec=BLUE, fs=6.2, sfs=5.0)
    box(ax, 29, H - 41, 29, 7.5, "AXI-Lite interconnect", "DMA registers + clock crossing to core", fc="white", ec=BLUE, fs=5.8, sfs=5.0)
    box(ax, 64, H - 14.5, 15, 6.5, "clock conv.", "+ 32→8 bit", fc="white", ec=ORANGE, tc="#7F3A0B", fs=5.6, sfs=5.0)
    box(ax, 64, H - 24, 15, 6.5, "clock conv.", "+ 16→32 bit", fc="white", ec=ORANGE, tc="#7F3A0B", fs=5.6, sfs=5.0)
    box(ax, 82, H - 30, 16, 22, "CNN + DFE\nequalizer", "ours_bce_dfe_w8\n5,421 LUT\n8,718 FF, 43 DSP\n0.213 W", fc=PALE, ec=NAVY, fs=6.5, sfs=5.2)
    arrow(ax, (22, H - 25), (29, H - 15), color=ORANGE, style="<|-|>", lw=0.8, ms=5)
    arrow(ax, (42, H - 15), (44, H - 15), color=BLUE, style="<|-|>", lw=0.8, ms=5)
    arrow(ax, (58, H - 11.2), (64, H - 11.2), color=NAVY, lw=0.8, ms=5, text="MM2S", tfs=5.0, toff=(0, 0.4))
    arrow(ax, (79, H - 11.2), (82, H - 11.2), color=NAVY, lw=0.8, ms=5)
    arrow(ax, (82, H - 20.7), (79, H - 20.7), color=NAVY, lw=0.8, ms=5)
    arrow(ax, (64, H - 20.7), (58, H - 18.5), color=NAVY, lw=0.8, ms=5, text="S2MM", tfs=5.0, toff=(0, 0.4))
    arrow(ax, (22, H - 37), (29, H - 37), color=BLUE, lw=0.8, ms=5)
    arrow(ax, (51, H - 33.5), (51, H - 21), color=BLUE, lw=0.7, ms=5)
    arrow(ax, (58, H - 37), (90, H - 30), color=BLUE, lw=0.7, ms=5, cs="arc3,rad=0.12")
    ax.text(74, H - 39.6, "weights + control (AXI-Lite)", fontsize=5.2, color=BLUE)
    ax.text(80.75, 5.0, "core WNS +0.160 ns at 200 MHz", ha="center", fontsize=5.8, color=ORANGE, fontweight="bold")
    ax.text(43.5, 5.0, "DMA WNS +1.778 ns", ha="center", fontsize=5.8, color=BLUE, fontweight="bold")
    save(fig, "fig11_system.png")


# ===================================================================== Fig 12: final comparison
def power_rows(name):
    t = open(EQ / "rtl" / "power" / f"power_{name}.rpt", encoding="utf8", errors="ignore").read()
    sec = t[t.find("1.1 On-Chip Components"):]
    sec = sec[sec.find("| On-Chip"):]
    out = {}
    for k in ("Clocks", "Slice Logic", "Signals", "DSPs", "Static Power"):
        m = re.search(r"\|\s*" + re.escape(k) + r"\s*\|\s*([<0-9.]+)", sec)
        out[k] = 0.0005 if m and m.group(1).startswith("<") else (float(m.group(1)) if m else 0.0)
    return out


BUILDS = [  # model, build, BER, LUT, FF, DSP, Fmax, power report
    ("paper's CNN W8", "DSP", 4.96e-4, 7056, 11543, 42, 187.9, "out_paper_mse_w8_5.0ns_dsp1_r8b"),
    ("paper's CNN W8", "LUT", 4.96e-4, 10907, 14840, 2, 196.3, "out_paper_mse_w8_5.0ns_dsp0_r8b"),
    ("ours W6", "DSP", 2.18e-5, 3957, 6393, 45, 207.2, "out_ours_bce_w6_5.0ns_dsp1_r7b"),
    ("ours W6", "LUT", 2.18e-5, 6580, 7620, 3, 200.0, "out_ours_bce_w6_5.0ns_dsp0_r7b"),
    ("ours W8 + DFE2", "DSP", 5.0e-7, 5430, 8919, 43, 202.4, "out_ours_bce_dfe_w8_5.0ns_dsp1_r8c"),
    ("ours W8 + DFE2", "LUT", 5.0e-7, 10331, 12383, 3, 195.8, "out_ours_bce_dfe_w8_5.0ns_dsp0_r8b"),
]
MCOL = {"paper's CNN W8": GRAY, "ours W6": BLUE, "ours W8 + DFE2": GREEN}


def fig_compare():
    fig, (a, b) = plt.subplots(1, 2, figsize=(TEXTW, 2.75), gridspec_kw=dict(width_ratios=[1.25, 1], wspace=0.33))
    for m, bld, ber, lut, ff, dsp, fmax, rpt in BUILDS:
        p = power_rows(rpt)
        dyn = p["Clocks"] + p["Slice Logic"] + p["Signals"] + p["DSPs"]
        a.scatter(lut / 1000, ber, s=dyn * 900, color=MCOL[m], alpha=0.55 if bld == "LUT" else 0.9,
                  marker="o" if bld == "DSP" else "s", edgecolor="black", lw=0.5, zorder=3)
        a.text(lut / 1000, ber * (0.42 if bld == "DSP" else 2.1), f"{bld}  {dyn:.2f} W", fontsize=5.4, ha="center", color="#333333")
    for m, c in MCOL.items():
        a.scatter([], [], s=40, color=c, label=m)
    a.set_yscale("log")
    a.set_xlim(2.5, 12.5)
    a.set_ylim(1.5e-7, 3e-3)
    a.set_xlabel("kLUT (out of context, XC7Z020)")
    a.set_ylabel("BER (integer model, 4M symbols)")
    a.grid(True, which="major")
    a.legend(loc="center right", fontsize=6, bbox_to_anchor=(1.0, 0.55))
    a.annotate("better", xy=(3.2, 3e-7), xytext=(5.2, 2.2e-6), fontsize=6.5, color=NAVY, fontweight="bold",
               arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.0))
    a.set_title("(a) accuracy vs area; marker area = dynamic power", loc="left", color=NAVY)
    metrics = ["LUT", "FF", "DSP", "dyn. power"]
    ref = None
    vals = {}
    for m, bld, ber, lut, ff, dsp, fmax, rpt in BUILDS:
        if bld != "DSP":
            continue
        p = power_rows(rpt)
        dyn = p["Clocks"] + p["Slice Logic"] + p["Signals"] + p["DSPs"]
        vals[m] = np.array([lut, ff, dsp, dyn])
    ref = vals["paper's CNN W8"]
    x = np.arange(len(metrics))
    for k, (m, v) in enumerate(vals.items()):
        r = v / ref
        b.bar(x + (k - 1) * 0.27, r, 0.25, color=MCOL[m], label=m)
        for xx, rr in zip(x + (k - 1) * 0.27, r):
            b.text(xx, rr + 0.02, f"{rr:.2f}", ha="center", fontsize=5.2, rotation=90, va="bottom")
    b.axhline(1, color=GRAY, lw=0.6, ls="--")
    b.set_xticks(x, metrics)
    b.set_ylim(0, 1.45)
    b.set_ylabel("relative to the paper's CNN")
    b.set_title("(b) DSP builds, same engine, same chip", loc="left", color=NAVY)
    b.grid(True, axis="y")
    save(fig, "fig12_compare.png")


# ===================================================================== Fig 13: power breakdown
def fig_power():
    fig, ax = plt.subplots(figsize=(TEXTW, 2.25))
    cats = [("Clocks", "#8FAADC"), ("Slice Logic", BLUE), ("Signals", NAVY), ("DSPs", ORANGE), ("Static Power", LGRAY)]
    labels = []
    for i, (m, bld, *_rest, rpt) in enumerate(BUILDS):
        p = power_rows(rpt)
        left = 0
        for k, c in cats:
            ax.barh(i, p[k], left=left, color=c, height=0.62, label=k if i == 0 else None, edgecolor="white", lw=0.4)
            if p[k] > 0.035:
                ax.text(left + p[k] / 2, i, f"{p[k]:.3f}", ha="center", va="center", fontsize=5.3, color="white" if k != "Static Power" else "#333333")
            left += p[k]
        ax.text(left + 0.006, i, f"{left:.3f} W", va="center", fontsize=6, color="#333333")
        labels.append(f"{m}, {bld}")
    ax.set_yticks(range(len(BUILDS)), labels, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlim(0, 0.58)
    ax.set_xlabel("on-chip power at 200 MHz (W), activity from gate-level simulation (SAIF), confidence High")
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.17), fontsize=6.2)
    ax.grid(True, axis="x")
    save(fig, "fig13_power.png")


# ===================================================================== Fig 14: verification pyramid
def fig_verif():
    fig, ax, H = canvas(TEXTW, 2.15)
    levels = [
        ("Integer golden model (Python)", "exact RTL arithmetic; matches fake-quant decisions > 99.9 %; 11 unit tests", "#F2F2F2", GRAY),
        ("Layer unit testbench", "16 configurations (K 1-15, stride 1-8, FOLD 1-3, PACK, signed/unsigned), random frames 1-120, random stalls", PALE, BLUE),
        ("Full-model testbench", "7 models x LUT/DSP x stall 0/30 %, bit-exact, TLAST and frame counters, throughput", PALE, BLUE),
        ("Mutation tests", "6 deliberately broken RTL copies (owed counter, fold, borrow, lane, DFE reset, tap order): all caught", "#FFF4E8", ORANGE),
        ("Gate-level routed netlists", "6/6 final builds bit-exact in post-route functional simulation (also the SAIF power runs)", "#E8F5EE", GREEN),
    ]
    n = len(levels)
    for i, (t, s, fc, ec) in enumerate(levels):
        y = 2 + i * (H - 4) / n
        h = (H - 4) / n - 1.0
        inset = i * 6.0
        ax.add_patch(Polygon([(inset, y), (60 - inset, y), (60 - inset - 6, y + h), (inset + 6, y + h)], closed=True, fc=fc, ec=ec, lw=0.9))
        ax.text(30, y + h / 2, t, ha="center", va="center", fontsize=6.4, fontweight="bold", color=NAVY if ec != GREEN else "#1D5C3A")
        ax.text(62, y + h / 2, s, ha="left", va="center", fontsize=5.6, color="#333333", wrap=True)
        ax.plot([60 - inset - 3, 61.5], [y + h / 2, y + h / 2], color=ec, lw=0.6)
    save(fig, "fig14_verif.png")


if __name__ == "__main__":
    which = sys.argv[1:] or None
    figs = [fig_pipeline, fig_link, fig_cnn, fig_proakis, fig_dse, fig_dfe_heatmap, fig_quant, fig_rtl, fig_pack_dfe,
            fig_journey, fig_system, fig_compare, fig_power, fig_verif]
    for f in figs:
        if which is None or f.__name__ in which:
            f()
