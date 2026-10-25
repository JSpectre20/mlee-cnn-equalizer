"""Plot and summarize the IM/DD design-space sweep (results of run_imdd_dse.py).

Produces results/imdd_dse/dse.png (BER vs exact MAC/symbol for FIR, Volterra
and all CNN configs, MSE vs cross-entropy) and prints a summary table.

The vertical line is the paper's 40 GBd budget on the XCVU13P,
MAC_max = DSP / (T_req / f_clk) * 1.2 = 12288 / (40e9 / 200e6) * 1.2 = 73.7,
which is in the paper's per-sample units; x Nos = 147 MAC per symbol.
"""
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("results/imdd_dse")
BUDGET_EXACT = 12288 / (40e9 / 200e6) * 1.2 * 2
PAPER_CFG = dict(vp=8, layers=3, kernel=9, channels=5)


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def pareto(points):
    pts = sorted(points)
    front, best = [], np.inf
    for m, b in pts:
        if b < best:
            front.append((m, b))
            best = b
    return front


def main():
    base = json.loads((OUT / "baselines.json").read_text())
    runs = load_jsonl(OUT / "screen.jsonl") + load_jsonl(OUT / "refine.jsonl")
    by_cfg = defaultdict(list)
    for r in runs:
        by_cfg[(r["vp"], r["layers"], r["kernel"], r["channels"], r["loss"])].append(r)

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    colors = {"mse": "tab:blue", "bce": "tab:red"}
    for kind, marker in (("fir", "o"), ("volterra", "s")):
        for loss in ("mse", "bce"):
            rows = sorted([r for r in base if r["kind"] == kind and r["loss"] == loss], key=lambda r: r["macs"])
            ax.plot([r["macs"] for r in rows], [max(r["ber"], 1e-7) for r in rows], marker + ("--" if loss == "mse" else "-"),
                    color="gray" if kind == "fir" else "tab:green", mfc="none" if loss == "mse" else None, ms=5,
                    label=f"{kind.upper() if kind == 'fir' else 'Volterra'}, {'MSE' if loss == 'mse' else 'cross-entropy'}")
    summary = {}
    for loss in ("mse", "bce"):
        pts = []
        for (vp, L, K, C, l), rs in by_cfg.items():
            if l != loss:
                continue
            best = min(r["ber"] for r in rs)
            pts.append((rs[0]["macs"], max(best, 1e-7)))
        if not pts:
            continue
        ax.scatter(*zip(*pts), s=10, color=colors[loss], alpha=0.35, label=f"CNN configs, {loss.upper()}")
        front = pareto(pts)
        ax.plot(*zip(*front), "-", color=colors[loss], lw=1.5, label=f"CNN Pareto front, {loss.upper()}")
        sel = by_cfg.get((8, 3, 9, 5, loss))
        if sel:
            b = min(r["ber"] for r in sel)
            ax.plot(sel[0]["macs"], b, "*", color=colors[loss], ms=14, mec="k", label=f"paper's CNN, {loss.upper()}")
            summary[f"paper_cnn_{loss}"] = {"macs": sel[0]["macs"], "best_ber": b, "seeds": len(sel), "all": sorted(r["ber"] for r in sel)}
        summary[f"pareto_{loss}"] = front
    ax.axvline(BUDGET_EXACT, color="k", ls=":", lw=1, label="paper's 40 GBd budget (exact units)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("MAC operations per symbol (exact count)")
    ax.set_ylabel("BER")
    ax.set_title("Simulated 40 GBd PAM2 IM/DD, 31.5 km SSMF")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=7, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "dse.png", dpi=150)

    def best_under(rows, budget):
        ok = [r for r in rows if r["macs"] <= budget]
        return min(ok, key=lambda r: r["ber"]) if ok else None

    for kind in ("fir", "volterra"):
        for loss in ("mse", "bce"):
            r = best_under([x for x in base if x["kind"] == kind and x["loss"] == loss], BUDGET_EXACT)
            summary[f"best_{kind}_{loss}_within_budget"] = r and {"spec": r["spec"], "macs": r["macs"], "ber": r["ber"]}
    for loss in ("mse", "bce"):
        cands = [{"cfg": k[:4], "macs": rs[0]["macs"], "ber": min(r["ber"] for r in rs)} for k, rs in by_cfg.items() if k[4] == loss]
        summary[f"best_cnn_{loss}_within_budget"] = best_under(cands, BUDGET_EXACT)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
