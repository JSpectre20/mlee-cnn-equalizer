"""One-off generator of the draw.io sources fig01_pipeline.drawio and fig07_hardware.drawio.

After generation the .drawio files are the sources of truth: open them in draw.io desktop to edit by
hand, then run report/diagrams/build_diagrams.py. Re-running this script overwrites hand edits
(it refuses unless --force is given).
Facts: rtl/src/*.sv, rtl/gen/ours_bce_dfe_w8 and the Vivado reports of checkpoints/hw_v2.
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
NAVY, BLUE, LIGHT, PALE = "#1F3864", "#2E75B6", "#D9E2F3", "#EAF1FB"
ORANGE, PORANGE, BROWN = "#C55A11", "#FFF4E8", "#7F3A0B"
GREEN, PGREEN, DGREEN = "#2E8B57", "#E8F5EE", "#1D5C3A"
GRAY, PGRAY, TXT = "#7F7F7F", "#F2F2F2", "#333333"


class Diagram:
    def __init__(self):
        self.cells, self.n = [], 1

    def _id(self):
        self.n += 1
        return f"c{self.n}"

    def box(self, x, y, w, h, title, sub="", fc="#FFFFFF", ec=BLUE, tc=NAVY, fs=9, sfs=7.5, rounded=True, dashed=False,
            bold=True, align="center", valign="middle", lw=1.2, extra=""):
        cid = self._id()
        t = f'<b>{title}</b>' if bold and title else title   # titles are trusted HTML written in this script
        if sub:
            t += f'<br><font style="font-size:{sfs}px" color="{TXT}">{sub}</font>'
        style = (f"rounded={int(rounded)};arcSize=8;whiteSpace=wrap;html=1;fillColor={fc};strokeColor={ec};fontColor={tc};"
                 f"fontFamily=Arial;fontSize={fs};align={align};verticalAlign={valign};strokeWidth={lw};"
                 f"dashed={int(dashed)};spacing=3;{extra}")
        self.cells.append(f'<mxCell id="{cid}" value="{escape(t, {chr(34): "&quot;"})}" style="{style}" vertex="1" parent="1">'
                          f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return cid

    def text(self, x, y, w, h, s, fs=8, color=TXT, bold=False, align="left", italic=False):
        cid = self._id()
        st = 1 * bold + 2 * italic
        style = (f"text;html=1;whiteSpace=wrap;fontFamily=Arial;fontSize={fs};fontColor={color};align={align};"
                 f"verticalAlign=middle;fontStyle={st};spacing=0;")
        self.cells.append(f'<mxCell id="{cid}" value="{escape(s, {chr(34): "&quot;"})}" style="{style}" vertex="1" parent="1">'
                          f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return cid

    def edge(self, a, b, color=NAVY, lw=1.2, dashed=False, label="", fs=7, exit=None, entry=None, pts=(), end="block",
             start="none", curved=False, lcolor=None):
        cid = self._id()
        style = (f"edgeStyle={'none' if curved else 'orthogonalEdgeStyle'};rounded=1;html=1;strokeColor={color};strokeWidth={lw};"
                 f"endArrow={end};endFill=1;startArrow={start};startFill=1;endSize=5;startSize=5;dashed={int(dashed)};"
                 f"fontFamily=Arial;fontSize={fs};fontColor={lcolor or color};labelBackgroundColor=#FFFFFF;")
        if curved:
            style += "curved=1;"
        if exit:
            style += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry:
            style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        geo = '<mxGeometry relative="1" as="geometry">'
        if pts:
            geo += '<Array as="points">' + "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in pts) + '</Array>'
        geo += '</mxGeometry>'
        self.cells.append(f'<mxCell id="{cid}" value="{escape(label, {chr(34): "&quot;"})}" style="{style}" edge="1" parent="1" '
                          f'source="{a}" target="{b}">{geo}</mxCell>')
        return cid

    def save(self, path, name):
        body = "".join(self.cells)
        xml = (f'<mxfile host="drawio"><diagram name="{name}" id="{name}"><mxGraphModel dx="800" dy="600" grid="1" gridSize="5" '
               f'page="0" math="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram></mxfile>')
        path.write_text(xml, encoding="utf8")
        print("wrote", path.name)




# Font sizes are in draw.io px; the 640-px-wide canvas is printed at 15.9 cm, i.e. 1 px = 0.70 pt, so
# 10 px = 7 pt (titles) and 8.5 px = 6 pt (details).

# ======================================================================= Figure 1: workflow
def fig_pipeline():
    d = Diagram()
    W = 640
    d.box(0, 0, W, 140, "", fc="#F6F9FD", ec=LIGHT, rounded=False, lw=1)
    d.box(0, 158, W, 158, "", fc="#FDF6F1", ec="#F2D3BF", rounded=False, lw=1)
    d.text(10, 4, 600, 18, "<b>Algorithm and learning</b>  (Python, PyTorch; package <i>eqsim</i>)", fs=10.5, color=BLUE)
    d.text(10, 294, 600, 18, "<b>Hardware</b>  (hand-written SystemVerilog, Vivado / xsim 2025.2, PYNQ-Z2)", fs=10.5, color=ORANGE)
    top = [("1  Channels", "40 GBd PAM2 IM/DD,<br>31.5 km SSMF;<br>Proakis-B"),
           ("2  Baselines", "FIR, Volterra,<br>FFE + DFE, MLSE"),
           ("3  CNN search", "135 topologies<br>&times; MSE / cross-entropy,<br>3 seeds, fresh test"),
           ("4  CNN + DFE", "2 feedback taps,<br>9 channel conditions"),
           ("5  Quantization", "QAT 3&ndash;8 bit,<br>integer golden model")]
    bot = [("6  Export", "params.mem, package,<br>test vectors"),
           ("7  Streaming RTL", "conv1d_stream &times; L,<br>DSP packing,<br>DFE look-ahead"),
           ("8  Verification", "unit, full model,<br>mutation, gate level"),
           ("9  Implementation", "timing closure,<br>200 MHz, SAIF power"),
           ("10  PYNQ-Z2", "PS7 + AXI DMA,<br>two clock domains")]
    w, h, gap, x0 = 114, 90, 17.5, 8
    tops, bots = [], []
    for i, (t, s) in enumerate(top):
        tops.append(d.box(x0 + i * (w + gap), 34, w, h, t, s, ec=BLUE, fs=10, sfs=8.6))
    for i, (t, s) in enumerate(bot):
        bots.append(d.box(x0 + i * (w + gap), 196, w, h, t, s, ec=ORANGE, tc=BROWN, fs=10, sfs=8.6))
    for a, b in zip(tops, tops[1:]):
        d.edge(a, b, color=BLUE, lw=1.5)
    for a, b in zip(bots, bots[1:]):
        d.edge(a, b, color=ORANGE, lw=1.5)
    xg = x0 + 4 * (w + gap) + w / 2
    d.edge(tops[4], bots[0], color=NAVY, lw=1.5, exit=(0.5, 1), entry=(0, 0.5), pts=[(xg, 149), (3, 149), (3, 241)],
           label="exports weights, biases, M, S, feedback taps", fs=9)
    d.edge(tops[4], bots[2], color=NAVY, lw=1.1, dashed=True, exit=(0.3, 1), entry=(0.5, 0),
           pts=[(x0 + 4 * (w + gap) + w * 0.3, 168), (x0 + 2 * (w + gap) + w / 2, 168)])
    d.text(x0 + 2 * (w + gap) + w / 2 + 8, 172, 260, 14, "expected outputs: bit-exact reference", fs=9, color=NAVY, italic=True)
    d.save(HERE / "fig01_pipeline.drawio", "pipeline")


# ======================================================================= Figure 7 (report Fig. 3): hardware
def fig_hardware():
    d = Diagram()
    # ---------------------------------------------------------------- (a) system
    d.text(0, 0, 640, 16, "<b>(a) PYNQ-Z2 system (XC7Z020) with the deployed CNN + DFE equalizer</b>", fs=10.5, color=NAVY)
    d.box(0, 22, 104, 196, "", fc=PGRAY, ec=GRAY, lw=1.2)
    d.text(2, 26, 100, 14, "<b>Zynq PS7</b>", fs=10, color="#404040", align="center")
    d.text(2, 40, 100, 12, "ARM Cortex-A9", fs=8.5, color="#404040", align="center")
    gp0 = d.box(8, 58, 88, 38, "GP0 master", "control, weights", ec=BLUE, fs=9.5, sfs=8.5)
    hp0 = d.box(8, 116, 88, 38, "HP0 slave", "64-bit DMA data", ec=ORANGE, tc=BROWN, fs=9.5, sfs=8.5)
    ddr = d.box(8, 170, 88, 38, "DDR3", "frames, symbols", ec=GRAY, tc="#404040", fs=9.5, sfs=8.5)
    d.edge(ddr, hp0, color=GRAY, lw=1.1, start="block")
    # 100 MHz domain
    d.box(112, 22, 124, 196, "", fc="#F6F9FD", ec=BLUE, dashed=True, lw=1.1)
    d.text(112, 26, 124, 14, "<b>FCLK0 100 MHz</b>", fs=10, color=BLUE, align="center")
    lite = d.box(120, 48, 108, 44, "AXI-Lite<br>interconnect", "clock crossing", fs=9.5, sfs=8.5)
    dma = d.box(120, 108, 108, 84, "AXI DMA", "MM2S: DDR &rarr; core<br>S2MM: core &rarr; DDR<br>32-bit streams", fs=9.5, sfs=8.5)
    d.edge(gp0, lite, color=BLUE, lw=1.3, exit=(1, 0.5), entry=(0, 0.5))
    d.edge(hp0, dma, color=ORANGE, lw=1.5, start="block", exit=(1, 0.5), entry=(0, 0.25))
    d.edge(lite, dma, color=BLUE, lw=1.1, exit=(0.5, 1), entry=(0.5, 0))
    d.text(112, 200, 124, 14, "WNS +1.778 ns", fs=9, color=BLUE, bold=True, align="center")
    # 200 MHz domain
    d.box(244, 22, 396, 196, "", fc="#FDF6F1", ec=ORANGE, dashed=True, lw=1.1)
    d.text(244, 26, 396, 14, "<b>FCLK1 200 MHz</b>", fs=10, color=ORANGE, align="center")
    cin = d.box(250, 106, 60, 42, "clock +<br>width", "32 &rarr; 8 bit", ec=ORANGE, tc=BROWN, fs=8.5, sfs=8)
    cout = d.box(250, 152, 60, 42, "clock +<br>width", "16 &rarr; 32 bit", ec=ORANGE, tc=BROWN, fs=8.5, sfs=8)
    d.edge(dma, cin, color=NAVY, lw=1.4, exit=(1, 0.21), entry=(0, 0.5), label="MM2S", fs=8.5)
    d.edge(cout, dma, color=NAVY, lw=1.4, exit=(0, 0.5), entry=(1, 0.75), label="S2MM", fs=8.5)
    # equalizer core
    d.box(318, 44, 316, 152, "", fc="#FFFFFF", ec=NAVY, lw=1.7)
    d.text(324, 47, 304, 14, "<b>cnn_eq_top</b>  ours_bce_dfe_w8: K = 9, 8-bit weights and activations", fs=8.8, color=NAVY)
    pm = d.box(324, 64, 304, 22, "AXI-Lite registers + parameter memory (336 words)", fc=PORANGE, ec=ORANGE, tc=BROWN, fs=8.8, bold=False)
    chain = [("layer 0", "1&rarr;3 ch<br>stride 4"), ("layer 1", "3&rarr;3 ch<br>stride 1"), ("layer 2", "3&rarr;3 ch<br>stride 1"),
             ("layer 3", "3&rarr;4 ch<br>stride 2"), ("serial-<br>izer", "4 &rarr; 1"), ("DFE", "2 taps,<br>look-ahead")]
    cw, cg, cx = 46, 5.6, 324
    cells = []
    for i, (t, s) in enumerate(chain):
        is_dfe = t == "DFE"
        cells.append(d.box(cx + i * (cw + cg), 102, cw, 48, t, s, fc=PGREEN if is_dfe else (PALE if i < 4 else "#FFFFFF"),
                           ec=GREEN if is_dfe else BLUE, tc=DGREEN if is_dfe else NAVY, fs=8.8, sfs=7.8))
    for a, b in zip(cells, cells[1:]):
        d.edge(a, b, lw=1.2)
    d.edge(cin, cells[0], lw=1.4, exit=(1, 0.5), entry=(0, 0.6))
    dx = cx + 5 * (cw + cg) + cw / 2
    d.edge(cells[-1], cout, lw=1.4, exit=(0.5, 1), entry=(1, 0.5), pts=[(dx, 173)])
    d.text(324, 153, 304, 13, "in: 8-bit samples, TLAST = frame end", fs=8.2, color="#404040")
    d.text(324, 177, 304, 14, "out: 16-bit soft value <i>u</i>, bit = (<i>u</i> &gt; 0)", fs=8.2, color="#404040")
    for k in (0, 1, 2, 3, 5):
        d.edge(pm, cells[k], color=ORANGE, lw=0.9, exit=((cw / 2 + k * (cw + cg)) / 304, 1), entry=(0.5, 0))
    d.edge(lite, pm, color=BLUE, lw=1.1, exit=(1, 0.5), entry=(0, 0.5), pts=[(240, 70), (240, 75)])
    d.text(244, 200, 396, 14, "core WNS +0.160 ns; 5,421 LUT, 8,718 FF, 43 DSP, no BRAM", fs=9, color=ORANGE, bold=True, align="center")

    # ---------------------------------------------------------------- (b) one layer
    y0 = 234
    d.text(0, y0, 640, 16, "<b>(b) Inside one conv1d_stream layer</b> (all stages registered; one output channel or pair per cycle)",
           fs=10.5, color=NAVY)
    blocks = [("Window", "K&times;IC shift reg.,<br>zero pad, flush"), ("Hold-back", "last job carries<br>the frame end"),
              ("Operand mux", "fold phase <i>f</i><br>selects taps"), ("Multipliers", "LUT or DSP48E1,<br>2 ch per DSP"),
              ("Adder trees", "growing width,<br>borrow count"), ("Fold acc.", "sums the FOLD<br>partials"),
              ("Requant", "&times;M, round,<br>&gt;&gt;&gt; S, clamp"), ("Collector", "OC channels,<br>FIFO of 16")]
    bw, bx, by = 72, 0, y0 + 46
    bg = (640 - 8 * bw) / 7
    bl = []
    for i, (t, s) in enumerate(blocks):
        bl.append(d.box(bx + i * (bw + bg), by, bw, 58, t, s, fc=PALE if t == "Multipliers" else "#FFFFFF", fs=9.5, sfs=8.2))
    for a, b in zip(bl, bl[1:]):
        d.edge(a, b, lw=1.2)
    d.edge(bl[7], bl[1], color="#C00000", lw=1.1, dashed=True, exit=(0.5, 1), entry=(0.5, 1),
           pts=[(bx + 7 * (bw + bg) + bw / 2, by + 76), (bx + 1 * (bw + bg) + bw / 2, by + 76)],
           label="credit: a job starts only if the output FIFO has room for its results", fs=8.8)
    d.edge(bl[1], bl[0], color=GRAY, lw=1.1, dashed=True, exit=(0.5, 0), entry=(0.5, 0),
           pts=[(bx + 1 * (bw + bg) + bw / 2, by - 13), (bx + bw / 2, by - 13)], label="back-pressure", fs=8.8, lcolor="#404040")
    d.text(0, by + 88, 640, 14, "Deployed DSP build: 5 + 14 + 14 + 7 multiplier DSPs + 3 requant DSPs = 43; "
           "0.975 samples per clock = 97.5 MBd at 200 MHz.", fs=8.8, color="#404040")
    d.save(HERE / "fig07_hardware.drawio", "hardware")

if __name__ == "__main__":
    for f in (HERE / "fig01_pipeline.drawio", HERE / "fig07_hardware.drawio"):
        if f.exists() and "--force" not in sys.argv:
            raise SystemExit(f"{f.name} exists (hand edits?); pass --force to overwrite")
    fig_pipeline()
    fig_hardware()
