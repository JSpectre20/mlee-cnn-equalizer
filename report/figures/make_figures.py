r"""All report figures (one consistent style). Run from Project/ with the eqsim venv:
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
    "savefig.dpi": 300, "legend.frameon": False, "svg.fonttype": "path",
})


def save(fig, name):
    """Write the figure as PNG (300 dpi, Word fallback) and SVG (vector, what Word displays)."""
    for ext in (".png", ".svg"):
        fig.savefig(OUT / Path(name).with_suffix(ext), bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print("wrote", name, "+ .svg")


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


# ===================================================================== Fig 2: link model
def fig_link():
    from scipy import signal
    from eqsim.channels import IMDDChannel

    fig = plt.figure(figsize=(TEXTW, 3.9))
    gs = fig.add_gridspec(2, 3, height_ratios=[0.62, 1.45], width_ratios=[1.35, 1, 1], hspace=0.30, wspace=0.42,
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
    band = f < 24e9   # beyond ~24 GHz the 40 GHz-wide signal has almost no power, so the CSD estimate is noise
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.plot(f[band] / 1e9, 20 * np.log10(meas[band] / meas[1]), color=BLUE, lw=1.0, label="simulated link")
    ax1.plot(f[band] / 1e9, 20 * np.log10(theory[band] + 1e-6), "--", color=ORANGE, lw=0.9, label=r"$|\cos(\beta_2 L\,\omega^2/2)|$")
    for k in (0, 1):
        fn = small.fading_null_hz(k) / 1e9
        ax1.axvline(fn, color=GRAY, ls=":", lw=0.7)
        ax1.text(fn, 2.2, f"{fn:.1f} GHz", fontsize=6, color="#404040", ha="center", bbox=dict(fc="white", ec="none", pad=0.6))
    ax1.axvspan(0, 20, color=LIGHT, alpha=0.35, lw=0)
    ax1.text(0.6, -21, "signal band\n(Nyquist 20 GHz)", fontsize=6, color=NAVY)
    ax1.set_ylim(-40, 6)
    ax1.set_xlim(0, 24)
    ax1.set_xlabel("frequency (GHz)")
    ax1.set_ylabel("small-signal |H| (dB)")
    ax1.legend(loc="lower left", fontsize=6)
    ax1.set_title("(b) CD power fading: spectral nulls in band", loc="left", color=NAVY)
    eye0 = None
    for j, km in enumerate((0.0, ch.length_km)):
        ax = fig.add_subplot(gs[1, 1 + j], sharey=eye0)
        eye0 = eye0 or ax
        c = IMDDChannel(**{**ch.__dict__, "length_km": km, "snr_db": 30.0, "nos": 8})
        rx, _ = c(3000, np.random.default_rng(1))
        seg = rx[: (len(rx) // 16) * 16].reshape(-1, 16)
        t = np.arange(16) / 8
        ax.plot(t, seg[50:650].T, color=BLUE if km == 0 else ORANGE, alpha=0.06, lw=0.6)
        ax.set_xlabel("time (symbols)")
        if j == 0:
            ax.set_ylabel("received (normalized)")
        else:
            ax.tick_params(labelleft=False)
        ax.set_ylim(-3.2, 3.6)
        ax.set_title(f"({'c' if j == 0 else 'd'}) eye, {'back-to-back' if km == 0 else '31.5 km'}", loc="left", color=NAVY)
        ax.set_xlim(0, 1.875)
    save(fig, "fig02_link.png")


# ===================================================================== Fig 4: Proakis-B
def fig_proakis():
    r = json.load(open(RES / "proakis" / "results.json"))
    seeds = json.load(open(RES / "proakis" / "seeds.json"))["rows"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(TEXTW, 3.05), gridspec_kw=dict(width_ratios=[1.55, 1], wspace=0.30))
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
    a.text(140, 5.6e-2, "MLSE (4-state Viterbi):\n0 errors in 9.9e5 symbols", fontsize=6, color=GREEN, va="top")
    a.set_xscale("log")
    a.set_yscale("log")
    a.set_ylim(5e-4, 8e-2)
    a.set_xlabel("multiplications per symbol (exact)")
    a.set_ylabel("BER")
    a.grid(True, which="major")
    a.legend(loc="upper center", bbox_to_anchor=(0.62, -0.2), fontsize=5.8, ncol=3, columnspacing=1.0, handletextpad=0.4)
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
    b.set_ylim(3.5e-3, 9e-2)
    b.set_ylabel("BER (CNN, 10 seeds)")
    b.text(1.0, 3.81e-2, "  diverged run", fontsize=5.6, color=ORANGE, va="center")
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
    fig, ax = plt.subplots(figsize=(TEXTW, 3.45))
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
    ax.annotate("paper's 40 GBd hardware budget:\n147 MAC/symbol", xy=(147, 1.1e-6), xytext=(9, 1.1e-6), color=RED, fontsize=6.2, va="center",
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=0.7, shrinkA=2, shrinkB=0))
    pm = [e["ber"] for e in conf if e["key"].startswith("vp8_L3_K9_C5_mse")]
    ob = [e["ber"] for e in conf if e["key"].startswith("vp4_L4_K9_C3_bce")]
    ax.scatter([112.5], [min(pm)], marker="*", s=110, color="black", zorder=5, label=f"paper's CNN (fresh test) {min(pm):.1e}")
    ax.scatter([121.5], [min(ob)], marker="D", s=40, color=ORANGE, edgecolor="black", lw=0.5, zorder=5, label=f"ours vp4 L4 K9 C3 (fresh test) {min(ob):.1e}")
    ax.annotate("", xy=(121.5, min(ob) * 1.25), xytext=(112.5, min(pm) * 0.8), arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.0))
    ax.text(62, 4e-5, "~16x lower BER\nat similar cost", color=ORANGE, fontsize=6.8, fontweight="bold", ha="center")
    ax.axhline(floor, color=LGRAY, lw=0.5)
    ax.text(3.2, floor * 1.25, "0 errors in 2M bits (plotted at 3e-7)", fontsize=5.8, color=GRAY)
    ax.text(3.2, 3e-3, "FIR floor", fontsize=6, color="black")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(3, 4000)
    ax.set_ylim(2e-7, 0.5)
    ax.set_xlabel("multiplications per symbol (exact; the paper's formula counts half)")
    ax.set_ylabel("BER (IM/DD, 24 dB)")
    ax.grid(True, which="major")
    ax.legend(loc="upper center", fontsize=5.9, ncol=3, bbox_to_anchor=(0.5, -0.16), columnspacing=1.2)
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
    fig, ax = plt.subplots(figsize=(TEXTW, 2.95))
    im = ax.imshow(Z, cmap="YlGnBu_r", vmin=-7, vmax=-1.5, aspect="auto")
    for i in range(len(conds)):
        best = np.nanargmin(np.where(M[i] == 0, 1e-12, M[i]))
        for j in range(len(models)):
            v = M[i, j]
            txt = "0 errors" if v == 0 else f"{v:.1e}"
            if j >= 4 and not np.isnan(med[i, j]) and v > 0:
                txt += f"\n({med[i, j]:.1e})"
            dark = Z[i, j] < -4.6
            ax.text(j, i, txt, ha="center", va="center", fontsize=6.4, color="white" if dark else "#1a1a1a",
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
    ax.plot([], [], ":", color=GRAY, lw=0.8, label="FP32 reference of each model")
    ax.annotate("deployed:\nW8 CNN+DFE2\n5.0e-7", xy=(8, 5e-7), xytext=(6.75, 1.5e-7), fontsize=6, color=GREEN, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=GREEN, lw=0.6))
    ax.annotate("W6 CNN\n2.2e-5", xy=(6, 2.18e-5), xytext=(4.55, 1.6e-6), fontsize=6, color=BLUE, arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.6))
    ax.annotate("paper's CNN W8\n5.0e-4", xy=(8, 4.96e-4), xytext=(6.75, 6e-5), fontsize=6, color="#404040", arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.6))
    ax.set_yscale("log")
    ax.set_xlabel("bits (weights = activations = input)")
    ax.set_ylabel("BER of the integer model\n(fresh 4M-symbol test set)")
    ax.set_xticks([3, 4, 5, 6, 7, 8])
    ax.set_xlim(2.8, 8.3)
    ax.set_ylim(1e-7, 2.0)
    ax.grid(True, which="major")
    ax.legend(loc="upper right", fontsize=5.9, ncol=2, columnspacing=1.0)
    save(fig, "fig07_quant.png")


# ===================================================================== Fig 12: final comparison
def power_rows(name):
    t = open(EQ / "rtl" / "power" / f"power_{name}.rpt", encoding="utf8", errors="ignore").read()
    sec = t[t.find("1.1 On-Chip Components"):]
    sec = sec[sec.find("| On-Chip"):]
    out = {}
    for k in ("Clocks", "Slice Logic", "Signals", "DSPs", "Static Power"):
        m = re.search(r"\|\s*" + re.escape(k) + r"\s*\|\s*([<0-9.]+)", sec)
        out[k] = 0.0005 if m and m.group(1).startswith("<") else (float(m.group(1)) if m else 0.0)
    for k, lab in (("total", "Total On-Chip Power (W)"), ("dynamic", "Dynamic (W)")):   # report totals (not sums of rounded parts)
        out[k] = float(re.search(r"\|\s*" + re.escape(lab) + r"\s*\|\s*([0-9.]+)", t).group(1))
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
        dyn = p["dynamic"]
        a.scatter(lut / 1000, ber, s=dyn * 900, color=MCOL[m], alpha=0.55 if bld == "LUT" else 0.9,
                  marker="o" if bld == "DSP" else "s", edgecolor="black", lw=0.5, zorder=3)
        up = bld == "LUT" or m.startswith("paper")   # the paper's DSP label goes above: the ratio arrows leave below it
        a.text(lut / 1000, ber * (2.1 if up else 0.42), f"{bld}  {dyn:.2f} W", fontsize=5.4, ha="center", color="#333333")
    for m, c in MCOL.items():
        a.scatter([], [], s=40, color=c, label=m)
    a.set_yscale("log")
    a.set_xlim(2.5, 12.5)
    a.set_ylim(1.5e-7, 3e-3)
    a.set_xlabel("kLUT (out of context, XC7Z020)")
    a.set_ylabel("BER (integer model, 4M symbols)")
    a.grid(True, which="major")
    a.legend(loc="center right", fontsize=6, bbox_to_anchor=(1.0, 0.5))
    # headline ratios (DSP builds): from the paper's CNN to ours
    p0 = (7.056, 4.96e-4)
    for (x1, y1), txt, xy_t, c in (((5.43, 5.0e-7), "~1000x lower BER\nat the same 8 bits,\n-23 % LUT", (6.25, 4.2e-6), GREEN),
                                   ((3.957, 2.18e-5), "23x lower BER,\n-44 % LUT", (2.65, 2.7e-4), BLUE)):
        a.annotate("", xy=(x1 + 0.12, y1 * 2.2), xytext=(p0[0] - 0.12, p0[1] / 1.9),
                   arrowprops=dict(arrowstyle="-|>", color=c, lw=1.0, shrinkA=0, shrinkB=0))
        a.text(*xy_t, txt, fontsize=6.0, color=c, fontweight="bold", ha="left", va="center")
    a.set_title("(a) accuracy vs area; marker area = dynamic power", loc="left", color=NAVY)
    metrics = ["LUT", "FF", "DSP", "dyn. power"]
    ref = None
    vals = {}
    for m, bld, ber, lut, ff, dsp, fmax, rpt in BUILDS:
        if bld != "DSP":
            continue
        p = power_rows(rpt)
        dyn = p["dynamic"]
        vals[m] = (np.array([lut, ff, dsp, dyn]), ber)
    ref = vals["paper's CNN W8"][0]
    x = np.arange(len(metrics))
    for k, (m, (v, ber)) in enumerate(vals.items()):
        r = v / ref
        b.bar(x + (k - 1) * 0.27, r, 0.25, color=MCOL[m], label=f"{m}: BER {ber:.1e}")
        for xx, rr in zip(x + (k - 1) * 0.27, r):
            b.text(xx, rr + 0.02, f"{rr:.2f}", ha="center", fontsize=5.2, rotation=90, va="bottom")
    b.axhline(1, color=GRAY, lw=0.6, ls="--")
    b.set_xticks(x, metrics)
    b.set_ylim(0, 1.75)
    b.legend(loc="upper center", fontsize=5.8, ncol=1, bbox_to_anchor=(0.5, 1.0))
    b.set_ylabel("relative to the paper's CNN")
    b.set_title("(b) DSP builds, same engine, same chip", loc="left", color=NAVY)
    b.grid(True, axis="y")
    save(fig, "fig12_compare.png")


if __name__ == "__main__":
    which = sys.argv[1:] or None
    # data figures only; the block diagrams (fig01, fig07_hardware, fig09) come from report/diagrams/build_diagrams.py
    figs = [fig_link, fig_proakis, fig_dse, fig_dfe_heatmap, fig_quant, fig_compare]
    for f in figs:
        if which is None or f.__name__ in which:
            f()
