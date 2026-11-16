# CONTEXT HANDOFF — MLEE project (read this first after any context loss)

Written 2026-11-16 because the chat context was about to run out. This file is the complete state of the project
and of the conversation with the user. More detailed, older sources (still authoritative):
- `equalizer/PROGRESS.md`: single source of truth for the project state, §0 says where to resume.
- `equalizer/rtl/history/CHANGES.md`: every RTL revision r1 to r8c, itemised, with P&R numbers.
- `MLEE_paper_shortlist_and_ideas.md`: the research and shortlist history.
- Auto-memory at `C:\Users\Admin\.claude\projects\C--Users-Admin-Documents-Bits-3-1-mlee-Project\memory\` (MEMORY.md, feedback-tool-access.md, mlee-project-shortlist.md).

---------------------------------------------------------------------------------------------------
## 0. RIGHT NOW: what was being done when context ran out

**Task the user gave (2026-11-16):** "start with the report. make an amazing research paper type report with everything we've done in detail, using good visual elements only when required is a plus (dont just stick to graphs, there are more which are far more appealing, explore), make sure all relevant data is included. dont stop until its a great report".

The user asked "why not LaTeX". I explained the trade-off and the user chose: **report in the Word (.docx) course template** (Recommended option); the **poster in LaTeX** later. TeX question:
- The user asked "how big is MiKTeX, is it worth it, will Tectonic suffice?".
- I answered that Tectonic suffices, and would install it later when we reach the poster (and ask then).
- **Nothing is installed yet. No LaTeX on this laptop.**

**FINAL DEADLINE: 20 Nov 2026 (firm). Today 16 Nov.** The fiber kit is post-submission unless the lab hands over a working analog-output kit immediately.

### Status of the report work
1. **Template analysed** (`Project submission templates/Project submission templates/MLEE_Project_Report_Template.docx`).
   - **Page and fonts:**
     - A4 (11906 x 16838 dxa), margins top/left/right 1440 dxa, bottom 1300, header/footer 708;
     - text width 9026 dxa = 15.9 cm; Arial everywhere.
   - **Header:** "BITS Pilani  |  MLEE Project Report". **Footer:** "[Project title] | Team [ID]\tPage X of Y" (fields).
   - **Title block, in order:**
     - a 1x1 table "[ Insert BITS Pilani logo here ]";
     - "Birla Institute of Technology and Science, Pilani" (Arial 13 pt bold, 1F3864, centred, spacing before 200 / after 40);
     - "Department of Electrical and Electronics Engineering";
     - "MLEE | Course Project Report" (11 pt bold, 2E75B6, after 240);
     - title paragraph (17 pt bold 1F3864, centred, top+bottom border 1F3864 sz 8 space 8, before/after 120);
     - a 6x2 info table (label column 2300 dxa shaded EAF1FB, value 6726 dxa; borders A6A6A6 sz 4; cell margins 70/110/70/110; 10 pt; label bold). Rows: Course / Team ID / Team members / Instructor / Date of submission / Code / data link.
   - **Abstract:** heading "Abstract", then a guidance box, then the text, then "Keywords:" (bold 10 pt) plus italic keywords.
   - **Body paragraphs:** Arial 11 pt (sz 22), justified, spacing after 120, line 276.
   - **Lists:** style ListParagraph with numPr numId 2, after 60, line 264, 11 pt.
   - **Headings:** Heading1 (Arial 14 bold 1F3864, numbered in text like "1. Introduction"); Heading2 (Arial 12 bold 2E75B6, "2.1 ...").
   - **Equations:** centred, right tab at 9026, equation text then "\t(1)".
   - **Figures:** a 1x1 table placeholder; caption below: "Figure N: ..." 9.5 pt italic, centred, before 80 / after 200.
   - **Tables:** the caption sits ABOVE the table: "Table N: ..." same style. Header row shaded D9E2F3, bold 10 pt, tblHeader repeat; borders A6A6A6 sz 4; cell margins 70/110; body 10 pt.
   - **Guidance boxes** (grey F2F2F2, left border 2E75B6, italic 9.5 pt, "Guidance: ...") MUST be removed in the final.
   - **Sections (keep this order):**
     - Abstract (120–150 words) + Keywords;
     - 1 Introduction (context, problem statement, objectives as a list, organisation);
     - 2 Background: 2.1 Theoretical Preliminaries (numbered equations), 2.2 Related Work, 2.3 Gap and Motivation;
     - 3 Methodology: 3.1 Overall Approach (+ Figure 1 pipeline), 3.2 Data and Preprocessing, 3.3 Model/Algorithm/Circuit Design, 3.4 Implementation and Experimental Setup (Table 1 hyperparameters), 3.5 Evaluation Metrics;
     - 4 Results and Discussion: 4.1 Quantitative (Table 2 baseline vs proposed), 4.2 Qualitative/Visualisations, 4.3 Discussion (strengths / weaknesses / threats to validity as bullets);
     - 5 Conclusion (summary, limitations, future work);
     - Acknowledgements (optional);
     - References (IEEE numeric, cited in order);
     - Annex A: Team Contributions (table: member / contribution / report-poster);
     - Annex B: Report–Poster Alignment Guide. **"delete this annex before submission"**: do NOT include it.
   - Guidance word counts (main body roughly 2,000–2,500 words): Introduction 250–350, Background 300–400, Methodology 400–500 plus 1 figure, Results 500–600 plus 2–4 figures/tables, Conclusion 150–200.
   - **Plan agreed with myself, and told the user:** follow the sections and styling exactly; write the main body as a full research paper (longer than the guidance is OK); put the deep detail in extra annexes:
     - Annex C: full DSE / quantization tables;
     - Annex D: RTL revision history;
     - Annex E: verification matrix;
     - Annex F: reproducibility (commands, repo layout, frozen checkpoints, tags).
   - Team members / IDs / Team ID are **unknown**: leave clearly marked placeholders "[Name (ID)]", "[Team ID]" and tell the user to fill them in.
     - Instructor: Dr. Ritesh Vyas.
     - Course: "EEE G513 Machine Learning for Electronics Engineers (MLEE)", Semester I 2026–27.
     - Date: 20 November 2026.
     - Code link: https://github.com/JSpectre20/mlee-cnn-equalizer (private; access on request).
     - The user's email (engrshreyansh@gmail.com) is private: do not put it in the report unless asked.
   - Logo: `Project submission templates/Project submission templates/bits_logo.png` (and dept_logo.png).
   - The instructions PDF ("Instructions for MLEE project.pdf") is image-only. Requirements known: team ≤ 3, report on the docx template, A3 colour poster on the LaTeX template, running code; the report must state member roles; no paper reused across groups.
2. **Tools:**
   - python-docx and PyMuPDF installed into `D:\venvs\mlee-eq` (2026-11-16).
   - **Microsoft Word is installed** (`C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE`). Convert docx→PDF through Word COM (PowerShell: `$w = New-Object -ComObject Word.Application; $d = $w.Documents.Open(path); $d.SaveAs([ref]pdf, [ref]17); $d.Close(); $w.Quit()`), then render pages with PyMuPDF (`fitz`) to PNG and inspect them with the Read tool.
   - No LibreOffice, pandoc or pdftoppm. docx-js (npm) is NOT installed. Plan: build the report with python-docx by opening the template, deleting the body content (keep sectPr, header, footer, styles) and appending our content with helper functions that reproduce the template's direct formatting.
3. **Figures:**
   - Script written: `report/figures/make_figures.py` (14 figures, 300 dpi, Arial, mathtext "cm", palette NAVY 1F3864 / BLUE 2E75B6 / LIGHT D9E2F3 / PALE EAF1FB / ORANGE C55A11 / GREEN 2E8B57 / GRAY 7F7F7F / PURPLE 7030A0 / RED C00000).
   - Run from Project/: `$env:PYTHONPATH="equalizer"; D:\venvs\mlee-eq\Scripts\python.exe report\figures\make_figures.py [fig_name ...]`.
   - **First run crashed at fig09 (`fig_pack_dfe`): mathtext has no `\bmod`. Fix: replace `v=n \bmod V_p` with `v=n\ \mathrm{mod}\ V_p`.** Figures 01–08 probably got written; re-run all and then LOOK at every PNG (Read tool) and fix overlaps or clipping.
   - Figure list (file → content):
     - fig01_pipeline: two lanes, ML (5 boxes) and HW (5 boxes), golden-model arrows.
     - fig02_link: (a) IM/DD chain diagram; (b) small-signal fading response simulated vs |cos(β2Lω²/2)|, nulls 11.1 / 19.3 GHz; (c, d) eye diagrams back-to-back vs 31.5 km (simulated with eqsim).
     - fig03_cnn: ours (vp4 L4 K9 C3 + DFE) vs paper (vp8 L3 K9 C5) layer diagrams with shapes for a 1024-symbol frame.
     - fig04_proakis: (a) BER vs MAC (FIR LS, Volterra MSE vs CE, CNN 10 seeds MSE/BCE, paper stars, MLSE note); (b) seed strip MSE vs CE with medians, p = 0.011.
     - fig05_dse: 135 configs x MSE/CE scatter, Pareto steps, FIR curve, 147-MAC budget line, paper star (4.4e-4 fresh) vs ours diamond (2.7e-5 fresh), "~16x".
     - fig06_dfe_heatmap: 9 conditions x 6 equalizers, log BER colour, best per row boxed.
     - fig07_quant: BER vs bits for 4 recipes + CNN+DFE W6/7/8, FP32 dotted lines.
     - fig08_rtl: (a) top-level chain; (b) conv1d_stream internals, credit loop.
     - fig09_pack_dfe: (a) DSP48E1 2-channel packing bit fields; (b) DFE look-ahead 4 candidates + 4:1 mux loop.
     - fig10_journey: (a) Fmax per revision r1..r7b (LUT / DSP) + DFE r8 / r8b / r8c, notes; (b) kLUT and DSP bars r4*..r7b.
     - fig11_system: PYNQ-Z2 system with 2 clock domains.
     - fig12_compare: (a) bubble chart BER vs kLUT, marker area = SAIF dynamic power; (b) DSP builds normalised to the paper (LUT, FF, DSP, dynamic power).
     - fig13_power: stacked SAIF power breakdown (Clocks / Logic / Signals / DSP / Static) for the 6 builds.
     - fig14_verif: verification pyramid (golden → unit TB → full model → mutation → gate level).
4. **Next steps for the report, in order:**
   1. fix \bmod and re-run the figures, then review every PNG;
   2. write `report/build_report.py` (python-docx on the template), all text content, Tables 1–N;
   3. build `report/MLEE_Report.docx`;
   4. convert to PDF via Word;
   5. render the pages and review each one; iterate until great;
   6. commit and push (git, see §9);
   7. Haiku subagent updates PROGRESS.md;
   8. tell the user to fill in names / IDs.
   After the report: the **poster** (LaTeX tikzposter A0 template `MLEE_Poster_Template.tex`, pdflatex/MiKTeX on the instructor's side; ask the user before installing Tectonic), then the **PYNQ notebook + on-board run** (the user must run it on the board).

---------------------------------------------------------------------------------------------------
## 1. Course, people, preferences
- **Course:** MLEE = EEE G513 Machine Learning for Electronics Engineers, BITS Pilani, Dept. EEE, instructor Dr. Ritesh Vyas.
  - Deliverables: report (docx template), A3 poster (LaTeX template), running code.
  - Title form due 20 Oct 2026 (done). **Final due 20 Nov 2026.**
- **Submitted title:** "Low-Complexity Neural Network Equalization for Optical Fibre Communication on FPGA".
- **The user:** BITS student, GitHub JSpectre20 (git user.name JSpectre20). Has Cadence, Vivado / Vitis 2025.2 (free Standard edition, no Enterprise, no RFSoC), a **PYNQ-Z2** (board files `C:\FPGA_boards\pynq-z2\A.0`), maybe a Zynq UltraScale+ via the professor. The old Zybo Z7-10 is retired. No Spartan-7 board, so the XC7S25 build was dropped ("keep it to pynq").
- **Preferences and working agreements (all from the user):**
  - Wants non-trivial, genuinely novel, publishable-quality work; avoids projects with readily available code.
  - Likes multi-tool projects; don't assume missing tools.
  - Short answers when asked ("brief", "short ans").
  - **Always record changes in detail and keep exact copies so any version can be restored** ("make sure to always mention wht changes u make in detail"). Snapshots live in `rtl/history/`, plus git tags.
  - "save copy of this model, dont just quantize directly": never overwrite progress; frozen checkpoints are read-only.
  - Optimisation work: "do 2 at once", carefully engineered passes; "write brilliant rtl that works efficiently and is optimized but can also be deployed so don't need to overdo it".
  - Only our w6 model had to reach 200 MHz; the paper's model is measured on the final engine at a common clock.
  - Progress tracking: keep PROGRESS.md updated; small doc edits through a **Haiku subagent**, heavy work by the main agent.
  - **Git: commit and push at every milestone** to the private repo; commit messages end with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
  - The user gets annoyed by sidetracking: keep focus, explain why when doing extra checks.
  - The user wanted KAN-LUT (I1) deferred: "would change the project too drastically", "maybe a paper after".
  - Real data: no breadboard; the PYNQ-Z2 audio-cable loopback is possible; maybe the lab fiber trainer kit. Focus on optimising before the deploy step.

## 2. Environment
- **Laptop:** Windows 11, 6C/12T, 8 GB RAM (Vivado peaks ~2 GB; run Vivado jobs ONE AT A TIME; parallel per-IP synthesis dies silently), GTX 1650 (unused), C: ~18 GB free, D: ~880 GB.
- **Python venv** `D:\venvs\mlee-eq` (Python 3.14, torch 2.14.1+cpu, numpy 2.5, scipy 1.18, matplotlib 3.11, pytest, python-docx, pymupdf). Pip cache D:\pip-cache. System Python has pypdf (use `python -P -E`).
- Run from `equalizer/` with `$env:PYTHONPATH = (Get-Location).Path`.
- **Vivado / Vitis 2025.2** at `D:\AMD\2025.2`. The `.bat` wrappers split arguments at '=' (use +stallN plusargs and generated include files). An empty '' argument is dropped by the .bat (pass the part explicitly: `xc7z020clg400-1`).
- gh CLI at `C:\Program Files\GitHub CLI\gh.exe` (logged in as JSpectre20). Git 2.55.

## 3. The base paper and the project idea
- **Base paper:** Ney, Füllner, Lauinger, Schmalen, Randel, Wehn, "CNN-Based Equalization for Communications: Achieving Gigabit Throughput with a Flexible FPGA Hardware Architecture", arXiv:2405.02323 (`papers/`).
  - Link: 40 GBd PAM2 IM/DD, 31.5 km SSMF, 40 GHz PD, N_os = 2.
  - CNN template (L layers, kernel K, C channels, V_p symbols/pass); selected L=3, K=9, C=5, V_p=8; MSE loss.
  - Learned bit widths ~13 b weights / 10 b activations.
  - Vitis HLS + Vivado 2022.2. High-throughput build on XCVU13P: 64 instances, 200 MHz, 9,648 DSP (78.5 %), 68 % LUT, 79 % BRAM. Low-power build on XC7S25-1CSGA324: DOP 1–225, 4–110 Mbit/s, 0.1–0.2 W (vectorless estimates).
  - Proakis-B h = [0.407, 0.815, 0.407] at 20 dB: CNN 8.4e-3 vs FIR 9.6e-3.
  - No public code or data.
- Research shortlist history (2026-10-20): A = Sensors 2025 TI-ADC Volterra+NN (user-named), 1 = OpenDPDv2, 2 = KANELÉ, 3 = Extended STE analog CIM, 4 = PPAAS, 5 = PINN-DAB. The user later chose the simpler P2 (Ney CNN equalizer). See `MLEE_paper_shortlist_and_ideas.md` and PROGRESS §9.
- **Related work / prior art for the report:**
  - Fischer, Matalla, Randel, Schmalen, "Non-linear Equalization in 112 Gb/s PONs Using KANs", OFC 2025, arXiv 2411.19631 (KAN equalizer, no hardware);
  - KANELÉ arXiv 2512.12850 (LUT-native KAN on FPGA);
  - Ney & Wehn trainable FPGA equalizer, DSD 2024, arXiv 2407.02967;
  - Ney et al. real-time demo arXiv 2402.15288;
  - imdd-task benchmark simulator arXiv 2412.03129;
  - Freire et al. JLT 2023;
  - Proakis, Digital Communications (Proakis-B channel, MLSE);
  - LSQ: Esser et al., ICLR 2020;
  - CD power fading in IM/DD (classic);
  - DFE fixes spectral nulls (classic);
  - NN + MLSE in PAM4 (TUM, JLT 2023);
  - CE vs MSE for NN equalizers (Marvell/WSU magnetic recording; Southampton minimum-BER);
  - LogicNets / PolyLUT / NeuraLUT (LUT-NN survey arXiv 2506.07367).
  - Verify exact citations before writing them (titles, venues).

## 4. Simulation and ML: what was built and found
- **eqsim package** (`equalizer/eqsim`):
  - pulses (RC / RRC); metrics (Gray BER, Wilson CI);
  - channels: ProakisBChannel; IMDDChannel (40 GBd, RRC β=0.2, 8 sps internal, MZM at quadrature m=0.8, CD 31.5 km D=16 ps/nm/km at 1550 nm, square-law PD, 4th-order Bessel 40 GHz, AWGN at the given electrical SNR, N_os=2, AC coupling + normalisation, optional ADC);
  - equalizers: FIR, Volterra (unique terms; MAC = M1 + 2P2 + 3P3), NeyCNN (exact MAC = K·C·nos/vp + (L−2)·K·C²·nos/vp + K·C; the paper's formula = exact / N_os); LS and logistic fits;
  - detectors (Viterbi MLSE); train (Adam, MSE or BCE); data (fixed datasets); quant (QAT/LSQ, BN folding, IntegerModel, golden forward_int, `dfe_int`, QuantCNNDFE, export_integer_dfe); dfe (FFE+DFE LS fit, own-decision DFE, CNNDFE, train_cnn_dfe teacher forcing, ber_cnn_dfe).
  - Tests: 11 pass (8 basics + 3 quant).
- **Proakis-B (20 dB, 1e6 test symbols):**
  - FIR LS: 3→5.67e-2, 5→3.30e-2, 9→1.65e-2, 17→1.17e-2, 25→1.03e-2, 41→9.07e-3, **57→8.96e-3** (paper FIR 9.6e-3).
  - Volterra MSE → CE: (9,3,3) 51 MAC 2.54e-2 → 8.7e-3; (13,5,3) 73 MAC 2.16e-2 → 5.7e-3; (15,5,5) 150 MAC 2.16e-2 → 3.2e-3; (25,9,5) 220 MAC 1.94e-2 → 2.6e-3; (25,9,9) 610 MAC 1.02e-2 → 8.3e-4; (35,15,9) 770 MAC 9.9e-3 → 8.5e-4. The MSE Volterra is worse than FIR.
  - Paper CNN, 10 seeds: MSE 6.71e-3…1.42e-2, median 1.13e-2, expected best-of-3 **8.5e-3 (paper 8.4e-3)**; BCE 4.61e-3…9.43e-3 (plus one diverged run 3.81e-2), median 6.7e-3, best-of-3 5.2e-3. **Mann-Whitney one-sided p = 0.011.**
  - MLSE: 0 errors in 9.9e5 at 20 dB; 9.8e-2 at 6 dB, 2.6e-2 at 9 dB, 1.6e-3 at 12 dB.
- **IM/DD sanity:** fading null 11.1 GHz (second 19.3 GHz) matches theory. FIR floor: FIR-121 4.1e-4 at 40 dB.
- **DSE** (`results/imdd_dse`, 24 dB): 135 configs (vp {1,2,4,8,16} x L {3,4,5} x K {9,15,21} x C {3,4,5}) x {MSE, BCE}, 1 seed, then Pareto with 3 seeds, then a fresh 4M-symbol test (seed 3). Train 2M (seed 1), test 2M (seed 2).
  - BCE won 81/121 screens. vp16 trains badly.
  - Budget 147 exact MAC/sym (paper's 12288 DSP / 200 · 1.2 = 73.7 in its units).
  - Fresh test, best / median of 3:

    | Model | MSE | CE |
    |---|---|---|
    | FIR57 | 8.3e-4 | 7.8e-4 |
    | FIR121 | 4.5e-4 | 3.8e-4 |
    | Paper CNN (vp8 L3 K9 C5, 112.5 MAC) | 4.4e-4 / 5.7e-4 | 4.5e-4 / 5.1e-4 |
    | vp4 L3 K15 C3 (135 MAC) | 1.3e-4 / 1.9e-4 | 1.2e-4 / 1.7e-4 |
    | **vp4 L4 K9 C3 (121.5 MAC)** | 9.4e-4 / 1.3e-3 | **2.7e-5 / 4.2e-5** |

  - Volterra CE best in budget (13,5,3) 3.9e-2; needs 1200 MAC for 5.5e-5. Big CNNs (400–2400 MAC) reach 0 errors.
- **Paper issues found:**
  1. The MAC formula undercounts by N_os = 2.
  2. MSE handicaps nonlinear / deeper models.
  3. No MLSE baseline.
  4. Large seed variance (best-of-3 matters).
  5. The selected topology only ties FIR on our link.
  6. Power is a vectorless estimate only; Proakis-B is a weak showcase.
  7. No DFE baseline: a tiny FFE+DFE beats every CNN at the paper's operating point.
- **Quantization** (`results/quant`, integer BER on the fresh 4M set; QAT LSQ lr 2e-4, 4000 it):

  | Model | FP32 | W8 | W6 | W5 | W4 | W3 |
  |---|---|---|---|---|---|---|
  | paper_mse | 4.39e-4 | 4.96e-4 | 3.09e-3 | 1.69e-2 | 6.39e-2 | 1.80e-1 |
  | paper_bce | 4.55e-4 | 3.45e-4 | 5.63e-4 | 1.96e-3 | 1.20e-2 | 7.43e-2 |
  | ours_mse | 9.38e-4 | 8.57e-4 | 1.26e-3 | 3.77e-3 | 2.96e-2 | 1.67e-1 |
  | ours_bce | 2.70e-5 | 1.13e-5 | **2.18e-5** | 1.72e-4 | 3.70e-3 | 9.10e-2 |

  - Integer contract: x_q = clamp(round_half_up(rx/s_in)); per-channel symmetric weights; hidden a' = clamp(((acc+b)·M + 2^(S−1)) >>> S, 0, 2^B_A − 1) with M u16, S in 1..40; last z = acc + b; decision z > 0.
  - Accumulators worst case: paper 21, ours W6 16, ours W8 20 bits.
- **DFE quick study** (`results/quick_dfe_mlse`, 4M fresh): FFE17 2.2e-2 → +DFE2 6.0e-5; FFE25 8.5e-3 → +DFE2 5.0e-7 (27 MAC); FFE33 → 7.5e-7; FFE41 / 57 + DFE2 → 0 errors.
  - Genie (true past symbols) FFE17+DFE2 1.5e-5; random feedback collapses to 0.22–0.28.
  - Viterbi: FFE57 + VA4(1,0.5,0.25) 1.0e-5; FFE121 + VA4 0.
- **DFE stress test** (`results/dfe_stress`; 1M train / 2M test per condition; CNN = vp4 L4 K9 C3 BCE, 3 seeds; best (median)):

  | Condition | FFE121 | FFE57+DFE2 | CNN | CNN+DFE2 |
  |---|---|---|---|---|
  | 20 km 20 dB | 2.6e-4 | 0 | 1.8e-5 (5.1e-5) | 6.5e-6 (9.0e-6) |
  | 31.5/14 | 2.5e-3 | 2.0e-4 | 5.4e-4 | **1.3e-4** |
  | 31.5/16 | 1.5e-3 | **2.4e-5** | 2.3e-4 | 4.6e-5 |
  | 31.5/18 | 9.1e-4 | **1.0e-6** | 9.9e-5 | 1.7e-5 |
  | 31.5/20 | 6.6e-4 | **0** | 5.7e-5 | 1.2e-5 |
  | 31.5/22 | 5.2e-4 | **0** | 4.2e-5 | 8.0e-6 |
  | 31.5/24 | 4.5e-4 | **0** | 2.9e-5 | 3.5e-6 |
  | 40 km 20 dB | 1.7e-3 | 2.0e-3 | 1.5e-3 | **5.2e-4** |
  | 50 km 20 dB | 3.3e-3 | 5.7e-3 | 4.7e-3 | **3.1e-3** |

  FFE57 and FFE25+DFE2 columns are also in the jsonl. CNN+DFE beats CNN everywhere (1.5–8x). FFE+DFE is best at ≥ 16 dB / 31.5 km and at 20 km; CNN+DFE wins at 40 km and 14 dB; FFE+DFE suffers error propagation at 40–50 km.
- **CNN+DFE2 QAT** (source `results/dfe_stress/models/snr24_L31.5_cnndfe_s1.pt`, FP32 3.5e-6): W6 2.8e-5 (9.5e-4 without feedback), W7 3.5e-6, **W8 5.0e-7** (2 errors in 4M; 2.1e-4 without feedback). Integer taps W8 [[-1864, -3978], [-1835, -3916], [-1763, -3763], [-1905, -4065]]. **Deployed model: ours_bce_dfe_w8.**

## 5. RTL (hand-written SystemVerilog, U-Net style, runtime-loadable weights)
- **Files** (`equalizer/rtl/src`): sync_fifo.sv, add_tree.sv, conv1d_stream.sv, dfe_stream.sv, cnn_eq_core.sv, cnn_eq_top.sv. Per-model package `rtl/gen/<model>/cnn_eq_pkg.sv` (+ params.mem, test vectors, tb_cfg.svh, meta.json) made by `scripts/export_rtl.py`.
- **Contract** in `rtl/WEIGHT_FORMAT.md`:
  - pmem word i at 0x4000 + 4i; per layer: weights ((oc·IC+ic)·K+k), bias, M, S (hidden layers);
  - FB taps at FB_OFF (v·N_FB + k);
  - registers ID 0x4E455131 "NEQ1", SHAPE, NPARAM, CTRL (bit 0 soft reset), FRAMES, BUSY_CYC, IN_BEATS, OUT_BEATS;
  - AXIS in 8-bit samples (TLAST at frame end), AXIS out 16-bit sat(z or u).
- **Architecture** (final r8c):
  - window shift register with per-frame zero pad / flush (torch Conv1d(padding=K/2) semantics, n_out = ceil(n/stride));
  - jobs-owed running counter;
  - held-back `pend` → `job` handoff (no job FIFO);
  - engine issues channel groups per cycle;
  - FOLD (multiplier sharing; core computes FOLD = cycles-per-job / groups);
  - PACK (2 output channels per DSP48E1 via the pre-adder, (w_hi·2^PW + w_lo)·a, borrow count tree);
  - MUL2_PW = 14 (LUT products ≥ 14 bits get a 2-stage hi/lo split);
  - adder trees with growing widths; fold accumulator; pair serializer; bias; requant (multiply, round, coarse/fine shift, registered clamp); collector + output FIFO 16 with registered, conservative credit;
  - dfe_stream: fbsum registered, stage I input register selecting the lane taps, stage A candidates + >0 flags, stage B 4:1 select, history reset to −1 per frame;
  - serializer 4 lanes → 1 symbol / beat; sat16.
- **Revisions and P&R** (XC7Z020-1, OOC; details in CHANGES.md):

  | Rev | Change | ours_bce_w6 |
  |---|---|---|
  | r1 | one-step requant | 139 MHz LUT (8,176 LUT) |
  | r2 | split requant | 182.3 LUT / 174.0 DSP |
  | r3 | regressed (rem calc) | 147–159 |
  | r4 | jobs-owed counter | 199.2 / 198.7; **directive flow** (impl_ooc_opt.tcl) **200.3 / 201.4** (8,592 LUT / 10,414 FF; DSP 3,572 / 5,474 / 136 DSP) |
  | r5 | no job FIFO, narrow datapath | 201.7 / 200.4; 7,316 LUT / 9,812 FF; DSP 3,019 / 5,336 / 136 |
  | r6 | FOLD + 1-stage mult | 200.0 / 200.3; 6,464 / 7,624; DSP 2,962 / 5,089 / 117 |
  | r7 | PACK (attribute bug) | 83 DSP, 3,989 LUT, 204.8 |
  | r7b | attribute fix | LUT 200.0, 6,580 / 7,620; **DSP 207.2, 3,957 / 6,393 / 45 DSP** |
  | r8 | DFE | ours_bce_dfe_w8 153 MHz (DFE input unregistered) |
  | r8b | input register | 195.6 |
  | **r8c** | lane select in stage I | **202.4 MHz, 5,430 LUT / 8,919 FF / 43 DSP** |

- **Final-engine comparison (OOC, 5 ns):**

  | Model | Build | MHz | LUT | FF | DSP |
  |---|---|---|---|---|---|
  | paper_mse_w8 | DSP | 187.9 | 7,056 | 11,543 | 42 |
  | paper_mse_w8 | LUT | 196.3 | 10,907 | 14,840 | 2 |
  | ours_bce_dfe_w8 | LUT (r8b) | 195.8 | 10,331 | 12,383 | 3 |

  (Post-route phys_opt off for paper_mse_w8: Vivado crash.)
- **PYNQ-Z2 system** (`rtl/bd/build_bd.tcl` + `cnn_eq_axi.v` wrapper):
  - PS7 board preset; FCLK0 100 MHz (DMA, interconnect, HP0 64-bit); FCLK1 200 MHz (core);
  - AXI DMA no SG, 32-bit streams / 64-bit MM;
  - axis_clock_converter + axis_dwidth_converter (32→8 in, 16→32 out); tkeep added in the wrapper;
  - global synthesis (`synth_checkpoint_mode None`, -jobs 1).
  - v1 (ours_bce_w6, r7b): WNS +0.119; core 3,865 LUT / 6,306 FF / 45 DSP / 0.155 W (vectorless); system 6,857 LUT; 1.58 W.
  - **v2 deployed (ours_bce_dfe_w8, r8c): core WNS +0.160 at 200 MHz, DMA +1.778; system 8,416 LUT / 13,148 FF / 43 DSP / 2 RAMB36 + 2 RAMB18; core 5,421 LUT / 8,718 FF / 43 DSP / 0.213 W (vectorless); system 1.642 W (PS7 1.26 W).** Overlay: `rtl/bd/proj_ours_bce_dfe_w8_200_dsp1_2clk_r8c/overlay/cnn_eq.{bit,hwh}` (frozen in checkpoints/hw_v2).
  - A single 200 MHz clock failed only in the DMA IP (WNS −0.948).
- **BRAM = 0 by design:** tiny parameters needed in parallel, shallow FIFOs in LUTRAM, window in flip-flops.
- **Throughput:** 1 sample/clk, ~0.975 samples/cycle on long frames (0.85–0.86 on 64-symbol frames), i.e. ~97.5 MBd / Mb/s per instance at 200 MHz.
- **Verification:**
  - golden integer model;
  - unit TB `tb_conv1d_unit.sv` (16 configs);
  - full-model TB `tb_cnn_eq.sv` (all models x LUT/DSP x stall 0/30);
  - mutations caught: owed counter phase, fold accumulate, borrow correction, lane 1, DFE no-reset, DFE tap swap;
  - **gate-level: all 6 final routed netlists bit-exact** (512/512).
- **SAIF power** (`rtl/power/run_power.ps1`; netlist funcsim at 200 MHz, `_short` vectors, after the parameter load; confidence High; 59–68 % of nets annotated):

  | Model | Build | Total | Dynamic |
  |---|---|---|---|
  | paper_mse_w8 | DSP | 0.409 | 0.302 |
  | paper_mse_w8 | LUT | 0.495 | 0.387 |
  | ours_bce_w6 | DSP | 0.365 | 0.259 (−14 %) |
  | ours_bce_w6 | LUT | 0.349 | 0.243 (−37 %) |
  | ours_bce_dfe_w8 r8c | DSP | 0.426 | 0.318 (+5 %); breakdown clocks 0.064, logic 0.075, signals 0.118, DSP 0.062 |
  | ours_bce_dfe_w8 | LUT | 0.499 | 0.390 (+1 %) |

  Vectorless was optimistic (0.220 → 0.318 dynamic). Energy ~2.5–3.3 nJ/bit.
- **Headline:**
  - ours W6: 23x lower BER than the paper's CNN with −44 % LUT / −45 % FF (DSP builds), −14 % / −37 % dynamic power;
  - ours W8+DFE2: ~1000x lower BER at the same 8 bits, −23 % LUT / FF, same DSPs, +1–5 % power.

## 6. Gotchas learned (put the important ones in the report's limitations / appendix)
- xsim `$urandom(seed)` not supported → use `process::self().srandom()`.
- The .bat wrappers split '='; xelab and xsim write xelab.log / xsim.log, so don't tee into them.
- Netlist sim: wait for glbl.GSR (first 100 ns) before reset release.
- Gate-level full-length vectors are too slow; use the `_short` sets.
- Vivado post-route phys_opt AggressiveExplore crashes reproducibly on 8-bit builds (postphys 0).
- `use_dsp="yes"` on the pre-adder register puts the pre-add in its own DSP.
- Parallel per-IP OOC synthesis OOMs on 8 GB.
- The DFE needs a precise CNN (W6 loses the gain).
- An app restart orphans background processes (they keep running but stop showing as tasks).

## 7. Frozen artifacts, versions, backups
- Checkpoints (read-only, SHA-256 MANIFEST.json, `scripts/freeze_checkpoints.py` / `freeze_artifacts.py` refuse to overwrite): `equalizer/checkpoints/fp32_v1` (FP32 models + datasets), `quant_v1` (results/quant + rtl/gen), `hw_v1` (CNN-only r7b system), `hw_v2` (r8c CNN+DFE system, overlay, reports).
- Git: private https://github.com/JSpectre20/mlee-cnn-equalizer, branch main, root = `Project/`. Tags `v1.0-cnn-200mhz`, `v2.0-cnn-dfe-200mhz`. Last commits: 0210238 (power flow), f103361 (power results), 3be1287 (PROGRESS power). `.gitignore` excludes Vivado projects, *.dcp, sim/power work dirs, results/**/*.npz, backups/.
- Zip backup: `Project/backups/equalizer_src_2026-10-25_1224.zip`.

## 8. Open items / to ask the user
- Team member names and IDs, Team ID; acknowledgements; who did what (Annex A). Suggested split: (1) simulator + data + baselines, (2) ML methods + experiments, (3) RTL / FPGA + poster.
- The PYNQ image version on the board (`pip show pynq`).
- The fiber kit (components needed: Tx module with an external modulation input, fiber + connectors, **Rx with an ANALOG output**, power supply, leads; optional attenuator + USB scope; the XADC ~1 MSa/s caps on-board capture at ~0.5 MBd).
- Whether to install Tectonic for the poster.

## 9. How to continue (commands)
- Figures: see §0. Tests: `D:\venvs\mlee-eq\Scripts\python.exe -m pytest -q` (from equalizer/).
- RTL sim: `powershell -File rtl\sim\run_sim.ps1 -Model <m> -Stall 30 -UseDsp 1`; unit: `rtl\sim\run_unit.ps1`.
- OOC P&R: `vivado -mode batch -source rtl/syn/impl_ooc_opt.tcl -tclargs <model> 5.0 <dsp> ../history/r8c <tag> 0 xc7z020clg400-1 <postphys>`.
- System: `rtl/bd/build_bd.tcl -tclargs <model> 200 1 <tag> 100`. Power: `rtl/power/run_power.ps1 -Model <m>_short -OutDir <out dir>`.
- Commit: `git add ...; git commit -m "..." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"; git push`.
