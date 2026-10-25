// dfe_stream.sv - decision feedback on the serialized equalizer output (improvement I5).
//
// Arithmetic (exactly IntegerModel.forward_int with fb set, see rtl/WEIGHT_FORMAT.md):
//   u[n] = z[n] + sum_k fb[v][k] * d[n-1-k],   v = lane of symbol n (n mod VP)
//   d[n] = +1 if u[n] > 0 else -1;  d = -1 before the first symbol of every frame
// Output: u (signed UW bits) per symbol, tlast passed through.
//
// Look-ahead so the decision loop is a single 2^N_FB:1 mux of one-bit flags:
//   fbsum[v][p] = sum_k (p[k] ? +fb[v][k] : -fb[v][k])      registered (taps are static)
//   stage A:  cand[p] = z + fbsum[v][p],  pos[p] = (cand[p] > 0)
//   stage B:  pattern = history of decisions (bit k = d[n-1-k] > 0);  u = cand[pattern];
//             history <= {history, pos[pattern]}  (reset to all -1 after a frame's last symbol)
// Both stages advance together when the output register is free (one symbol per clock).
`timescale 1ns/1ps
module dfe_stream #(
    parameter int VP    = 4,
    parameter int N_FB  = 2,
    parameter int ZW    = 16,          // input z width (signed)
    parameter int FW    = 16,          // feedback tap width (signed)
    localparam int UW   = ((ZW > FW) ? ZW : FW) + N_FB,   // u width: |z| + sum|fb| fits
    localparam int NP   = 1 << N_FB,
    localparam int VW   = (VP > 1) ? $clog2(VP) : 1
) (
    input  logic clk,
    input  logic rst,
    input  logic signed [FW-1:0] fb [VP][N_FB],   // stable while frames are in flight
    input  logic                 s_valid,
    output logic                 s_ready,
    input  logic signed [ZW-1:0] s_z,
    input  logic [VW-1:0]        s_lane,
    input  logic                 s_last,
    output logic                 m_valid,
    input  logic                 m_ready,
    output logic signed [UW-1:0] m_u,
    output logic                 m_last
);
    // static tap combinations per lane and decision pattern
    logic signed [UW-1:0] fbsum [VP][NP];
    always_ff @(posedge clk)
        for (int v = 0; v < VP; v++)
            for (int p = 0; p < NP; p++) begin
                logic signed [UW-1:0] acc;
                acc = '0;
                for (int k = 0; k < N_FB; k++) acc = p[k] ? acc + UW'(fb[v][k]) : acc - UW'(fb[v][k]);
                fbsum[v][p] <= acc;
            end

    wire adv = !m_valid || m_ready;
    assign s_ready = adv;

    // stage A: candidates for every decision pattern
    logic                 a_v, a_last;
    logic signed [UW-1:0] cand [NP];
    logic [NP-1:0]        pos;
    always_ff @(posedge clk) begin
        if (adv) begin
            a_v    <= s_valid;
            a_last <= s_last;
            for (int p = 0; p < NP; p++) begin
                logic signed [UW-1:0] c;
                c = UW'(s_z) + fbsum[s_lane][p];
                cand[p] <= c;
                pos[p]  <= (c > 0);
            end
        end
        if (rst) a_v <= 1'b0;
    end

    // stage B: select by the decision history; update the history
    logic [N_FB-1:0] hist;                 // bit k: d[n-1-k] > 0 (0 = -1)
    always_ff @(posedge clk) begin
        if (rst) begin
            m_valid <= 1'b0;
            hist    <= '0;
        end else if (adv) begin
            m_valid <= a_v;
            if (a_v) begin
                m_u    <= cand[hist];
                m_last <= a_last;
                if (a_last) hist <= '0;
                else begin
                    for (int k = N_FB - 1; k > 0; k--) hist[k] <= hist[k - 1];
                    hist[0] <= pos[hist];
                end
            end
        end
    end
endmodule
