r"""Build the MLEE project report (report/MLEE_Report.docx) on the course template.

Run from Project/:  D:\venvs\mlee-eq\Scripts\python.exe report\build_report.py
Figures: report/figures (make_figures.py for data plots, diagrams/build_diagrams.py for diagrams).
Numbers: the result files and Vivado reports under equalizer/ (the long tables are read directly below).
"""
import json
from collections import defaultdict
from pathlib import Path

import docx
from docx.shared import Cm

from docxlib import Report, _run

ROOT = Path(__file__).resolve().parents[1]
EQ = ROOT / "equalizer"
RES = EQ / "results"
TPL = ROOT / "Project submission templates" / "Project submission templates"
OUT = Path(__file__).resolve().parent / "MLEE_Report.docx"

TITLE = "Low-Complexity Neural Network Equalization for Optical Fibre Communication on FPGA"
SHORT = "Low-Complexity NN Equalization on FPGA"


def e(x, d=1):
    """1.23e-04 -> 1.2 x 10^-4 markup."""
    if x == 0:
        return "0 errors"
    m, ex = f"{x:.{d}e}".split("e")
    return f"{m}×10^{{{int(ex)}}}"


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


# =============================================================================== bibliography (IEEE)
BIB = {
    "khan19": 'F. N. Khan, Q. Fan, C. Lu, and A. P. T. Lau, "An optical communication\'s perspective on machine learning and its applications," *J. Lightw. Technol.*, vol. 37, no. 2, pp. 493–516, 2019.',
    "schaedler19": 'M. Schaedler, C. Bluemm, M. Kuschnerov, F. Pittalà, S. Calabrò, and S. Pachnicke, "Deep neural network equalization for optical short reach communication," *Applied Sciences*, vol. 9, no. 21, 2019.',
    "meslener84": 'G. J. Meslener, "Chromatic dispersion induced distortion of modulated monochromatic light employing direct detection," *IEEE J. Quantum Electron.*, vol. 20, no. 10, pp. 1208–1216, Oct. 1984, doi: 10.1109/JQE.1984.1072286.',
    "eriksson17": 'T. A. Eriksson, H. Bülow, and A. Leven, "Applying neural networks in optical communication systems: Possible pitfalls," *IEEE Photon. Technol. Lett.*, vol. 29, no. 23, pp. 2091–2094, 2017, doi: 10.1109/LPT.2017.2755663.',
    "kaneda22": 'N. Kaneda, C.-Y. Chuang, Z. Zhu, A. Mahadevan, B. Farah, K. Bergman, D. Van Veen, and V. Houtsma, "Fixed-point analysis and FPGA implementation of deep neural network based equalizers for high-speed PON," *J. Lightw. Technol.*, vol. 40, no. 7, pp. 1972–1980, 2022.',
    "li21": 'M. Li, W. Zhang, Q. Chen, and Z. He, "High-throughput hardware deployment of pruned neural network based nonlinear equalization for 100-Gbps short-reach optical interconnect," *Opt. Lett.*, vol. 46, no. 19, pp. 4980–4983, 2021.',
    "freire23": 'P. J. Freire, S. Srivallapanondh, M. Anderson, B. Spinnler, T. Bex, T. A. Eriksson, A. Napoli, W. Schairer, N. Costa, M. Blott, S. K. Turitsyn, and J. E. Prilepsky, "Implementing neural network-based equalizers in a coherent optical transmission system using field-programmable gate arrays," *J. Lightw. Technol.*, vol. 41, no. 12, pp. 3797–3815, 2023, doi: 10.1109/JLT.2023.3272011.',
    "ney24": 'J. Ney, C. Füllner, V. Lauinger, L. Schmalen, S. Randel, and N. Wehn, "CNN-based equalization for communications: Achieving gigabit throughput with a flexible FPGA hardware architecture," arXiv:2405.02323, 2024.',
    "ney23samos": 'J. Ney, C. Füllner, V. Lauinger, L. Schmalen, S. Randel, and N. Wehn, "From algorithm to implementation: Enabling high-throughput CNN-based equalization on FPGA for optical communications," in *Embedded Computer Systems: Architectures, Modeling, and Simulation (SAMOS)*. Cham, Switzerland: Springer, 2023, pp. 158–173.',
    "ney23eucnc": 'J. Ney, V. Lauinger, L. Schmalen, and N. Wehn, "Unsupervised ANN-based equalizer and its trainable FPGA implementation," in *Proc. EuCNC/6G Summit*, 2023, pp. 60–65, doi: 10.1109/EuCNC/6GSummit58263.2023.10188269.',
    "ney24demo": 'J. Ney, P. Matalla, V. Lauinger, L. Schmalen, S. Randel, and N. Wehn, "Real-time FPGA demonstrator of ANN-based equalization for optical communications," arXiv:2402.15288, 2024.',
    "fischer25": 'R. Fischer, P. Matalla, S. Randel, and L. Schmalen, "Non-linear equalization in 112 Gb/s PONs using Kolmogorov-Arnold networks," in *Proc. Optical Fiber Communication Conf. (OFC)*, 2025, arXiv:2411.19631.',
    "proakis08": 'J. G. Proakis and M. Salehi, *Digital Communications*, 5th ed. New York, NY, USA: McGraw-Hill, 2008.',
    "esser20": 'S. K. Esser, J. L. McKinstry, D. Bablani, R. Appuswamy, and D. S. Modha, "Learned step size quantization," in *Proc. Int. Conf. Learning Representations (ICLR)*, 2020.',
    "jacob18": 'B. Jacob, S. Kligys, B. Chen, M. Zhu, M. Tang, A. Howard, H. Adam, and D. Kalenichenko, "Quantization and training of neural networks for efficient integer-arithmetic-only inference," in *Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition (CVPR)*, 2018, pp. 2704–2713.',
    "mann47": 'H. B. Mann and D. R. Whitney, "On a test of whether one of two random variables is stochastically larger than the other," *Ann. Math. Statist.*, vol. 18, no. 1, pp. 50–60, 1947.',
    "kuon10": 'I. Kuon and J. Rose, *Quantifying and Exploring the Gap Between FPGAs and ASICs*. New York, NY, USA: Springer, 2010.',
    "ug479": 'AMD (Xilinx), "7 Series DSP48E1 Slice User Guide," UG479.',
    "ug907": 'AMD (Xilinx), "Vivado Design Suite User Guide: Power Analysis and Optimization," UG907.',
    "pynq": 'AMD (Xilinx), "PYNQ: Python productivity for Zynq," [Online]. Available: http://www.pynq.io',
}


# =============================================================================== data-driven tables
def stress_rows():
    rows = jl(RES / "dfe_stress" / "results.jsonl")
    models = ["FFE57", "FFE121", "FFE25+DFE2", "FFE57+DFE2", "CNN", "CNN+DFE2"]
    conds = [(20, 20.0), (14, 31.5), (16, 31.5), (18, 31.5), (20, 31.5), (22, 31.5), (24, 31.5), (20, 40.0), (20, 50.0)]
    out, best_cells = [], []
    for s, L in conds:
        r = [f"{L:g} km, {s} dB"]
        vals = []
        for m in models:
            v = sorted(x["ber"] for x in rows if x["snr"] == s and x["L"] == L and x["model"] == m)
            vals.append(v[0])
            txt = e(v[0]) if v[0] > 0 else "0 errors"
            if m.startswith("CNN") and v[0] > 0:
                txt += f"\n({e(sorted(v)[len(v) // 2])})"
            r.append(txt)
        best = min(range(len(vals)), key=lambda j: vals[j])
        r[1 + best] = "\n".join(f"**{line}**" for line in r[1 + best].split("\n"))   # bold per line (cells split at \n)
        out.append(r)
    return out


