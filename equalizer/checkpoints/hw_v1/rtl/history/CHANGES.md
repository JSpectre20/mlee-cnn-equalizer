# conv1d_stream.sv revision history (timing closure, 2026-10-24)

The project has no git repository, so each timing revision of `rtl/src/conv1d_stream.sv` is kept here as a full snapshot, with every change listed. To go back to a revision, copy its snapshot over `rtl/src/conv1d_stream.sv` (and check the testbench note below). To simulate a snapshot without copying, run `rtl/sim/run_sim.ps1 -Model <m> -ConvSrc rtl\history\<file>`. To implement one: `rtl/syn/impl_ooc_opt.tcl` takes a `conv_src` argument.

Every snapshot is bit-exact against the golden model (`run_sim.ps1`, stall 30).

| Rev | Snapshot | Best Fmax at a 5 ns target (XC7Z020-1, OOC) |
|---|---|---|
| r1 | (not kept: superseded by r2, one-step requant) | 139–146 MHz |
| r2 | `conv1d_stream_r2.sv` | **ours_bce_w6 LUT 182.3**, DSP 174.0; ours_bce_w8 161.0 / 171.4; paper_mse_w8 156.9 / 169.2 |
| r3 | not kept (regressed; r4 replaces its FLUSH logic, the rest of r3 is in r4) | 147.0–158.9 |
| r4 | `conv1d_stream_r4.sv` | default flow: ours_bce_w6 199.2 LUT / 198.7 DSP; directive flow (`impl_ooc_opt.tcl`): **200.3 / 201.4 (met)**; paper_mse_w8 DSP 198.7 |
| r5 | `r5/` (full RTL snapshot: all four `.sv`) | pass 1, ours_bce_w6 (directive flow): **LUT 201.7 MHz**: 7,316 LUT (121 LUTRAM) / 9,812 FF / 3 DSP / 0.248 W (0.143 dyn); **DSP 200.4 MHz**: 3,019 LUT / 5,336 FF / 136 DSP / 0.284 W (0.179 dyn). paper_mse_w8 not run (decision: intermediate passes P&R ours_bce_w6 only; the paper's model is measured on the final engine; all models still simulated every pass) |
| r6 | `r6/` (full RTL snapshot) | pass 2, ours_bce_w6: **LUT 200.0 MHz** (WNS +0.001; critical = single-stage 12-bit LUT multiplier, 4.98 ns): 6,464 LUT (122 LUTRAM) / 7,624 FF / 3 DSP / 0.233 W (0.129 dyn); **DSP 200.3 MHz** (WNS +0.008; critical = g → weight mux → DSP B input, 83% route): 2,962 LUT / 5,089 FF / 117 DSP / 0.253 W (0.148 dyn) |
| r7 | `r7/` (full RTL snapshot incl. `add_tree.sv`) | pass 3a (P&R running, ours_bce_w6 DSP then LUT) |

Pass 1 vs r4 (ours_bce_w6, LUT): LUT −14.9% (8,592 → 7,316), LUTRAM 520 → 121, FF −5.8%, vectorless dynamic power 0.195 → 0.143 W. DSP build: LUT −15.5% (3,572 → 3,019). Its vectorless power estimate rose (0.132 → 0.179 W dyn); vectorless estimates are not reliable at this level, and power will be re-measured with simulation activity (SAIF) on the final engine.

r4 baseline for the optimisation passes (directive flow, 5 ns, XC7Z020-1): ours_bce_w6 LUT 8,592 LUT / 10,414 FF / 3 DSP / 0.300 W (0.195 dyn); DSP 3,572 / 5,474 / 136 / 0.237 W (0.132); paper_mse_w8 LUT 14,770 / 17,159 / 2 / 0.370 W (WNS −0.626); DSP 5,664 / 10,036 / 149 / 0.335 W (WNS −0.032).

## r1 → r2
- The requant was split into register stages: multiply, round-add, coarse shift by `S[5:3]*8`, fine shift by `S[2:0]`, registered clamp (was one stage: variable shift up to 40 + clamp + collector).
- Added the `USE_DSP` parameter (`use_dsp` attribute on the product registers).

## r2 → r3 (all in `conv1d_stream.sv`)
1. **FLUSH condition.** The 32-bit `n_out_total` register was replaced by `rem` (8-bit, jobs still to create) and `rem_nz` (registered `rem != 0`). Both were computed at the `s_last` beat as `ceil((n_in+1)/STRIDE) - created - job_now`. FLUSH pushed while `rem_nz`, decremented `rem` per job, and went to FINAL when `!rem_nz`.
   - **This was the mistake:** the 32-bit arithmetic still ran in the `s_last` cycle, chained after `job_now`, and became the new critical path (14 logic levels).
2. **Multipliers, two register stages.**
   - LUT: `a = a_hi*2^H + a_lo` with `H = AW/2` and `a_lo` unsigned; products `p_lo`, `p_hi` registered, then `p = (p_hi <<< H) + p_lo` registered.
   - DSP: `p` (MREG) then `p2` (PREG).
   - New tag stage `t2` (valid bit reset) between `t1` and `tt[0]`. Pipeline +1 cycle.
3. **Credit.** `credit_ok` is a register: `credit_ok <= !rst && (of_count + inflight + 1 < OUT_DEPTH)` (was combinational `of_count + inflight < OUT_DEPTH`). It is one slot conservative and safe because occupancy + in-flight grows by at most 1 per cycle.
4. Comment: "stage 1: products" → "stages 1-2: products".

## r3 → r4 (all in `conv1d_stream.sv`)
- `rem`/`rem_nz` replaced by a **running jobs-owed counter**:
  - `rem` (width `clog2(PAD+3)`) and `phase` (= `n_in mod STRIDE`, width `clog2(STRIDE)`, min 1);
  - RUN, per input beat: `phase` advances mod STRIDE, `rem <= rem + (phase == 0) - job_now`;
  - FLUSH: push while `rem != 0 && !jf_full`, `rem <= rem - 1` per job, go to FINAL when `rem == 0`;
  - reset and FINAL clear `phase` (`rem` is 0 at FINAL by construction).
- r3 changes 2–4 are kept.

## r4 → r5 (optimisation pass 1: no job FIFO, narrower datapath)
`conv1d_stream.sv`:
1. **Job FIFO removed.**
   - The 2-entry `u_jobs` FIFO (a copy of the whole packed window per entry, LUTRAM, with a wide write-enable fan-out) and the signals `jf_wr/jf_din/jf_rd/jf_dout/jf_empty/jf_full/jf_count` are gone.
   - The held-back job `pend` is handed straight to the engine `job` register:
     - `load = (job_now && pend_valid) || load_last`;
     - `load_last = (st == FINAL) && pend_valid && can_load`;
     - `job <= {load_last, pend}`.
   - New `can_load = credit_ok && (!busy || g == OC-1)`. A push that would create a job while `pend` is still waiting and the engine can't take it is held back: `push_ok = !(to_next == 1 && pend_valid && !can_load)`.
     - In RUN: `s_ready = (st == RUN) && push_ok`.
     - In FLUSH: push while `rem != 0 && push_ok`.
     - FINAL exits when `!pend_valid || can_load`.
   - The hold-back itself is kept. When STRIDE > PAD+1 (e.g. the paper's layer 0, stride 8), the frame's last job is created *before* `s_last`, so it can't be flagged at creation.
2. **Narrower datapath.**
   - New parameters `DW` (significant input bits) and `IN_SIGNED`. Window, `pend`, `job` and `a_r` are stored in DW bits (they were AW = max(B_IN, B_A+1)).
   - Products are computed as signed(DW+1) × WW for unsigned activations, and signed(DW) × WW for signed inputs, so PW = DW + WW (was AW + WW).
   - LUT split: `H = DW/2`, with `a_hi` signed or zero-extended to match.
3. **Adder tree widens level by level.** Generate blocks `g_lvl[lv]` with width `min(PW + lv, ACC_W)` (was ACC_W at every level). It's exact: every partial sum is bounded by sum|W|·max|x|, which `export_rtl.py` checks against ACC_W. Result: `acc_b <= ACC_W'(g_lvl[LEVELS].s[0]) + bias`.
4. Debug block: the X-check no longer lists `jf_*`.

`cnn_eq_core.sv`: layer 0 gets `.DW(B_IN), .IN_SIGNED(1)`; hidden and last layers get `.DW(B_A), .IN_SIGNED(0)`.

Verification:
- unit TB 16/16 PASS (now with `DW`/`IN_SIGNED` per instance: signed and unsigned, DW = AW and DW < AW);
- full models: 5 models × stall 0/30 (LUT) and 3 models (DSP) PASS;
- throughput unchanged (0.981–0.982 samples/cycle on long frames, 0.88–0.89 on short).

## r5 → r6 (optimisation pass 2: multiplier sharing, selective 2-stage products)
`conv1d_stream.sv`:
1. **New parameter `FOLD`.**
   - The engine issues each output channel over FOLD cycles with `NM = ceil(NT/FOLD)` multipliers. Fold phase `f` multiplies taps `f*NM + m` (zero beyond NT).
   - New counter `f` (width FW), with `issue_end = (g == OC-1) && (f == FOLD-1)` and `can_load = credit_ok && (!busy || issue_end)`.
   - The tag struct gains `f`.
   - Stage 0 selects the operands per phase (`a_r[m]`, `w_r[m]`; arrays now NM long). The adder tree is sized from NM (`LEVELS = clog2(NM)`).
   - A new fold-accumulate stage `g_fold` (FOLD > 1 only) does `part <= f==0 ? s : part + s` and `tot <= (f==0 ? 0 : part) + s`, with `ta.v` only on `f == FOLD-1`. For FOLD = 1, `ta`/`tot` are wires. The bias stage takes `tot`/`ta`.
2. **New parameter `MUL2_PW` (default 14).** `MUL_ST = (USE_DSP || PW >= MUL2_PW) ? 2 : 1`.
   - LUT products narrower than 14 bits use one register stage (`g_mul_lut1`); wider ones keep the r3 hi/lo split (`g_mul_lut2`). DSP builds keep MREG + PREG.
   - The tag delay `tp` (a register `g_tag2` or a wire `g_tag1`) matches the stages; it replaces the r3 `t2`.

`cnn_eq_core.sv`: a constant function `fold_of(l, oc)`.
- Cycles per job of layer l at 1 sample/clk = prod(STRIDE_L[0..l]). FOLD = 2 if 2·OC ≤ that, else 1.
- Result: the last layer folds by 2 in both studied topologies (ours: 27 → 14 multipliers; the paper's: 45 → 23); all other layers have FOLD = 1.
- ours_bce_w6 products are 12 bits wide, so 1 LUT stage; the w8 models' are 16 bits, so 2 stages.

Verification:
- unit TB 16/16 PASS. The macro gains a `fold` argument: FOLD 2 on NT = 27 / 45 (not multiples of 2), FOLD 3 on NT = 6, both one- and two-stage LUT products.
- A deliberately broken fold accumulate (`tot <= s_ext`) is caught (MISMATCH).
- Full models: 5 × stall 0/30 (LUT) + 3 (DSP) PASS.
- Throughput (long frames): ours 0.981 → 0.977, paper 0.982 → 0.974; short frames 0.88 → 0.86. The folded last layer has zero slack plus a few extra latency cycles per frame.

## r6 → r7 (optimisation pass 3a: two channels per DSP; adder trees kept out of DSPs)
New file `add_tree.sv`:
- a registered binary adder tree, widths `min(IW + lv, OW)` per level, latency `clog2(N)`, `(* use_dsp = "no" *)` on every level;
- it replaces the inline `g_lvl` generate of r5/r6 (same arithmetic and latency).

`conv1d_stream.sv`:
1. **New parameter `PACK`** (needs `USE_DSP` and `FOLD >= 2`; checked by `$fatal` in simulation).
   - Lanes `NL = PACK ? 2 : 1`; channel groups `NG = ceil(OC/NL)`. The engine counter `g` now counts groups, and `issue_end = (g == NG-1) && (f == FOLD-1)`.
   - The stage-0 weight registers become `w_r[NL][NM]` (lane l = channel NL·g + l; zero when that channel doesn't exist).
2. **Packed DSP (`g_mul_pack`):**
   - `ad <= (w_r[0] <<< PW) + w_r[1]` (the pre-adder, AWD = WW+PW+1 ≤ 25 bits); `b1 <= a` (DW+1 ≤ 18 bits); `m1 <= ad*b1`; `p1 <= m1` (`MUL_ST = 3`).
   - Low lane = `p1[PW-1:0]` (exact, since |w_lo·a| < 2^(PW-1)); high lane = `p1[2PW-1:PW]`, which reads one too low when the low lane is negative.
   - The borrow bits `p1[PW-1]` are counted by a second `add_tree` (`u_cnt`) and added to the high-lane tree output.
3. **Tags:** the tag delay is a generic chain `tdl[0..TD]`, `TD = MUL_ST - 1 + LEVELS`, so `tt` is aligned with the tree outputs. It replaces `tp` and `tt[]`.
4. **Fold accumulate** per lane (`part[l]`, `tot[l]`).
5. **New pair serializer `g_ser` (PACK):**
   - when a group completes, emit lane 0 as channel 2g now and hold lane 1 (channel 2g+1, if it exists) for the next cycle;
   - groups complete at most every FOLD ≥ 2 cycles, so the slot is free.
   - Output-side tags are a new `otag_t {v, c, last}` (channel index c); bias, requant and collector index by `c`.

`cnn_eq_core.sv`:
- `fold_of(l, oc, pack)` = max(1, cycles-per-job / channel groups), generalising r6.
- `pack_of(l, oc, nt, dw)` = USE_DSP && packed FOLD ≥ 2 && operands fit DSP48E1 (2·B_W + dw + 1 ≤ 25, dw + 1 ≤ 18) && fewer DSPs than unpacked.
- Result (DSP build):

  | Layer | Groups × fold | DSPs |
  |---|---|---|
  | ours L0 | 2 × 2 | 5 |
  | ours hidden | 2 × 2 | 14 each |
  | ours last | 2 × 4 | 7 |
  | paper L0 | 3 × 2 | 5 |
  | paper hidden | 3 × 2 | 23 |
  | paper last | 4 × 4 | 12 |

- LUT builds: unchanged choice (FOLD 1 except the last layer, FOLD 2).

Scripts: `add_tree.sv` added to `run_sim.ps1`, `run_unit.ps1` and `impl_ooc.tcl`; `impl_ooc_opt.tcl` adds it when the snapshot directory has it.

Verification:
- unit TB 16/16 PASS (`UT` macro gains `pk`; packed instances with OC = 4, 8 (even) and 3 (odd, idle second lane), FOLD 2/3);
- two deliberately broken copies are caught: no borrow correction (off by exactly the number of negative low-lane products, e.g. −1213 vs −1212), and lane 1 dropped;
- full models: 5 × stall 0/30 × LUT and DSP = 20/20 PASS;
- throughput (long frames): LUT 0.977 / 0.974 (ours / paper), DSP packed 0.975 / 0.973.

**r7 P&R (ours_bce_w6):**
- DSP build: 204.8 MHz (WNS +0.117), 3,989 LUT / 6,409 FF / **83 DSP** / 0.283 W (0.178 dyn).
- LUT build: 200.0 MHz (WNS 0.000), 6,580 LUT / 7,620 FF / 3 DSP / 0.245 W.
- 83 DSP instead of the expected ~43. The `(* use_dsp = "yes" *)` on the pre-adder register `ad` made Vivado build the pre-add in a DSP of its own, so each packed multiply took 2 DSPs (per layer 11 / 29 / 29 / 14 vs 6 / 15 / 15 / 7, requant included).
- LUTs rose (2,962 → 3,989) because `use_dsp = "no"` in `add_tree` moved the first-level tree adds that r6 had absorbed into DSP post-adders back into fabric (~200 LUT per 14-leaf tree).

## r7 → r7b (attribute fix)
- `conv1d_stream.sv` `g_mul_pack`: no `use_dsp` attribute on `ad` / `b1` (only on `m1` / `p1`), so the pre-add can map to the multiplier DSP's A+D pre-adder.
- `add_tree.sv`: no `use_dsp` attribute at all. Vivado may absorb first-level adds into DSP post-adders in DSP builds; LUT builds never did this in r4–r6 (3 DSP = requant only).
- Logic unchanged: unit TB 16/16 and ours_bce_w6 / paper_mse_w8 DSP stall 30 PASS.

**r7b P&R (ours_bce_w6):**
- **DSP build: 207.2 MHz** (WNS +0.174), 3,957 LUT / 6,393 FF / **45 DSP** (per layer 8 / 15 / 15 / 7, requant included) / 0.262 W (0.158 dyn).
- **LUT build: 200.0 MHz** (WNS 0.000), 6,580 LUT / 7,620 FF / 3 DSP / 0.245 W.
- Trade-off vs r6 (DSP build): DSP −62% (117 → 45), LUT +34% (2,962 → 3,957); the trees now sit in fabric (~410 LUT per 27-tap layer).
- **Chosen: r7b.** At ~60 LUT per DSP it's ~6.7k vs ~10.0k LUT-equivalent, and it fits an XC7Z010 (80 DSP), which r6 does not.
- Removing the trees entirely would need a DSP cascade (PCIN) with operand skew SRLs; not worth the complexity here.
- r7b is the final engine (= `rtl/src`).

## r7 → (pass 3b) PYNQ-Z2 in-context build
New `rtl/bd/cnn_eq_axi.v` (Verilog wrapper, needed for an IP Integrator module reference) and `rtl/bd/build_bd.tcl`:
- PS7 with the board preset, FCLK0 = <fclk> MHz, HP0 enabled;
- AXI DMA without SG (MM2S 8-bit, S2MM 16-bit), connected to the equalizer streams;
- equalizer and DMA lite on GP0, DMA masters on HP0;
- `Performance_ExplorePostRoutePhysOpt` strategy; bitstream + `.hwh` copied to `overlay/`.

Build history:
1. **First attempt (one 200 MHz clock, DMA streams 8/16 bit):** automation error. The DMA → HP0 rule must be applied to the `ps7/S_AXI_HP0` slave pin with an explicit `Master`; fixed.
2. **Single clock at 200 MHz:** implemented, bitstream produced, **timing failed (WNS −0.948 ns)**. Every failing path was in Xilinx IP (AXI DMA S2MM data-mover 5.9 ns / 9 levels; AXI interconnect upsizer and protocol converter); none in the equalizer.
3. **Fix: two clock domains.**
   - FCLK0 = 100 MHz for the DMA, interconnects and HP0; FCLK1 = 200 MHz for the equalizer.
   - The DMA moves 32-bit words over a 64-bit memory port (= HP0 width, so no upsizer).
   - `axis_clock_converter` + `axis_dwidth_converter` on both streams (32 → 8 bit in, 16 → 32 bit out).
   - The equalizer AXI-Lite crosses clocks in the GP0 interconnect.
   - `cnn_eq_axi.v` gains `s_axis_tkeep` (unused) and `m_axis_tkeep = 2'b11`, so the width converters keep both output bytes.
   - Bandwidth: 400 MB/s per direction vs 200 MB/s needed.
4. **Two-clock build with per-IP out-of-context synthesis, `-jobs 2`:** three IP synth runs died silently in `synth_design` (~1.6 GB each in parallel, 8 GB machine). Fixed with `synth_checkpoint_mode None` (one global synthesis) and `-jobs 1`.
5. **Result** (ours_bce_w6, DSP build, r7b):
   - **Timing met.** FCLK1 200 MHz WNS +0.119 ns, FCLK0 100 MHz WNS +1.693 ns; hold and pulse width met; 0 failing endpoints.
   - **System:** 6,857 LUT (12.9%) / 10,726 FF / 45 DSP / 3 BRAM, of which:
     - equalizer 3,865 LUT / 6,306 FF / 45 DSP;
     - DMA 1,599 LUT / 2,285 FF;
     - interconnects ~1,150 LUT;
     - stream converters ~190 LUT.
   - **Power (vectorless):** 1.58 W total, of which PS7 1.26 W and equalizer 0.155 W.
   - Overlay: `rtl/bd/proj_ours_bce_w6_200_dsp1_2clk/overlay/cnn_eq.{bit,hwh}`.

## Testbench / script changes made alongside (not part of the RTL snapshots)
- r5: `tb_cnn_eq.sv` timeout dump no longer prints `jf_count`. `tb_conv1d_unit.sv` gains `DW`/`IN_SIGNED` parameters (macro `UT(i, ic, oc, k, s, aw, dw, sg, ww, last, dsp, ist, ost)`). `impl_ooc_opt.tcl` accepts a snapshot directory as `conv_src`.
- `tb_cnn_eq.sv`:
  - the timeout debug dump no longer prints `n_out_total` / `rem`, so the TB elaborates with every revision;
  - includes `tb_dsp.svh` (`localparam bit USE_DSP`, written by `run_sim.ps1`) and passes it to `cnn_eq_top`.
- `run_sim.ps1`: new `-UseDsp 0|1` and `-ConvSrc <path>` options.
- New: `tb_conv1d_unit.sv` + `run_unit.ps1` (layer-level unit TB, 16 configurations).
- New: `rtl/syn/impl_ooc_opt.tcl` (directive flow, selectable conv source). `impl_ooc.tcl` is unchanged.
