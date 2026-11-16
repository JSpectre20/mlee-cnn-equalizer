r"""Build the report's block diagrams.

TikZ sources (report/diagrams/tikz/figNN_*.tex) are compiled with Tectonic, draw.io sources
(report/diagrams/drawio/figNN_*.drawio) are exported with the draw.io desktop CLI; both go to PDF,
then PyMuPDF writes report/figures/figNN_*.svg (vector, text as paths, what Word shows) and
report/figures/figNN_*.png (300 dpi fallback).

Run from Project/:  D:\venvs\mlee-eq\Scripts\python.exe report\diagrams\build_diagrams.py [name ...]
Tools: D:\tools\tectonic\tectonic.exe (0.17.0), %LOCALAPPDATA%\Programs\draw.io\draw.io.exe (32.6).
"""
import os
import subprocess
import sys
from pathlib import Path

import pymupdf as fitz

HERE = Path(__file__).resolve().parent
FIG = HERE.parent / "figures"
BUILD = HERE / "build"
TECTONIC = Path(r"D:\tools\tectonic\tectonic.exe")
DRAWIO = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "draw.io" / "draw.io.exe"


def pdf_to_figures(pdf: Path, name: str):
    doc = fitz.open(pdf)
    page = doc[0]
    (FIG / f"{name}.svg").write_text(page.get_svg_image(text_as_path=True), encoding="utf8")
    page.get_pixmap(dpi=300, alpha=False).save(FIG / f"{name}.png")
    w, h = page.rect.width / 72 * 2.54, page.rect.height / 72 * 2.54
    print(f"wrote {name}.svg/.png  ({w:.1f} x {h:.1f} cm)")


def build_tikz(src: Path):
    BUILD.mkdir(exist_ok=True)
    r = subprocess.run([str(TECTONIC), "--keep-logs", "--outdir", str(BUILD), src.name], cwd=src.parent,
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"tectonic failed on {src.name}")
    pdf_to_figures(BUILD / f"{src.stem}.pdf", src.stem)


def build_drawio(src: Path):
    BUILD.mkdir(exist_ok=True)
    pdf = BUILD / f"{src.stem}.pdf"
    r = subprocess.run([str(DRAWIO), "-x", "-f", "pdf", "--crop", "-o", str(pdf), str(src)], capture_output=True, text=True)
    if r.returncode or not pdf.exists():
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"draw.io export failed on {src.name}")
    pdf_to_figures(pdf, src.stem)


if __name__ == "__main__":
    want = set(sys.argv[1:])
    for src in sorted((HERE / "tikz").glob("fig*.tex")):
        if not want or src.stem in want:
            build_tikz(src)
    for src in sorted((HERE / "drawio").glob("fig*.drawio")):
        if not want or src.stem in want:
            build_drawio(src)