def confirm_rows():
    conf = jl(RES / "imdd_dse" / "confirm.jsonl")
    d = defaultdict(list)
    for c in conf:
        d[(c["vp"], c["layers"], c["kernel"], c["channels"], c["loss"])].append(c["ber"])
    out = []
    names = {(8, 3, 9, 5): "Paper's CNN ($V_p$=8, L=3, K=9, C=5)", (4, 3, 15, 3): "$V_p$=4, L=3, K=15, C=3",
             (4, 4, 9, 3): "**Ours** ($V_p$=4, L=4, K=9, C=3)"}
    macs = {(8, 3, 9, 5): "112.5", (4, 3, 15, 3): "135", (4, 4, 9, 3): "121.5"}
    for cfg in ((8, 3, 9, 5), (4, 3, 15, 3), (4, 4, 9, 3)):
        for loss, lab in (("mse", "MSE"), ("bce", "cross-entropy")):
            v = sorted(d[cfg + (loss,)])
            out.append([names[cfg], macs[cfg], lab, e(v[0], 2), e(v[1], 2), e(v[2], 2)])
    return out


def quant_rows():
    q = json.load(open(RES / "quant" / "summary.json"))
    names = [("paper_mse", "Paper's CNN, MSE (paper recipe)"), ("paper_bce", "Paper's CNN, cross-entropy"),
             ("ours_mse", "Ours, MSE"), ("ours_bce", "Ours, cross-entropy")]
    out = []
    for key, lab in names:
        rs = {r["bits"]: r for r in q if r["name"] == key}
        fp = next(iter(rs.values()))["fp32_ber"]
        out.append([lab, e(fp, 1)] + [e(rs[b]["qat_ber"], 1) if b in rs else "–" for b in (8, 7, 6, 5, 4, 3)])
    dfe = {b: json.load(open(RES / "quant" / f"ours_bce_dfe_w{b}" / "metrics.json")) for b in (6, 7, 8)}
    out.append(["**Ours + DFE2 (deployed: W8)**", "3.5×10^{-6} †"] +
                [f"**{e(dfe[b]["qat_ber"], 1)}**" if b in dfe else "–" for b in (8, 7, 6, 5, 4, 3)])
    return out


