"""One-off generator of the draw.io sources fig01_pipeline.drawio and fig07_hardware.drawio.

After generation the .drawio files are the sources of truth: open them in draw.io desktop to edit by
hand, then run report/diagrams/build_diagrams.py. Re-running this script overwrites hand edits
(it refuses unless --force is given).
Facts: equalizer/PROGRESS.md 5.5-5.6, equalizer/rtl/history/CHANGES.md, rtl/src/*.sv, rtl/gen/ours_bce_dfe_w8.
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


# ======================================================================= Figure 1: workflow
def fig_pipeline():
    d = Diagram()
    W = 640
    d.box(0, 0, W, 132, "", fc="#F6F9FD", ec=LIGHT, rounded=False, lw=1)
    d.box(0, 150, W, 150, "", fc="#FDF6F1", ec="#F2D3BF", rounded=False, lw=1)
    d.text(10, 4, 520, 16, "<b>Algorithm and learning</b>  (Python, PyTorch; package <i>eqsim</i>)", fs=9, color=BLUE)
    d.text(10, 279, 520, 16, "<b>Hardware</b>  (hand-written SystemVerilog, Vivado / xsim 2025.2, PYNQ-Z2)", fs=9, color=ORANGE)
    top = [("1  Channel models", "40 GBd PAM2 IM/DD,<br>31.5 km SSMF;<br>Proakis-B (paper)"),
           ("2  Baselines", "FIR, Volterra,<br>FFE + DFE, MLSE<br>(closed-form fits)"),
           ("3  CNN search", "135 topologies<br>&times; {MSE, cross-entropy}<br>3 seeds, fresh test"),
           ("4  CNN + DFE", "2 feedback taps,<br>9 channel conditions"),
           ("5  QAT + integer model", "3&ndash;8 bit LSQ,<br>BN folding, requant<br>(acc+b)&middot;M &gt;&gt; S")]
    bot = [("6  Export", "weights &rarr; params.mem,<br>package, test vectors"),
           ("7  Streaming RTL", "conv1d_stream &times; L,<br>DSP packing,<br>DFE look-ahead"),
           ("8  Verification", "unit + full model +<br>mutation +<br>gate-level netlists"),
           ("9  Implementation", "timing closure r1&ndash;r8c,<br>200 MHz, SAIF power"),
           ("10  PYNQ-Z2 system", "PS7 + AXI DMA,<br>two clock domains,<br>overlay .bit/.hwh")]
    w, h, gap, x0 = 112, 82, 20, 12
    tops, bots = [], []
    for i, (t, s) in enumerate(top):
        tops.append(d.box(x0 + i * (w + gap), 34, w, h, t, s, ec=BLUE, fs=8.5, sfs=7.2))
    for i, (t, s) in enumerate(bot):
        bots.append(d.box(x0 + i * (w + gap), 184, w, h, t, s, ec=ORANGE, tc=BROWN, fs=8.5, sfs=7.2))
    for a, b in zip(tops, tops[1:]):
        d.edge(a, b, color=BLUE, lw=1.4)
    for a, b in zip(bots, bots[1:]):
        d.edge(a, b, color=ORANGE, lw=1.4)
    # the integer golden model feeds the export and is the reference of every simulation
    d.edge(tops[4], bots[0], color=NAVY, lw=1.4, exit=(0.5, 1), entry=(0, 0.5),
           pts=[(x0 + 4 * (w + gap) + w / 2, 141), (5, 141), (5, 225)],
           label="integer golden model = exact RTL arithmetic: weights, biases, M, S, feedback taps", fs=7.5)
    d.edge(tops[4], bots[2], color=NAVY, lw=1.0, dashed=True, exit=(0.35, 1), entry=(0.5, 0),
           pts=[(x0 + 4 * (w + gap) + w * 0.35, 148), (x0 + 2 * (w + gap) + w / 2, 148)], end="block")
    d.text(x0 + 2 * (w + gap) + w / 2 + 6, 160, 200, 12, "expected outputs, bit-exact compare", fs=7, color=NAVY, italic=True)
    d.save(HERE / "fig01_pipeline.drawio", "pipeline")


# ======================================================================= Figure 7: hardware
def fig_hardware():
    d = Diagram()
    # ---------------------------------------------------------------- (a) system
    d.text(0, 0, 400, 14, "<b>(a) PYNQ-Z2 system (XC7Z020) with the deployed CNN + DFE equalizer</b>", fs=9, color=NAVY)
    d.box(0, 20, 118, 196, "", fc=PGRAY, ec=GRAY, lw=1.2)
    d.text(6, 24, 106, 14, "<b>Zynq PS7</b>", fs=8.5, color="#404040", align="center")
    d.text(6, 37, 106, 12, "ARM Cortex-A9, PYNQ", fs=7, color="#404040", align="center")
    gp0 = d.box(10, 52, 98, 34, "GP0 master", "control and weights", ec=BLUE, fs=8, sfs=7)
    hp0 = d.box(10, 112, 98, 34, "HP0 slave", "64-bit, DMA data", ec=ORANGE, tc=BROWN, fs=8, sfs=7)
    ddr = d.box(10, 160, 98, 34, "DDR3 512 MB", "frames in, symbols out", ec=GRAY, tc="#404040", fs=8, sfs=7)
    d.edge(ddr, hp0, color=GRAY, lw=1.0, start="block")
    d.text(4, 200, 110, 12, "FCLK0 100 MHz, FCLK1 200 MHz", fs=6.8, color="#404040", align="center")
    # 100 MHz domain
    d.box(130, 20, 150, 196, "", fc="#F6F9FD", ec=BLUE, dashed=True, lw=1.1)
    d.text(130, 24, 150, 14, "<b>FCLK0 = 100 MHz</b>", fs=8.5, color=BLUE, align="center")
    lite = d.box(142, 46, 126, 40, "AXI-Lite interconnect", "DMA and core registers,<br>clock crossing", fs=8, sfs=7)
    dma = d.box(142, 104, 126, 82, "AXI DMA", "simple mode, no SG<br>MM2S: memory &rarr; stream<br>S2MM: stream &rarr; memory<br>32-bit streams", fs=8, sfs=7)
    d.edge(gp0, lite, color=BLUE, lw=1.2, exit=(1, 0.5), entry=(0, 0.5))
    d.edge(hp0, dma, color=ORANGE, lw=1.4, start="block", exit=(1, 0.5), entry=(0, 0.3))
    d.edge(lite, dma, color=BLUE, lw=1.0, exit=(0.5, 1), entry=(0.5, 0))
    d.text(142, 199, 126, 12, "WNS +1.778 ns", fs=7.5, color=BLUE, bold=True, align="center")
    # 200 MHz domain
    d.box(292, 20, 348, 196, "", fc="#FDF6F1", ec=ORANGE, dashed=True, lw=1.1)
    d.text(292, 24, 348, 14, "<b>FCLK1 = 200 MHz</b>", fs=8.5, color=ORANGE, align="center")
    cin = d.box(300, 104, 54, 34, "clock + width", "32 &rarr; 8 bit", ec=ORANGE, tc=BROWN, fs=7, sfs=6.5)
    cout = d.box(300, 152, 54, 34, "clock + width", "16 &rarr; 32 bit", ec=ORANGE, tc=BROWN, fs=7, sfs=6.5)
    d.edge(dma, cin, color=NAVY, lw=1.3, exit=(1, 0.18), entry=(0, 0.5), label="MM2S", fs=7)
    d.edge(cout, dma, color=NAVY, lw=1.3, exit=(0, 0.5), entry=(1, 0.77), label="S2MM", fs=7)
    # equalizer core
    d.box(364, 42, 270, 152, "", fc="#FFFFFF", ec=NAVY, lw=1.6)
    d.text(370, 45, 260, 13, "<b>cnn_eq_top</b>: ours_bce_dfe_w8 (K = 9; 8-bit weights, activations, input)", fs=7.3, color=NAVY)
    pm = d.box(372, 62, 254, 20, "AXI-Lite registers + parameter memory (336 words, in flip-flops)", fc=PORANGE,
               ec=ORANGE, tc=BROWN, fs=7, bold=False)
    chain = [("layer 0", "1&rarr;3 ch<br>stride 4"), ("layer 1", "3&rarr;3 ch<br>stride 1"), ("layer 2", "3&rarr;3 ch<br>stride 1"),
             ("layer 3", "3&rarr;4 ch<br>stride 2"), ("serializer", "4 lanes &rarr;<br>1 symbol"), ("DFE", "2 taps,<br>look-ahead")]
    cw, cg, cx = 37, 6.6, 372
    cells = []
    for i, (t, s) in enumerate(chain):
        is_dfe = t == "DFE"
        cells.append(d.box(cx + i * (cw + cg), 100, cw, 42, t, s, fc=PGREEN if is_dfe else (PALE if i < 4 else "#FFFFFF"),
                           ec=GREEN if is_dfe else BLUE, tc=DGREEN if is_dfe else NAVY, fs=6.8, sfs=6.0))
    for a, b in zip(cells, cells[1:]):
        d.edge(a, b, lw=1.1)
    d.edge(cin, cells[0], lw=1.3, exit=(1, 0.5), entry=(0, 0.5))
    dx = cx + 5 * (cw + cg) + cw / 2
    d.edge(cells[-1], cout, lw=1.3, exit=(0.5, 1), entry=(1, 0.5), pts=[(dx, 169)])
    d.text(372, 146, 254, 12, "in: 8-bit samples, TLAST = frame end; 1 sample per clock", fs=6.4, color="#404040")
    d.text(372, 173, 254, 14, "out: 16-bit soft value <i>u</i>; decision = (<i>u</i> &gt; 0)", fs=6.4, color="#404040")
    for k, ex in ((0, 0.072), (1, 0.243), (2, 0.414), (3, 0.585), (5, 0.927)):
        d.edge(pm, cells[k], color=ORANGE, lw=0.8, exit=(ex, 1), entry=(0.5, 0))
    d.edge(lite, pm, color=BLUE, lw=1.0, exit=(1, 0.5), entry=(0, 0.5), pts=[(286, 66), (286, 72)])
    d.text(296, 199, 340, 12, "core WNS +0.160 ns; 5,421 LUT, 8,718 FF, 43 DSP, 0 BRAM", fs=7.5, color=ORANGE, bold=True, align="center")

    # ---------------------------------------------------------------- (b) one layer
    y0 = 236
    d.text(0, y0, 520, 14, "<b>(b) Inside one conv1d_stream layer</b> (every stage registered; one output channel or channel pair issued per cycle)",
           fs=9, color=NAVY)
    blocks = [("Window", "K &times; IC shift reg.,<br>zero pad, flush"), ("Job hold-back", "last job carries<br>the frame end"),
              ("Operand mux", "fold phase <i>f</i>:<br>taps <i>f</i>&middot;NM+<i>m</i>"),
              ("Multipliers", "NM = &lceil;IC&middot;K/FOLD&rceil;<br>LUT or DSP48E1;<br>PACK: 2 ch / DSP"),
              ("Adder trees", "growing width;<br>+ borrow count"), ("Fold accum.", "sum FOLD<br>partials"),
              ("Requant", "pair serializer,<br>(acc+b)&middot;M, round,<br>&gt;&gt;&gt; S, clamp"),
              ("Collector", "OC channels &rarr;<br>output FIFO (16)")]
    bw, bg, bx, by = 70, 11.4, 0, y0 + 40
    bl = []
    for i, (t, s) in enumerate(blocks):
        bl.append(d.box(bx + i * (bw + bg), by, bw, 54, t, s, fc=PALE if t == "Multipliers" else "#FFFFFF", fs=7.8, sfs=6.6))
    for a, b in zip(bl, bl[1:]):
        d.edge(a, b, lw=1.1)
    # credit loop (below) and back-pressure (above)
    d.edge(bl[7], bl[1], color="#C00000", lw=1.0, dashed=True, exit=(0.5, 1), entry=(0.5, 1),
           pts=[(bx + 7 * (bw + bg) + bw / 2, by + 74), (bx + 1 * (bw + bg) + bw / 2, by + 74)],
           label="credit: a job starts only if the output FIFO has room for it (OUT_DEPTH &minus; occupancy &minus; in flight &gt; 0)", fs=7)
    d.edge(bl[1], bl[0], color=GRAY, lw=1.0, dashed=True, exit=(0.5, 0), entry=(0.5, 0),
           pts=[(bx + 1 * (bw + bg) + bw / 2, by - 12), (bx + bw / 2, by - 12)], label="back-pressure (s_ready)", fs=7, lcolor="#404040")
    d.text(0, by + 86, 640, 14, "Deployed DSP build: layers 0&ndash;2 PACK + FOLD 2 (5 / 14 / 14 DSP), layer 3 PACK + FOLD 4 (7 DSP), + 3 requant DSP = 43; "
           "0.975 samples / clock = 97.5 MBd per instance at 200 MHz.", fs=7, color="#404040")
    d.save(HERE / "fig07_hardware.drawio", "hardware")


if __name__ == "__main__":
    for f in (HERE / "fig01_pipeline.drawio", HERE / "fig07_hardware.drawio"):
        if f.exists() and "--force" not in sys.argv:
            raise SystemExit(f"{f.name} exists (hand edits?); pass --force to overwrite")
    fig_pipeline()
    fig_hardware()
