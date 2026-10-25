# CNN equalizer RTL

Hand-written SystemVerilog streaming engine for the Ney et al. CNN template (one bitstream per topology, weights loadable at runtime). The contract with the Python side is in [WEIGHT_FORMAT.md](WEIGHT_FORMAT.md).

## Flow
1. **Quantize** (from the frozen FP32 checkpoints): `python scripts/run_quant.py` → `results/quant/<model>_w<b>/integer_model.pkl`.
2. **Export** a model to RTL artifacts:
   `python scripts/export_rtl.py --model results/quant/ours_bce_w6/integer_model.pkl --name ours_bce_w6`
   → `rtl/gen/ours_bce_w6/` (package, parameter image, test vectors).
3. **Simulate** bit-exact against the golden model (Vivado xsim):
   `powershell -File rtl/sim/run_sim.ps1 -Model ours_bce_w6 -Stall 30`
4. **Implement** out-of-context on the PYNQ-Z2 part:
   `vivado -mode batch -source rtl/syn/impl_ooc.tcl -tclargs ours_bce_w6 5.0`
   → `rtl/syn/out_ours_bce_w6_5.0ns/` (utilization, timing, power, routed checkpoint).

## Architecture (per layer, `src/conv1d_stream.sv`)
```
s_axis ─► K×IC window ─► job FIFO (2) ─► issue 1 output channel/cycle ─► IC·K multipliers ─► adder tree ─► +bias ─► ×M, round, >>>S, clamp ─► collect OC ─► out FIFO (16) ─► next layer
          (zero pad / flush per frame)        (credit: FIFO room for every in-flight job)
```
- With 1 input sample per clock at layer 0, every layer of both studied topologies needs only one output channel per cycle, so `IC·K` multipliers per layer suffice:
  - ours (vp4 L4 K9 C3): 9 + 27 + 27 + 27 = 90 multipliers;
  - the paper's (vp8 L3 K9 C5): 9 + 45 + 45 = 99 multipliers.
- Throughput: 1 sample/clk, i.e. f_clk / NOS symbols/s per instance (frame flush overhead about 1.7% at 1024-symbol frames).