# =============================================================================== build
def build(defer=None):
    R = Report(TPL / "MLEE_Project_Report_Template.docx", ROOT / "report" / "figures")

    # ---------------------------------------------------------------- title block, header, footer
    logo_tbl, _, _, _, title_p, info_tbl = R.title_block
    cell_p = logo_tbl.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")
    for r in list(cell_p):
        if r.tag.endswith("}r"):
            cell_p.remove(r)
    docx.text.paragraph.Paragraph(cell_p, R.doc._body).add_run().add_picture(str(TPL / "bits_logo.png"), width=Cm(3.4))
    # the logo needs no dashed placeholder border
    for b in logo_tbl.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tcBorders"):
        for side in b:
            side.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "nil")
    t = title_p.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
    t.text = TITLE
    info = docx.table.Table(info_tbl, R.doc._body)
    values = ["MLEE (EEE G513): Machine Learning for Electronics Engineers, Semester I, 2026–27",
              "[Team ID]",
              "[Name 1 (ID)], [Name 2 (ID)], [Name 3 (ID)]",
              "Dr. Ritesh Vyas",
              "20 November 2026",
              "https://github.com/JSpectre20/mlee-cnn-equalizer (private; access on request)"]
    for row, v in zip(info.rows, values):
        tt = row.cells[1].paragraphs[0]._p.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        tt[0].text = v
        for extra in tt[1:]:
            extra.text = ""
    foot = R.doc.sections[0].footer.paragraphs[0]
    foot.runs[0].text = f"{SHORT} | Team [ID]"
    sp = docx.oxml.OxmlElement("w:p"); R._add(sp)

    # ---------------------------------------------------------------- abstract
    R.abstract_heading()
    R.para(
        "Short-reach optical links with intensity modulation and direct detection (IM/DD) suffer from chromatic-dispersion "
        "power fading, which leaves spectral nulls that a linear equalizer cannot fill. We reproduce, without access to its "
        "code or data, the CNN equalizer and FPGA architecture of Ney et al. for a 40 GBd, 31.5 km PAM2 link, and improve it. "
        "A decision-aligned cross-entropy loss and a search over 135 topologies give a CNN with 16× lower bit error rate "
        "(BER) than the paper's selected CNN at a similar cost (121.5 vs 112.5 multiplications per symbol). Adding two "
        "decision-feedback taps and quantizing to 8 bits gives an integer BER of 5.0×10^{-7}, about 1000× below the "
        "paper's CNN at the same bit width. Both models run on our hand-written streaming SystemVerilog engine: on a PYNQ-Z2 "
        "(XC7Z020) the deployed CNN+DFE closes timing at 200 MHz in the full system, uses 23 % fewer LUTs than the paper's CNN "
        "on the same engine, and every routed netlist is bit-exact against the golden model. A 6-bit variant reaches 23× "
        "lower BER with 44 % fewer LUTs and 14 % less dynamic power.")
    R.keywords("IM/DD optical communication, neural network equalizer, decision feedback, quantization-aware training, FPGA, "
               "SystemVerilog, PYNQ-Z2")

    # ---------------------------------------------------------------- 1 introduction
    R.h1("1. Introduction")
    R.para(
        "Data-centre interconnects and access networks carry most of their traffic over short optical links that use "
        "intensity modulation and direct detection (IM/DD), because one modulator and one photodiode keep cost and power "
        "low [@khan19, @schaedler19]. The price is that a photodiode measures only optical power. Chromatic dispersion (CD) "
        "acts linearly on the optical field, but after square-law detection it becomes a nonlinear impairment that produces "
        "frequency-selective *power fading* [@meslener84]. On a 40 GBd link over 31.5 km of standard single-mode fibre the "
        "first fading null sits at 11.1 GHz, well inside the signal band, so a linear feed-forward equalizer is left with an "
        "error floor.")
    R.para(
        "Neural-network (NN) equalizers recover part of this loss [@schaedler19, @eriksson17], and FPGA implementations show "
        "that they can run at line rate [@kaneda22, @li21, @freire23]. Ney et al. [@ney24] proposed a convolutional (CNN) "
        "equalizer template together with a flexible FPGA architecture generated with high-level synthesis (HLS), reached "
        "40 GBd on a large UltraScale+ device, and showed that the CNN beats a linear FIR equalizer of equal complexity on "
        "a measured 31.5 km link and on the Proakis-B channel. Neither their code nor their data are public.")
    R.para(
        "**Problem statement.** Given the photodiode signal sampled at $N_{os}=2$ samples per symbol, recover the "
        "transmitted PAM2 bits with the lowest bit error rate (BER) under the paper's complexity budget of 147 "
        "multiplications per symbol, and implement the equalizer as a streaming circuit that is bit-exact to its trained "
        "model and sustains one sample per clock at 200 MHz on the XC7Z020 of a PYNQ-Z2 board.")
    R.para("**Objectives.** The project sets out to:", after=60)
    R.bullets([
        "reproduce the base paper from scratch: an IM/DD link simulator, the paper's CNN template, and strong baselines "
        "(FIR, Volterra, feed-forward plus decision-feedback equalization, and maximum-likelihood sequence estimation);",
        "improve the equalizer at equal cost, with a decision-aligned loss, a topology search and a CNN with decision feedback;",
        "quantize the models to integer arithmetic with a bit-exact golden model;",
        "design a hand-written SystemVerilog streaming engine for the PYNQ-Z2, close timing at 200 MHz and verify it down to "
        "the routed netlist;",
        "compare honestly against the paper's CNN on the same engine, chip and clock, with power from simulated switching "
        "activity rather than a vectorless estimate."])
    R.para(
        "**Contributions.** The CNN we select (cross-entropy loss, four layers) reaches 16× lower BER than the paper's CNN "
        "at a similar multiplication count. A CNN with two decision-feedback taps reaches 5.0×10^{-7} at 8 bits, against "
        "4.96×10^{-4} for the paper's CNN quantized the same way. Our engine packs two output channels into each DSP "
        "slice and resolves the feedback loop with a look-ahead, and the deployed design meets 200 MHz in the PYNQ-Z2 system. "
        "Along the way we found that the paper's multiplication count is low by a factor of $N_{os}$, and that on our simulated "
        "link a 59-multiplication FFE with two feedback taps beats every CNN at the paper's operating point. Both findings "
        "change how the CNN's advantage should be read.", before=60)
    R.para(
        "Section 2 gives the theory and related work, Section 3 the simulator, models, quantization and hardware, Section 4 "
        "the results, and Section 5 concludes. Annexes B–D hold the full result tables, the RTL revision history and the "
        "reproduction instructions.")

    # ---------------------------------------------------------------- 2 background
    R.h1("2. Background")
    R.h2("2.1 Theoretical Preliminaries")
    R.para(
        "**Power fading.** Fibre dispersion multiplies the optical field spectrum by an all-pass phase, where $\\beta_2$ is the "
        "group-velocity dispersion and $L$ the fibre length:", keep_next=True)
    R.equation(r"H_{\mathrm{CD}}(\omega)=\exp\left(j\,\frac{\beta_2 L\,\omega^2}{2}\right)", "cd")
    R.para(
        "For a small intensity modulation, the photocurrent after square-law detection sees the two sidebands of each "
        "frequency rotate in opposite directions, so they partly cancel [@meslener84]:", keep_next=True)
    R.equation(r"\left|H_{\mathrm{IM}}(f)\right|=\left|\cos\left(2\pi^2\beta_2 L f^2\right)\right|,\qquad f_k=\sqrt{\frac{2k+1}{4\pi\left|\beta_2\right| L}}", "fading")
    R.para(
        "With $D=16$ ps/(nm·km) at 1550 nm ($\\beta_2\\approx-20.4$ ps²/km) and $L=31.5$ km, the nulls fall at "
        "$f_0=11.1$ GHz and $f_1=19.3$ GHz, both inside the 20 GHz Nyquist band of a 40 GBd signal ({fig:link}b). A "
        "linear equalizer cannot restore a frequency at which the channel has no gain. Decision feedback can, because it "
        "rebuilds the interference from past decisions instead of inverting the channel [@proakis08].")
    R.para(
        "**CNN equalizer.** The template of [@ney24] maps a frame of received samples $r$ to one real output $z[n]$ per "
        "symbol with $L$ one-dimensional convolutions of kernel $K$ and $C$ channels. The first layer strides by $V_p$ "
        "samples, the last by $N_{os}$ and has $V_p$ output channels, so each output position yields $V_p$ symbols. The "
        "decision is $\\hat b[n]=[z[n]>0]$. The exact number of multiplications per symbol is", keep_next=True)
    R.equation(r"M=\frac{K C N_{os}}{V_p}+(L-2)\,\frac{K C^2 N_{os}}{V_p}+K C", "macs")
    R.para(
        "This gives 112.5 for the paper's CNN ($V_p=8$, $L=3$, $K=9$, $C=5$) and 121.5 for ours ($V_p=4$, $L=4$, $K=9$, $C=3$). "
        "The formula printed in [@ney24] equals {eq:macs} divided by $N_{os}$, so it counts multiplications per input sample.")
    R.para(
        "**Training objective.** The paper trains with the mean squared error to the symbol $x=\\pm1$. Since only the sign "
        "of $z$ matters for the BER, we also train with the binary cross-entropy on the logit $z$, which for $x=2b-1$ reads", keep_next=True)
    R.equation(r"\mathcal{L}_{\mathrm{MSE}}=(z-x)^2,\qquad \mathcal{L}_{\mathrm{CE}}=\log\left(1+e^{-x z}\right)", "loss")
    R.para(
        "MSE also penalises correct decisions that lie far from ±1, which spends model capacity on reproducing amplitudes. "
        "Cross-entropy stops pushing once a decision is confidently right and concentrates on the symbols near the threshold.")
    R.para(
        "**Decision feedback.** A CNN with $N_{fb}$ feedback taps adds a linear term in its own past decisions $d=\\pm1$; "
        "the taps $f_{v,k}$ may differ per output lane $v=n \\bmod V_p$:", keep_next=True)
    R.equation(r"u[n]=z[n]+\sum_{k=1}^{N_{fb}} f_{v,k}\, d[n-k],\qquad d[n]=\mathrm{sgn}\left(u[n]\right)", "dfe")
    R.para(
        "**Integer arithmetic.** For hardware, every layer is computed in integers [@jacob18]. A hidden layer rescales its "
        "accumulator with a per-channel 16-bit multiplier $M$ and shift $S$, rounds, and clips to the activation range:", keep_next=True)
    R.equation(r"a'=\mathrm{clamp}\left(\left\lfloor\frac{(\mathrm{acc}+b)\,M+2^{S-1}}{2^{S}}\right\rfloor,\;0,\;2^{B_A}-1\right)", "requant")

    R.h2("2.2 Related Work")
    R.para(
        "Machine learning for optical links is surveyed in [@khan19]. Deep NN equalizers for short-reach IM/DD were studied in "
        "[@schaedler19], and [@eriksson17] warned against pitfalls in evaluating them, such as networks that learn the "
        "pseudo-random test sequence. FPGA implementations exist for passive optical networks with fixed-point analysis "
        "[@kaneda22], for pruned networks at 100 Gb/s [@li21], and for coherent links [@freire23]. FPGAs trade efficiency "
        "against an ASIC for flexibility [@kuon10]. The base paper [@ney24] belongs to a line of work by the same groups: "
        "an earlier version of the CNN architecture [@ney23samos], an unsupervised equalizer trained on the FPGA "
        "[@ney23eucnc], and a real-time 30 GBd demonstrator [@ney24demo]. More recently, Kolmogorov-Arnold networks were "
        "proposed as equalizers for 112 Gb/s PAM4 PON and evaluated on transmission experiments, with complexity counted but no hardware implementation [@fischer25]. For the baselines we rely on "
        "classical results: the Viterbi algorithm is the optimal sequence detector for a known linear channel, and "
        "decision feedback cancels post-cursor interference without amplifying noise [@proakis08]. For quantization we use "
        "learned step sizes [@esser20] and integer-only inference [@jacob18].")
    R.h2("2.3 Gap and Motivation")
    R.para("Reading [@ney24] closely leaves several open questions that motivate this project:", after=60)
    R.bullets([
        "**Loss and topology.** The CNN is trained with MSE, although the target is a hard decision. It is not known how much "
        "a decision-aligned loss changes the best topology under the same budget.",
        "**Baselines.** The paper compares only with a FIR equalizer. No decision-feedback or sequence-detection baseline is "
        "given, although power fading is the textbook case for decision feedback.",
        "**Complexity accounting.** The printed multiplication count is per input sample, which halves the cost of the CNN "
        "relative to the budget.",
        "**Hardware evidence.** The design is generated with HLS and its power is a vectorless estimate. The cost of a "
        "hand-written datapath, and power from real switching activity, are not reported.",
        "**Reproducibility.** Neither code nor data are public, so every number has to be rebuilt from first principles."])

    # ---------------------------------------------------------------- 3 methodology
    R.h1("3. Methodology")
    R.h2("3.1 Overall Approach")
    R.para(
        "{fig:pipeline} shows the workflow. A Python package (*eqsim*) simulates the channels, fits the baselines, trains and "
        "searches the CNNs, adds decision feedback, and quantizes the chosen models. Its integer golden model reproduces the "
        "hardware arithmetic exactly, and it bridges the two halves of the work: it exports the parameters to the RTL and "
        "supplies the expected outputs that every simulation, down to the routed netlist, must match bit for bit.")
    R.para(
        "Three rules keep the comparison honest. First, every equalizer, the paper's CNN included, is trained and "
        "tested on the same fixed datasets. Second, model selection uses one test set and every reported number a second, "
        "fresh one that no selection step has seen. Third, the hardware is judged on the same engine, device and clock for "
        "both CNNs, with power from simulated switching activity. FP32 models, datasets and hardware builds are frozen "
        "read-only with checksums, so every number in this report can be regenerated (Annex D).")
    R.figure("fig01_pipeline", "pipeline",
             "Project workflow. The integer golden model links learning and hardware: it exports the parameters and is the "
             "bit-exact reference for every simulation.")

    R.h2("3.2 Data and Preprocessing")
    R.figure("fig02_link", "link",
             "(a) Simulated IM/DD link. (b) Small-signal response of the simulated link against the theory of {eq:fading}; the first "
             "two fading nulls lie inside the signal band. (c, d) Eye diagrams back-to-back and after 31.5 km at 30 dB SNR.")
    R.para(
        "No measured data are available, so all data come from a physical link simulator ({fig:link}a). A PRBS-driven PAM2 "
        "signal at 40 GBd is shaped by a root-raised-cosine filter (roll-off 0.2) at 8 samples per symbol. It drives a "
        "Mach-Zehnder modulator biased at quadrature (modulation index 0.8) and propagates over 31.5 km of SSMF "
        "as in {eq:cd}. Detection is square-law with a 4th-order Bessel response of 40 GHz, followed by white noise at a given "
        "electrical SNR (24 dB in the main study). The signal is then resampled to $N_{os}=2$, AC-coupled and normalised to "
        "unit variance. The simulated fading response matches {eq:fading} to within the estimator noise, nulls included "
        "({fig:link}b). The eye closes completely after 31.5 km ({fig:link}d).")
    R.para(
        "Simulating a batch takes about 0.4 s, so the IM/DD data are fixed datasets built from independent 200,000-symbol "
        "chunks with 64 guard symbols each: 2M training symbols (seed 1), 2M test symbols used for model selection (seed 2), "
        "and a *fresh* 4M-symbol test set (seed 3) used only for the final numbers, so that selection bias does not inflate "
        "them. A stress test generates nine further conditions (20–50 km, 14–24 dB) with 1M training and 2M test symbols each. "
        "The Proakis-B channel, $h=[0.407, 0.815, 0.407]$ at 20 dB as in [@ney24], is simulated on the fly (raised-cosine "
        "roll-off 0.25, 10^{6} test symbols). All datasets and FP32 models are frozen read-only with SHA-256 manifests.")

    R.h2("3.3 Model, Algorithm and Circuit Design")
    R.lead("Baselines.",
           "To give the CNN strong opponents, FIR and Volterra equalizers are fitted in closed form, by least squares or by "
           "logistic regression started from the least-squares solution. A feed-forward equalizer with $B$ feedback taps "
           "(FFE+DFE) is fitted in closed form and always evaluated on its own decisions, so error propagation is included. "
           "On Proakis-B, where the channel is known and linear, a 4-state Viterbi detector gives the optimum.")
    R.lead("Topology search.",
           "We train the CNN template on a grid of $V_p\\in\\{1,2,4,8,16\\}$, $L\\in\\{3,4,5\\}$, $K\\in\\{9,15,21\\}$ and "
           "$C\\in\\{3,4,5\\}$ (135 topologies), each with MSE and with cross-entropy. One seed screens all 270 runs, three "
           "seeds refine the Pareto candidates, and the three most promising configurations within the budget are confirmed "
           "on the fresh test set.")
    R.lead("CNN with decision feedback.",
           "The selected CNN gets two feedback taps per output lane, as in {eq:dfe}. It is trained with teacher forcing, i.e. the "
           "true past symbols are fed back during training, and is always evaluated on its own decisions. The history is "
           "reset to $d=-1$ at every frame start, exactly as the hardware does.")
    R.lead("Quantization.",
           "Batch normalisation is folded into the convolutions. Weights (per-channel, symmetric), activations and the input "
           "are then fake-quantized with learned step sizes [@esser20] at the same bit width, and fine-tuned from the best "
           "FP32 seed. The export step converts every scale into the integer multiplier and shift of {eq:requant}, rounds "
           "the biases and feedback taps, and checks the worst-case accumulator width. The resulting integer model is the "
           "golden reference. Its decisions agree with the fake-quantized network on more than 99.9 % of symbols, and the "
           "rest are float32 rounding ties.")
    R.lead("Streaming engine.",
           "The hardware is written by hand in SystemVerilog rather than generated with HLS. This gives direct control of bit "
           "widths, pipelining and DSP mapping, and a guaranteed rate of one sample per clock. To keep the comparison fair, "
           "the paper's CNN and ours go through the *same* engine. Each layer is a `conv1d_stream` instance ({fig:hw}b). A "
           "K × IC window shift register applies the zero padding of a per-frame convolution. Every stride-th sample, it "
           "captures the window as a job, and the newest job is held back so that the frame's last job can carry the "
           "end-of-frame flag. An engine then issues one output channel (or channel pair) per cycle through the multipliers, "
           "registered adder trees, a fold accumulator and the requantization pipeline. A credit counter starts a job only "
           "if the output FIFO is guaranteed to have room, so the datapath never stalls internally.")
    R.lead("Sharing and packing.",
           "Because layer $l$ receives a new job only every $\\prod_{i\\le l} s_i$ cycles, a layer can share each multiplier "
           "over FOLD cycles ($\\lceil IC\\cdot K/\\mathrm{FOLD}\\rceil$ multipliers). In DSP builds, two output channels share "
           "one DSP48E1 [@ug479]: the 25-bit pre-adder forms $w_{2g}\\,2^{PW}+w_{2g+1}$, and one multiplication by the "
           "activation yields both products in separate bit fields ({fig:packdfe}a). The high field reads one too low whenever "
           "the low product is negative; a small tree counts these borrows and corrects each sum once, so both channels stay "
           "exact.")
    R.lead("Decision feedback in one clock.",
           "A direct DFE would put an adder and a comparator inside the one-cycle decision loop. Our `dfe_stream` instead "
           "precomputes, one stage early, the four candidates $z\\pm f_1\\pm f_2$ and their signs ({fig:packdfe}b). The loop "
           "is then only a 4:1 multiplexer of one-bit flags selected by the 2-bit decision history, which is what lets the "
           "DFE run at 200 MHz.")
    R.lead("System integration.",
           "Weights, biases, requantization constants and feedback taps are written at run time over AXI-Lite into a "
           "336-word parameter memory held in flip-flops. A layer reads up to IC × K weights in the same cycle, "
           "which a dual-port BRAM cannot deliver, so the core uses no block RAM. Under PYNQ [@pynq], the PS7 moves frames with an AXI DMA "
           "({fig:hw}a). A single 200 MHz clock failed timing only inside the DMA and interconnect IP, so the system uses two "
           "clock domains: FCLK0 at 100 MHz for the DMA, which moves 32-bit words over the 64-bit HP0 port, and FCLK1 at "
           "200 MHz for the equalizer.")
    R.figure("fig07_hardware", "hw",
             "(a) PYNQ-Z2 system with the deployed CNN+DFE equalizer: the DMA runs at 100 MHz and the equalizer at 200 MHz, "
             "joined by stream clock and width converters. (b) Pipeline of one convolution layer.")
    R.figure("fig09_pack_dfe", "packdfe",
             "(a) Two output channels per DSP48E1 through the pre-adder, with borrow correction. (b) Look-ahead decision "
             "feedback: the feedback loop is a 4:1 multiplexer of one-bit flags.")

    R.h2("3.4 Implementation and Experimental Setup")
    R.para("{tab:setup} lists the settings. Software runs on a 6-core laptop CPU (Python 3.14, PyTorch 2.14), and the hardware "
           "flow is AMD Vivado 2025.2 with the xsim simulator.")
    R.table("setup", "Key settings and hyperparameters.", ["Item", "Setting"], [
        ["IM/DD link", "40 GBd PAM2; RRC roll-off 0.2; MZM at quadrature, m = 0.8; 31.5 km SSMF, D = 16 ps/(nm·km) at 1550 nm; "
                       "square-law PD with 4th-order Bessel 40 GHz; AWGN, 24 dB electrical SNR; $N_{os}=2$"],
        ["Proakis-B", "h = [0.407, 0.815, 0.407], raised cosine 0.25, 20 dB, 10^{6} test symbols"],
        ["Datasets", "IM/DD train 2M / test 2M / fresh test 4M symbols (seeds 1 / 2 / 3); stress test 1M / 2M per condition"],
        ["CNN search", "$V_p$ ∈ {1, 2, 4, 8, 16}, L ∈ {3, 4, 5}, K ∈ {9, 15, 21}, C ∈ {3, 4, 5}; MSE and cross-entropy; "
                       "1 seed screen, 3 seeds refine, fresh-test confirmation"],
        ["CNN training", "Adam, learning rate 10^{-3}, 10,000 iterations, batch 32 × 512 symbols, 32 edge symbols cropped, BN + ReLU"],
        ["Baselines", "FIR / Volterra: least squares or logistic regression (L-BFGS, L2 10^{-4}); FFE+DFE: least squares, own "
                      "decisions; 4-state Viterbi MLSE"],
        ["CNN + DFE", "2 taps per lane; teacher forcing during training; own decisions at test; d = −1 at frame start"],
        ["QAT", "BN folding; LSQ, round half up; per-channel symmetric weights; W = A = input bits, 3–8; Adam 2×10^{-4}, "
                "4000 iterations from the best FP32 seed; M 16 bit, S ≤ 40"],
        ["Hardware flow", "XC7Z020-1CLG400 (PYNQ-Z2); out-of-context place and route at a 5 ns target with timing directives; "
                          "full system with PS7 + AXI DMA; power from SAIF activity of post-route netlist simulation at 200 MHz"],
    ], widths=[1900, 7126], align=["left", "left"], first_col_bold=True)
    R.para(
        "**Verification.** Every hardware result in Section 4 rests on the chain of checks in {tab:verif}. The mutation tests "
        "show that the testbenches would catch the subtle bugs this design is prone to. The gate-level runs show that "
        "synthesis and the timing optimisations preserved the arithmetic.")
    R.table("verif", "Verification matrix.", ["Level", "Scope", "Result"], [
        ["Integer golden model", "Exact RTL arithmetic (requantization, saturation, DFE); 11 unit tests", "pass"],
        ["Layer testbench", "16 `conv1d_stream` configurations (K 1–15, stride 1–8, FOLD 1–3, PACK, signed and unsigned "
                            "input), 80 random frames of 1–120 positions, random gaps and back-pressure up to 60 %", "16/16 bit-exact"],
        ["Full-model testbench", "All exported models (paper W8, ours W6 / W8 / W8+DFE; 1024- and 64-symbol frames) × LUT / DSP "
                                 "builds × 0 / 30 % stalls; TLAST, frame counters, throughput", "all bit-exact"],
        ["Mutation tests", "Six broken copies: owed counter ignores the stride phase, fold accumulator, no borrow correction, "
                           "lane 1 dropped, no DFE history reset, swapped DFE taps", "6/6 caught"],
        ["Gate level", "The six final routed designs in post-route functional simulation at 200 MHz (also the SAIF source)",
         "6/6 bit-exact (512/512)"],
    ], widths=[1850, 5476, 1700], align=["left", "left", "center"], first_col_bold=True)

    R.h2("3.5 Evaluation Metrics")
    R.bullets([
        "**BER** of hard decisions, with a 95 % Wilson interval. With zero errors in N bits we quote the bound 3/N "
        "(for example 7.5×10^{-7} for the 4M fresh set).",
        "**Complexity** as exact multiplications per symbol from {eq:macs}. The paper's 40 GBd budget, "
        "12,288 DSPs / 200 × 1.2 = 73.7 multiplications per input sample [@ney24], is 147 per symbol at $N_{os}=2$.",
        "**Hardware:** LUTs, flip-flops, DSP48E1 slices and BRAM after place and route; worst negative slack (WNS) and Fmax; "
        "throughput in samples per clock.",
        "**Power and energy:** Vivado power with switching activity annotated from gate-level simulation (SAIF) [@ug907], at "
        "200 MHz for all designs; dynamic energy per bit at the measured throughput."])

    # ---------------------------------------------------------------- 4 results
    R.h1("4. Results and Discussion")
    R.h2("4.1 Quantitative Results")
    R.para("{tab:ber} summarises the accuracy results of this section, which the following paragraphs explain in turn; Annex B gives the full tables.")
    R.table("ber", "BER of the main equalizers on the fresh 4M-symbol test set at 24 dB (best of three seeds).",
            ["Equalizer", "Mult. / symbol", "Loss", "BER, FP32", "BER, integer"], [
        ["FIR, 57 taps", "57", "LS", "8.3×10^{-4}", "–"],
        ["FIR, 121 taps", "121", "LS", "4.5×10^{-4}", "–"],
        ["Paper's CNN ($V_p$ 8, L 3, K 9, C 5)", "112.5", "MSE", "4.4×10^{-4}", "4.96×10^{-4} (W8)"],
        ["Paper's CNN", "112.5", "CE", "4.5×10^{-4}", "3.5×10^{-4} (W8)"],
        ["Ours ($V_p$ 4, L 4, K 9, C 3)", "121.5", "MSE", "9.4×10^{-4}", "8.6×10^{-4} (W8)"],
        ["Ours", "121.5", "CE", "2.7×10^{-5}", "2.2×10^{-5} (W6)"],
        ["FFE-25 + DFE2", "27", "LS", "5.0×10^{-7}", "–"],
        ["FFE-57 + DFE2", "59", "LS", "0 (< 7.5×10^{-7})", "–"],
        ["**Ours + DFE2 (deployed)**", "121.5", "CE", "3.5×10^{-6} †", "**5.0×10^{-7} (W8)**"],
    ], widths=[3100, 1300, 900, 1700, 2026], shade_rows=(8,),
            note="LS: least-squares fit; CE: cross-entropy. † FP32 value on the 2M stress-test set at 31.5 km, 24 dB. The DFE "
                 "taps need no multiplier: with d = ±1 each tap is an addition or a subtraction.")
    R.lead("Reproduction on Proakis-B.",
           "The FIR with 57 taps reaches 8.96×10^{-3} (paper: 9.6×10^{-3}). Over ten seeds, the paper's CNN trained with MSE "
           "spreads from 6.7×10^{-3} to 1.4×10^{-2}, and its expected best-of-three is 8.5×10^{-3}, matching the paper's "
           "8.4×10^{-3} ({fig:proakis}). Cross-entropy lowers the median from 1.13×10^{-2} to 6.7×10^{-3} (one-sided "
           "Mann–Whitney p = 0.011 [@mann47]). The same effect is starker for Volterra equalizers: fitted by MSE they are "
           "worse than the FIR, fitted by cross-entropy they fall to 8.3×10^{-4} at 610 multiplications. The optimal 4-state "
           "Viterbi detector makes no errors in 9.9×10^{5} symbols at 20 dB, which makes Proakis-B a weak showcase for any "
           "learned equalizer.")
    R.figure("fig04_proakis", "proakis",
             "Proakis-B at 20 dB. (a) BER against multiplications per symbol for FIR, Volterra (MSE and cross-entropy fits) and "
             "the paper's CNN over ten seeds; stars mark the paper's numbers. (b) Seed spread of the paper's CNN with each loss.")
    R.lead("Topology and loss search on the IM/DD link.",
           f"{{fig:dse}} shows all 270 screening runs. The paper's CNN only ties the 121-tap FIR (4.4×10^{{-4}} vs "
           f"4.5×10^{{-4}} on the fresh set), which reproduces the paper's ranking but not its margin. The best CNN within "
           f"the budget has four layers ($V_p=4$, K = 9, C = 3, 121.5 multiplications) and reaches 2.7×10^{{-5}} on the fresh "
           f"set: 16× below the paper's CNN (95 % interval of our BER: 2.2–3.3×10^{{-5}}). The gain comes from the loss and "
           f"the topology together. This 4-layer network trains poorly with MSE (median of three seeds 1.3×10^{{-3}}) and best "
           f"with cross-entropy (median 4.2×10^{{-5}}). The paper's 3-layer topology reaches about 4.5×10^{{-4}} with either "
           f"loss ({{tab:confirm}}). Over all 135 topologies cross-entropy wins 82 single-seed screens, loses 47 and ties 6 "
           f"(all at zero errors), but it is not uniformly better: within the budget most topologies with $V_p\\ge 8$ train "
           f"poorly with both losses. Several larger CNNs, from about 400 multiplications upward, make no errors in 2M bits.")
    R.figure("fig05_dse", "dse",
             "Search over 135 CNN topologies with each loss at 24 dB (one seed each), Pareto fronts over three seeds, the "
             "FIR baseline, and fresh-test results of the paper's CNN and ours. The dotted line is the paper's hardware "
             "budget.")
    R.lead("Decision feedback.",
           "Two feedback taps change the picture ({fig:stress}). At the paper's operating point (31.5 km, 16–24 dB) and at 20 km, "
           "a 57-tap FFE with two feedback taps (59 multiplications) beats every CNN and reaches zero errors in 2M bits from "
           "20 dB upward. The CNN wins where the channel is harder: at 14 dB, and at 40 km, where the FFE+DFE suffers from "
           "error propagation and falls behind the 121-tap linear FFE. Adding the same two taps to the CNN lowers its BER in all "
           "nine conditions, by 1.5–8×, which makes CNN+DFE the robust choice across conditions. At 50 km every equalizer in "
           "this budget stays above 3×10^{-3}.")
    R.figure("fig06_dfe_heatmap", "stress",
             "Stress test over nine channel conditions (best of three seeds; CNN medians in brackets). The best equalizer in "
             "each row is outlined.")
    R.lead("Quantization.",
           "Our cross-entropy CNN keeps its FP32 accuracy down to 6 bits (2.2×10^{-5}), while the paper's MSE-trained CNN needs "
           "8 bits (4.96×10^{-4}), consistent with the paper's learned widths of about 13 / 10 bits ({fig:quant}). Feedback "
           "needs a precise CNN output: at 6 bits the CNN+DFE is no better than the CNN alone. At 7 bits it reaches "
           "3.5×10^{-6}, and at 8 bits 5.0×10^{-7}, i.e. 2 errors in 4M bits (95 % interval 1.4×10^{-7} to 1.8×10^{-6}). We "
           "deploy the 8-bit CNN+DFE: the same bit width as the paper's CNN and about 1000× lower BER (at least 270× at 95 % "
           "confidence). Without its feedback taps, the same quantized network gives 2.1×10^{-4}.")
    R.figure("fig07_quant", "quant",
             "Integer-model BER against bit width (weights = activations = input) on the fresh 4M-symbol set. Dotted lines: FP32 "
             "references.", width_cm=12.6)

    R.lead("Timing closure.",
           "The first engine reached only 139 MHz. Each critical path was removed in turn ({tab:rtl} in Annex C). The "
           "requantization was split into five register stages (182 MHz), a 32-bit end-of-frame comparison was replaced by a "
           "small running counter of owed jobs (199 MHz), and Vivado timing directives closed 200 MHz. Three optimisation passes (r5–r7b) "
           "then cut the 6-bit design from 8,592 to 6,580 LUTs (LUT build) and from 136 to 45 DSPs (DSP build), without "
           "losing timing. Adding the DFE first dropped Fmax to 153 MHz because its input came straight from a LUT-RAM read. "
           "Registering that input (196 MHz) and moving the lane selection of the tap sums one stage earlier closed it at "
           "202.4 MHz.")
    R.lead("Final comparison.",
           "{tab:hw} compares the six final builds on the same engine and chip. In DSP builds, our 6-bit CNN uses 44 % fewer "
           "LUTs and 45 % fewer flip-flops than the paper's CNN for 23× lower BER. The deployed CNN+DFE needs 23 % fewer LUTs "
           "and flip-flops and one more DSP slice, with about 1000× lower BER. The paper's CNN closes at 187.9 MHz in the "
           "DSP build, ours at 202.4 MHz. Power is compared at a common 200 MHz. Dynamic power with simulated activity is "
           "0.259 W for our 6-bit CNN against 0.302 W for the paper's (−14 %), and 0.318 W for the CNN+DFE (+5 %). In LUT "
           "builds the 6-bit CNN saves 37 %. The vectorless estimates were optimistic, for example 0.220 W instead of 0.318 W "
           "for the deployed core. Because the engine sustains about 0.975 samples per clock, i.e. about 97.5 Mb/s per "
           "instance at 200 MHz, the dynamic energy is 2.5–4.0 nJ/bit.")
    R.table("hw", "Final engine on the XC7Z020-1: out-of-context place and route; power with SAIF activity at 200 MHz.",
            ["Design", "Bits", "BER", "Build", "Fmax (MHz)", "LUT", "FF", "DSP", "Dyn. power (W)", "nJ / bit"], [
        ["Paper's CNN", "8", "4.96×10^{-4}", "DSP", "187.9", "7,056", "11,543", "42", "0.302", "3.10"],
        ["Paper's CNN", "8", "4.96×10^{-4}", "LUT", "196.3", "10,907", "14,840", "2", "0.387", "3.97"],
        ["Ours", "6", "2.18×10^{-5}", "DSP", "207.2", "3,957", "6,393", "45", "0.259", "2.66"],
        ["Ours", "6", "2.18×10^{-5}", "LUT", "200.0", "6,580", "7,620", "3", "0.243", "2.49"],
        ["**Ours + DFE2 (deployed)**", "8", "5.0×10^{-7}", "DSP", "202.4", "5,430", "8,919", "43", "0.318", "3.26"],
        ["Ours + DFE2", "8", "5.0×10^{-7}", "LUT", "195.8", "10,331", "12,383", "3", "0.390", "4.00"],
    ], widths=[1560, 640, 1080, 680, 860, 800, 860, 560, 1050, 936], shade_rows=(4,), size=17,
            note="LUT builds keep the convolution multipliers in fabric (the 2–3 DSPs are requantization multipliers). "
                 "nJ/bit = dynamic power / 97.5 Mb/s. LUT and FF are the totals of Vivado's hierarchical utilisation report "
                 "of the routed design; the flat report differs by up to 5 % (relative savings change by at most 2 points).")
    R.para(
        "**System.** In the PYNQ-Z2 system the deployed equalizer meets 200 MHz with 0.160 ns of slack, and the 100 MHz "
        "DMA domain has 1.778 ns ({tab:sys}). The whole system uses 16 % of the device's LUTs and 20 % of its DSP slices; the "
        "processing system dominates the board-level power (1.26 W of 1.64 W).")
    R.table("sys", "Deployed PYNQ-Z2 system (CNN + DFE2, W8): placed and routed in context.",
            ["Resource", "Equalizer core", "Full system", "XC7Z020"], [
        ["LUT", "5,421", "8,416 (15.8 %)", "53,200"],
        ["Flip-flops", "8,718", "13,148 (12.4 %)", "106,400"],
        ["DSP48E1", "43", "43 (19.5 %)", "220"],
        ["Block RAM", "0", "2 RAMB36 + 2 RAMB18", "140 RAMB36"],
        ["Worst slack", "+0.160 ns at 200 MHz", "+1.778 ns at 100 MHz (DMA)", "–"],
    ], widths=[1800, 2300, 2900, 2026], first_col_bold=True)

    R.h2("4.2 Qualitative Results and Visualisations")
    R.para(
        "{fig:compare} places all six builds in one view. Each of our designs sits below and to the left of the paper's CNN "
        "with the same kind of multipliers: lower BER for less logic. Marker area, which encodes dynamic power, stays about "
        "the same, because power follows switched capacitance more than arithmetic count. The SAIF breakdown shows why: "
        "clock and signal nets together take 54–66 % of the dynamic power in every build, so the registers (parameter "
        "memory, windows, pipeline) and the nets they drive cost more power than the multipliers.")
    R.figure("fig12_compare", "compare",
             "Final comparison. (a) BER against LUTs for the six builds (circles: DSP builds, squares: LUT builds; marker area "
             "proportional to dynamic power). (b) DSP builds relative to the paper's CNN.")
    R.para(
        "The figures also explain *why* the improvements work. The fading nulls in {fig:link}b are the reason a few "
        "feedback taps beat a large CNN at 31.5 km: decision feedback rebuilds the interference that falls into the null, "
        "which no feed-forward filter of any size can recover. The CNN keeps its advantage when the eye is closed by noise "
        "(14 dB) or by longer dispersion (40 km), where wrong decisions would corrupt the feedback. Its own nonlinearity then "
        "pays off, and its decisions are good enough to feed back. The seed spreads in {fig:proakis}b and {tab:confirm} show "
        "a practical point the paper leaves implicit: with 5–10× variation between seeds, a best-of-three selection on a "
        "separate set is part of the method, and the final numbers must come from data the selection never saw.")

    R.h2("4.3 Discussion")
    R.para("**Strengths.**", after=40, keep_next=True)
    R.bullets([
        "Every step is reproducible from first principles: our own simulator, fixed and frozen datasets, a fresh test set, and "
        "a golden model that ties the trained network to the routed netlist bit for bit.",
        "The comparison with the paper is fair by construction: both CNNs use the same engine, chip and clock, and power comes "
        "from simulated activity.",
        "The hardware techniques are general: multiplier folding, two channels per DSP and the look-ahead DFE apply to any "
        "small streaming CNN on 7-series or newer devices.",
        "The baselines are deliberately strong (closed-form fits, cross-entropy Volterra, FFE+DFE, MLSE). That is how the "
        "decision-feedback result was found."])
    R.para("**Weaknesses.**", after=40, keep_next=True, before=60)
    R.bullets([
        "At the paper's operating point a much cheaper linear FFE with feedback is as good: on the same fresh set at 24 dB, "
        "FFE-57+DFE2 makes no errors and FFE-25+DFE2 (27 multiplications) matches our deployed 5.0×10^{-7}. The CNN's case "
        "rests on harder channels (14 dB, 40 km) and on robustness across conditions.",
        "One instance processes about 97.5 MBd. Reaching the paper's 40 GBd would take hundreds of parallel instances on a "
        "larger device, and the DFE recursion then needs an unrolled look-ahead across parallel symbols; neither is built here.",
        "The 6-bit model saves power, but the 8-bit CNN+DFE costs about 5 % more dynamic power than the paper's CNN, because "
        "its parameter memory and windows are wider."])
    R.para("**Threats to validity.**", after=40, keep_next=True, before=60)
    R.bullets([
        "All channel data are simulated: an ideal chirp-free modulator, white noise and no laser or amplifier nonlinearity. "
        "Measured links, such as the paper's, may contain impairments that feedback cannot cancel.",
        "The headline BER of 5.0×10^{-7} rests on two errors; its 95 % interval spans more than a factor of ten.",
        "The quantized models start from the best seed on the fresh set, a mild selection bias; the FP32 comparison itself "
        "is selection-free.",
        "Power is Vivado's model with 59–68 % of nets annotated from simulation, not a board measurement, and the on-board run "
        "is not yet done."])

    # ---------------------------------------------------------------- 5 conclusion
    R.h1("5. Conclusion")
    R.para(
        "We rebuilt the CNN equalizer of Ney et al. from first principles and reproduced its Proakis-B numbers to within a few "
        "percent. On a 40 GBd, 31.5 km IM/DD link, a decision-aligned loss and a wider topology search found a CNN with 16× "
        "lower BER at a similar cost. Two decision-feedback taps and 8-bit quantization took the integer BER to "
        "5.0×10^{-7}, about 1000× below the paper's CNN at the same bit width. A hand-written streaming engine runs this model "
        "at 200 MHz in a PYNQ-Z2 system, with 23 % fewer LUTs than the paper's CNN on the same engine. Every routed netlist "
        "matches the golden model bit for bit. The study also showed that the paper's complexity count is low by a factor of "
        "two, and that decision feedback, absent from the paper, is the strongest single idea for this channel.")
    R.para("**Limitations and future work.**", after=40, keep_next=True)
    R.bullets([
        "Run the overlay on the PYNQ-Z2 to measure BER, throughput and board power, and capture a real optical link (the lab's "
        "fibre trainer kit) to train and test on measured data.",
        "Scale towards line rate with parallel instances and a parallel look-ahead DFE, and study the co-design of ADC "
        "resolution and equalizer power (the simulator already models the ADC).",
        "Replace multipliers entirely with a LUT-native Kolmogorov-Arnold equalizer on raw ADC codes [@fischer25], and add soft "
        "outputs and output-layer adaptation, which the run-time-loadable weights already allow."])

    R.h2("Acknowledgements")
    R.para("We thank Dr. Ritesh Vyas for his guidance throughout the course and this project. The work used AMD Vivado 2025.2 "
           "(free edition), PyTorch, NumPy and SciPy.")

    # ---------------------------------------------------------------- references
    R.h1("References")
    refs_at = len(list(R.body.iterchildren())) - 1   # new elements go before the final sectPr

    # ---------------------------------------------------------------- annexes (written before the reference list is filled,
    # so citations in them are numbered too; the list is inserted at the References heading below)
    R.h1("Annex A: Team Contributions", page_break=True)
    R.para("[To be completed by the team: who did what. Both the report and the poster are assessed per member.]", italic=True)
    R.table("team", "Team contributions.", ["Team member", "Contribution", "Report / Poster"], [
        ["[Name 1 (ID)]", "[e.g., link simulator, datasets, baselines (FIR, Volterra, FFE+DFE, MLSE)]", "[sections]"],
        ["[Name 2 (ID)]", "[e.g., CNN search, cross-entropy study, decision feedback, quantization]", "[sections]"],
        ["[Name 3 (ID)]", "[e.g., RTL engine, verification, Vivado implementation, PYNQ-Z2 system, power]", "[sections]"],
    ], widths=[2000, 5026, 2000], align=["left", "left", "left"])

    R.h1("Annex B: Extended Results")
    R.table("confirm", "Fresh-test confirmation (4M symbols, 24 dB): BER of three seeds per configuration and loss.",
            ["Configuration", "Mult. / symbol", "Loss", "Best", "Median", "Worst"], confirm_rows(),
            widths=[3300, 1200, 1300, 1075, 1075, 1076])
    R.table("quantfull", "Integer-model BER against bit width (QAT, fresh 4M-symbol set).",
            ["Model", "FP32", "W8", "W7", "W6", "W5", "W4", "W3"], quant_rows(),
            widths=[2700, 950, 950, 750, 950, 950, 950, 826], size=16,
            note="† FP32 on the 2M stress-test set. CNN+DFE widths below 6 bits were not trained; post-training quantization alone "
                 "is much worse than QAT at 6 bits or fewer (e.g. 5.5×10^{-5} vs 2.2×10^{-5} for our W6 CNN).")
    R.table("stressfull", "Stress test: BER per channel condition (best of three seeds; CNN medians in brackets). "
                          "The best equalizer per condition is in bold.",
            ["Condition", "FFE-57", "FFE-121", "FFE-25 + DFE2", "FFE-57 + DFE2", "CNN", "CNN + DFE2"], stress_rows(),
            widths=[1500, 1150, 1150, 1300, 1300, 1313, 1313], size=16,
            note="Zero errors in 2M bits means BER < 1.5×10^{-6} at 95 % confidence. Multiplications per symbol: 57, 121, 27, 59, "
                 "121.5, 121.5.")

    R.h1("Annex C: RTL Revision History and Lessons")
    R.para("Every revision is kept as a full snapshot (`equalizer/rtl/history`) and was re-verified bit-exact before place and "
           "route. r1–r7b implement the 6-bit CNN, r8–r8c the 8-bit CNN+DFE.", after=80)
    R.table("rtl", "RTL revisions: best Fmax at a 5 ns target (XC7Z020-1, out of context) and resources.",
            ["Rev.", "Change", "LUT build: MHz / LUT / FF", "DSP build: MHz / LUT / FF / DSP"], [
        ["r1", "One-step requantization (variable shift up to 40 bits + clamp)", "139 / 8,176 / 8,898", "–"],
        ["r2", "Requantization split into multiply, round, coarse / fine shift, registered clamp", "182.3", "174.0"],
        ["r3", "Remaining-jobs counter at frame end (regressed: 14 logic levels); 2-stage multipliers; registered credit",
         "failed in opt_design", "156.1 / 3,950 / 5,312 / 136"],
        ["r4", "Running counter of owed jobs; then timing directives", "199.2 → 200.3 / 8,592 / 10,414", "198.7 → 201.4 / 3,572 / 5,474 / 136"],
        ["r5", "No job FIFO; DW-bit datapath; adder trees that widen per level", "201.7 / 7,316 / 9,812", "200.4 / 3,019 / 5,336 / 136"],
        ["r6", "Multiplier folding (FOLD); 1-stage LUT products below 14 bits", "200.0 / 6,464 / 7,624", "200.3 / 2,962 / 5,089 / 117"],
        ["r7", "Two channels per DSP (PACK) with borrow count; DSP attribute bug", "200.0 / 6,580 / 7,620", "204.8 / 3,989 / 6,409 / 83"],
        ["r7b", "Attribute fix: the pre-adder maps into the multiplier's DSP", "200.0 / 6,580 / 7,620", "**207.2 / 3,957 / 6,393 / 45**"],
        ["r8", "Decision feedback (`dfe_stream`), input taken combinationally", "153.2 / 10,346 / 12,363", "153.3 / 5,460 / 8,629 / 43"],
        ["r8b", "Registered DFE input (stage I)", "195.8 / 10,331 / 12,383", "195.6 / 5,444 / 8,834 / 43"],
        ["r8c", "Lane selection of the tap sums moved into stage I", "(as r8b)", "**202.4 / 5,430 / 8,919 / 43**"],
    ], widths=[650, 3900, 2100, 2376], align=["center", "left", "center", "center"], size=16)
    R.para("**Lessons that cost the most time.**", after=40, keep_next=True)
    R.bullets([
        "Moving a long computation to another cycle does not remove it (r3): only a different formulation (the running counter "
        "of r4) shortened the path.",
        "A `use_dsp` attribute on the pre-adder register made Vivado build the pre-addition in a DSP of its own, doubling the "
        "DSP count (r7: 83 instead of 45).",
        "Vendor IP, not the custom core, limited a single 200 MHz clock; two clock domains solved it at no cost to the core.",
        "On an 8 GB machine, parallel per-IP synthesis runs died silently; one global synthesis job fixed it. Post-route "
        "physical optimisation crashed reproducibly on the 8-bit builds and was disabled there.",
        "Gate-level simulation must wait for the global set/reset (100 ns) before releasing the design reset, or every "
        "flip-flop ignores its first inputs."])

    R.h1("Annex D: Reproducibility")
    R.para("All code, results and frozen artefacts are in the private repository listed on the title page (access on request); "
           "the main entry points are below. The FP32 models and datasets (`checkpoints/fp32_v1`), quantized models "
           "(`quant_v1`) and hardware builds (`hw_v1`, `hw_v2`, with the PYNQ overlay) are frozen read-only with SHA-256 "
           "manifests; git tags `v1.0-cnn-200mhz` and `v2.0-cnn-dfe-200mhz` mark the two hardware versions.", after=80)
    R.table("repro", "How to reproduce the main results (from the repository's equalizer folder).", ["Step", "Command / file"], [
        ["Unit tests", "python -m pytest -q  (11 tests)"],
        ["Proakis-B", "scripts/run_proakis.py, scripts/run_proakis_seeds.py --seeds 10"],
        ["IM/DD search", "scripts/run_imdd_dse.py --stage all, then --stage confirm --seeds 3"],
        ["Decision feedback", "scripts/run_dfe_stress.py; scripts/run_quant_dfe.py"],
        ["Quantization", "scripts/run_quant.py --bits 8 6 5 4 3"],
        ["RTL export", "scripts/export_rtl.py --model results/quant/<m>/integer_model.pkl --name <m>"],
        ["Simulation", "rtl/sim/run_sim.ps1 -Model <m> -Stall 30 -UseDsp 1; rtl/sim/run_unit.ps1"],
        ["Implementation", "rtl/syn/impl_ooc_opt.tcl <m> 5.0 <dsp> ...; rtl/bd/build_bd.tcl <m> 200 1 <tag> 100"],
        ["Power", "rtl/power/run_power.ps1 -Model <m>_short -OutDir <build>"],
        ["Report", "report/figures/make_figures.py; report/diagrams/build_diagrams.py; report/build_report.py"],
    ], widths=[2000, 7026], align=["left", "left"], first_col_bold=True, size=17)

    # ---------------------------------------------------------------- the reference list goes under its heading
    tail = list(R.body.iterchildren())[refs_at:-1]
    for el in tail:
        R.body.remove(el)
    unused = R.reference_list(BIB)
    for el in tail:
        R._add(el)
    if unused:
        print("bibliography entries never cited:", unused)
    done = R.apply_deferrals(defer or {})
    R.save(OUT)
    print("wrote", OUT, "| figures", len(R.labels["fig"]), "| tables", len(R.labels["tab"]), "| equations", len(R.labels["eq"]),
          "| references", len(R.cites))
    return done


