r"""Poster version of the hardware figure (report Fig. 3), simplified so that its labels print at about 24 pt on A0
(8 pt when the poster is printed at A3). Writes report/poster/poster_hw.drawio and exports fig_method.pdf / .png.

Run from Project/:  D:\venvs\mlee-eq\Scripts\python.exe report\poster\gen_poster_hw.py
Facts as in the report: PROGRESS.md 5.6, rtl/history/CHANGES.md, checkpoints/hw_v2 reports.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "diagrams" / "drawio"))
from gen_drawio import (BLUE, BROWN, DGREEN, GRAY, GREEN, NAVY, ORANGE, PALE, PGRAY, PGREEN, PORANGE,  # noqa: E402
                        Diagram)

DRAWIO = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "draw.io" / "draw.io.exe"


def build():
    d = Diagram()
    T, S = 19, 16.5            # title / detail font (px); canvas 640 px wide, printed ~30 cm wide on A0
    # ------------------------------------------------------------- (a) system
    d.text(0, 0, 640, 24, "<b>(a) PYNQ-Z2 system</b>", fs=T, color=NAVY)
    ps = d.box(0, 34, 122, 104, "Zynq PS7", "ARM + DDR3<br>(PYNQ)", fc=PGRAY, ec=GRAY, tc="#404040", fs=T, sfs=S)
    dma = d.box(178, 34, 112, 104, "AXI DMA", "100 MHz", ec=BLUE, fs=T, sfs=S)
    d.edge(ps, dma, color=ORANGE, lw=2.4, start="block", label="HP0", fs=S)
    core = d.box(330, 26, 310, 120, "", fc="#FDF6F1", ec=ORANGE, dashed=True, lw=1.8)
    d.text(330, 30, 310, 22, "<b>4 conv layers + DFE, 200 MHz</b>", fs=S, color=ORANGE, align="center")
    names = ["L1", "L2", "L3", "L4", "DFE"]
    cw, cg, cx = 50, 8, 343
    cells = []
    for i, n in enumerate(names):
        dfe = n == "DFE"
        cells.append(d.box(cx + i * (cw + cg), 64, cw, 54, n, "", fc=PGREEN if dfe else PALE, ec=GREEN if dfe else BLUE,
                           tc=DGREEN if dfe else NAVY, fs=T))
    for a, b in zip(cells, cells[1:]):
        d.edge(a, b, lw=2.0)
    d.edge(dma, cells[0], color=NAVY, lw=2.4, exit=(1, 0.5), entry=(0, 0.5), start="block")
    d.text(330, 124, 310, 20, "5,421 LUT, 43 DSP, slack +0.16 ns", fs=S, color=BROWN, bold=True, align="center")
    d.text(0, 146, 330, 22, "weights loaded at run time over AXI-Lite", fs=S, color="#404040")

    # ------------------------------------------------------------- (b) one layer
    y0 = 186
    d.text(0, y0, 640, 24, "<b>(b) One streaming layer, one output per clock</b>", fs=T, color=NAVY)
    blocks = [("Window", "shift reg."), ("Multiply", "2 ch / DSP"), ("Adder tree", "+ borrows"), ("Requant", "×M, ≫S"),
              ("FIFO", "16 deep")]
    bw = 112
    bg = (640 - 5 * bw) / 4
    bl = []
    for i, (t, s) in enumerate(blocks):
        bl.append(d.box(i * (bw + bg), y0 + 38, bw, 74, t, s, fc=PALE if t == "Multiply" else "#FFFFFF", fs=T, sfs=S))
    for a, b in zip(bl, bl[1:]):
        d.edge(a, b, lw=2.2)
    d.edge(bl[4], bl[0], color="#C00000", lw=1.8, dashed=True, exit=(0.5, 1), entry=(0.5, 1),
           pts=[(4 * (bw + bg) + bw / 2, y0 + 138), (bw / 2, y0 + 138)], label="credit: start only if the FIFO has room",
           fs=S)
    path = HERE / "poster_hw.drawio"
    d.save(path, "poster_hw")
    pdf = HERE / "fig_method.pdf"
    r = subprocess.run([str(DRAWIO), "-x", "-f", "pdf", "--crop", "-o", str(pdf), str(path)], capture_output=True, text=True)
    if r.returncode or not pdf.exists():
        raise SystemExit(r.stderr[-2000:])
    import pymupdf
    pymupdf.open(pdf)[0].get_pixmap(dpi=150).save(HERE / "fig_method.png")
    print("wrote", pdf.name)


if __name__ == "__main__":
    build()
