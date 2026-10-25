// add_tree.sv - registered binary adder tree, kept in fabric (no DSP).
// q = sum(d[0..N-1]) after LEVELS = clog2(N) clock cycles (0 for N = 1, combinational).
// Level lv holds sums of 2^lv inputs in min(IW + lv, OW) bits; the caller guarantees that
// every partial sum fits in OW bits (for the conv layers: sum|W|*max|x| < 2^(ACC_W-1)).
`timescale 1ns/1ps
module add_tree #(
    parameter int N  = 4,
    parameter int IW = 8,         // input width (signed)
    parameter int OW = 16,        // output width (signed), caps the level widths
    localparam int LEVELS = (N > 1) ? $clog2(N) : 0
) (
    input  logic                 clk,
    input  logic signed [IW-1:0] d [N],
    output logic signed [OW-1:0] q
);
    localparam int NPAD = 1 << LEVELS;
    for (genvar lv = 0; lv <= LEVELS; lv++) begin : g_lvl
        localparam int LW = (IW + lv < OW) ? IW + lv : OW;
        (* use_dsp = "no" *) logic signed [LW-1:0] s [NPAD >> lv];
        if (lv == 0) begin : g_leaf
            always_comb for (int n = 0; n < NPAD; n++) s[n] = (n < N) ? LW'(d[n]) : '0;
        end else begin : g_add
            always_ff @(posedge clk)
                for (int n = 0; n < (NPAD >> lv); n++) s[n] <= g_lvl[lv - 1].s[2 * n] + g_lvl[lv - 1].s[2 * n + 1];
        end
    end
    assign q = OW'(g_lvl[LEVELS].s[0]);
endmodule