# =============================================================================== layout pass
# Word places a figure or table that does not fit at the top of the next page and leaves the rest of the page empty.
# The pass below measures the layout in Word and moves the body paragraphs that follow such a float in front of it,
# one at a time, until no float leaves more than GAP_PT of empty space behind it. The result is kept in layout.json.
import subprocess
LAYOUT = Path(__file__).resolve().parent / "layout.json"
BODY_BOTTOM_PT = 841.9 - 65.0      # A4 height minus the template's bottom margin (1300 dxa)
GAP_PT = 85.0                      # 3 cm


def measure():
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(Path(__file__).resolve().parent / "measure_layout.ps1")], capture_output=True, text=True)
    rows = []
    for line in r.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) == 5:
            rows.append((parts[0], int(parts[1]), int(parts[2]), int(parts[3]), float(parts[4])))
    return rows


def layout_pass(max_iter=12):
    defer = {int(k): v for k, v in json.loads(LAYOUT.read_text()).items()} if LAYOUT.exists() else {}
    stuck = set()
    for it in range(max_iter):
        done = build(defer)
        for k, n in done.items():
            if n < defer.get(k, 0):
                defer[k] = n
                stuck.add(k)            # nothing more to move after this float
        changed = False
        for k, (kind, num, page, ppage, py) in enumerate(measure()):
            gap = BODY_BOTTOM_PT - (py + 14.0)
            if page == ppage + 1 and gap > GAP_PT and k not in stuck:
                print(f"  pass {it}: {kind} {num} starts page {page}, {gap / 28.35:.1f} cm left empty on page {ppage}")
                defer[k] = defer.get(k, 0) + 1
                changed = True
        if not changed:
            break
    LAYOUT.write_text(json.dumps({str(k): v for k, v in sorted(defer.items()) if v}, indent=1))
    build(defer)
    print("layout:", {k: v for k, v in defer.items() if v})


if __name__ == "__main__":
    import sys
    if "--no-layout" in sys.argv:
        build({int(k): v for k, v in json.loads(LAYOUT.read_text()).items()} if LAYOUT.exists() else {})
    else:
        layout_pass()
