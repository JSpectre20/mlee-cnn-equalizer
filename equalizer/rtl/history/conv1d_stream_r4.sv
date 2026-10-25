// conv1d_stream.sv - one streaming Conv1D layer of the Ney et al. CNN equalizer.
//
// Frame semantics are identical to torch Conv1d(padding=K/2) applied to each
// frame on its own (see rtl/WEIGHT_FORMAT.md and eqsim/quant.py):
//   out[p] = sum_{ic,k} W[oc][ic][k] * x_pad[ic][p*STRIDE + k],  x_pad = PAD zeros | frame | PAD zeros
//   n_out  = ceil(n_in / STRIDE)
//
// Structure:
//   window  K x IC shift register fed by the input stream (zeros at frame start,
//           zero-flush after s_last); every STRIDE pushes an output position's
//           window is captured as a "job". Jobs are held back one step so the
//           frame's last job can carry the frame-end flag.
//   engine  pops a job and issues one output channel per cycle (OC cycles per
//           job, back-to-back across jobs) into a fully pipelined
//           multiply / adder-tree / requant datapath with IC*K multipliers.
//   collect assembles the OC results of a position and pushes them into the
//           output FIFO. Jobs are only started when the FIFO is guaranteed to
//           have room for them (credit = OUT_DEPTH - occupancy - in flight).
//
// Hidden layers output clamp(((acc+bias)*M + 2^(S-1)) >>> S, 0, 2^BA-1) in an
// AW-bit signed container; the last layer (LAST=1) outputs z = acc + bias.
`timescale 1ns/1ps
module conv1d_stream #(
    parameter int IC     = 1,
    parameter int OC     = 3,
    parameter int K      = 9,
    parameter int STRIDE = 1,
    parameter int AW     = 9,     // input activation width (signed container)
    parameter int WW     = 8,     // weight width (signed)
    parameter int ACC_W  = 24,    // accumulator / bias width (signed)
    parameter int BA     = 8,     // output activation bits (hidden layers)
    parameter bit LAST   = 0,
    parameter bit USE_DSP = 0,    // 1: conv multipliers in DSP48; 0: in LUTs
    parameter int OUT_DEPTH = 16,
    localparam int OUTW  = LAST ? ACC_W : AW,
    localparam int NT    = IC * K
) (
    input  logic clk,
    input  logic rst,
    // parameters (stable while frames are in flight)
    input  logic signed [WW-1:0]    w    [OC][NT],   // w[oc][ic*K + k]
    input  logic signed [ACC_W-1:0] bias [OC],
    input  logic [15:0]             mul  [OC],
    input  logic [5:0]              shf  [OC],
    // input stream: one position (IC channels) per beat
    input  logic                    s_valid,
    output logic                    s_ready,
    input  logic signed [AW-1:0]    s_data [IC],
    input  logic                    s_last,
    // output stream: one position (OC channels) per beat
    output logic                    m_valid,
    input  logic                    m_ready,
    output logic signed [OUTW-1:0]  m_data [OC],
    output logic                    m_last
);
    localparam int PAD    = K / 2;
    localparam int JW     = NT * AW;                  // packed window width
    localparam int LEVELS = (NT > 1) ? $clog2(NT) : 0;
    localparam int NPAD   = 1 << LEVELS;
    localparam int GW     = (OC > 1) ? $clog2(OC) : 1;
    localparam int PW     = AW + WW;                  // product width

    // ------------------------------------------------------------------ window
    logic signed [AW-1:0] win [K][IC];               // win[0] oldest ... win[K-1] newest
    logic [JW-1:0] win_next_packed, pend;
    logic          pend_valid;
    localparam int RMW = $clog2(PAD + 3);
    localparam int PHW = (STRIDE > 1) ? $clog2(STRIDE) : 1;
    logic [31:0]    n_in, created;
    // jobs owed = ceil(n_in / STRIDE) - created, kept as a small running count:
    // +1 on an input beat that opens a stride group, -1 per job created
    logic [RMW-1:0] rem;
    logic [PHW-1:0] phase;                             // n_in mod STRIDE
    logic [$clog2(STRIDE+PAD+2)-1:0] to_next;          // pushes left to_next the next output
    typedef enum logic [1:0] {RUN, FLUSH, FINAL} state_t;
    state_t st;

    logic          jf_wr, jf_full, jf_rd, jf_empty;
    logic [JW:0]   jf_din, jf_dout;
    logic [$clog2(3)-1:0] jf_count;

    sync_fifo #(.WIDTH(JW + 1), .DEPTH(2)) u_jobs (
        .clk, .rst, .wr_en(jf_wr), .din(jf_din), .full(jf_full),
        .rd_en(jf_rd), .dout(jf_dout), .empty(jf_empty), .count(jf_count));

    // window after shifting in `x` (x = input beat or zeros during flush)
    logic push;                    // shift the window this cycle
    logic signed [AW-1:0] push_x [IC];
    logic signed [AW-1:0] win_n [K][IC];
    always_comb begin
        for (int k = 0; k < K - 1; k++) win_n[k] = win[k + 1];
        win_n[K - 1] = push_x;
        for (int ic = 0; ic < IC; ic++)
            for (int k = 0; k < K; k++)
                win_next_packed[(ic * K + k) * AW +: AW] = win_n[k][ic];
    end

    wire job_now = push && (to_next == 1);
    assign s_ready = (st == RUN) && !jf_full;

    always_comb begin
        push = 1'b0;
        for (int ic = 0; ic < IC; ic++) push_x[ic] = '0;
        if (st == RUN && s_valid && s_ready) begin
            push = 1'b1;
            push_x = s_data;
        end else if (st == FLUSH && rem != 0 && !jf_full) begin
            push = 1'b1;
        end
        // push the held-back job when a newer one replaces it, or at frame end
        jf_wr  = (job_now && pend_valid) || (st == FINAL && !jf_full);
        jf_din = {(st == FINAL), pend};
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            st <= RUN;
            to_next <= PAD + 1;
            n_in <= '0;
            created <= '0;
            rem <= '0;
            phase <= '0;
            pend_valid <= 1'b0;
            for (int k = 0; k < K; k++) for (int ic = 0; ic < IC; ic++) win[k][ic] <= '0;
        end else begin
            if (push) begin
                win <= win_n;
                to_next <= (to_next == 1) ? STRIDE : to_next - 1'b1;
                if (job_now) begin
                    pend <= win_next_packed;
                    pend_valid <= 1'b1;
                    created <= created + 1'b1;
                end
            end
            case (st)
                RUN: if (s_valid && s_ready) begin
                    n_in  <= n_in + 1'b1;
                    phase <= (phase == PHW'(STRIDE - 1)) ? '0 : phase + 1'b1;
                    rem   <= rem + ((phase == 0) ? 1'b1 : 1'b0) - (job_now ? 1'b1 : 1'b0);
                    if (s_last) st <= FLUSH;
                end
                FLUSH: begin
                    if (job_now) rem <= rem - 1'b1;
                    if (rem == 0) st <= FINAL;
                end
                FINAL: if (!jf_full) begin  // last job pushed with the frame-end flag; new frame
                    st <= RUN;
                    pend_valid <= 1'b0;
                    to_next <= PAD + 1;
                    n_in <= '0;
                    created <= '0;
                    phase <= '0;
                    for (int k = 0; k < K; k++) for (int ic = 0; ic < IC; ic++) win[k][ic] <= '0;
                end
                default: st <= RUN;
            endcase
        end
    end

    // ------------------------------------------------------------------ engine
    logic             busy;
    logic [GW-1:0]    g;
    logic [JW:0]      job;
    logic [7:0]       inflight;
    logic             of_wr, of_full, of_rd, of_empty;
    logic [$clog2(OUT_DEPTH+1)-1:0] of_count;

    // registered credit, one slot conservative: occupancy + in flight grows by at most 1 per cycle
    logic credit_ok;
    always_ff @(posedge clk) credit_ok <= !rst && (of_count + inflight + 1 < OUT_DEPTH);
    wire load      = !jf_empty && credit_ok && (!busy || g == GW'(OC - 1));
    assign jf_rd   = load;

    always_ff @(posedge clk) begin
        if (rst) begin
            busy <= 1'b0;
            g <= '0;
            inflight <= '0;
        end else begin
            if (load) begin
                job  <= jf_dout;
                g    <= '0;
                busy <= 1'b1;
            end else if (busy) begin
                if (g == GW'(OC - 1)) busy <= 1'b0;
                else g <= g + 1'b1;
            end
            inflight <= inflight + (load ? 8'd1 : 8'd0) - (of_wr ? 8'd1 : 8'd0);
        end
    end

    // ---------------------------------------------------- datapath pipeline
    // stage 0: operands; stages 1-2: products; LEVELS tree stages; then bias and requant.
    typedef struct packed { logic v; logic [GW-1:0] g; logic last; } tag_t;
    tag_t                    t0, t1;
    tag_t                    tt [LEVELS + 1];
    logic signed [AW-1:0]    a_r  [NT];
    logic signed [WW-1:0]    w_r  [NT];
    logic signed [PW-1:0]    prod [NT];
    logic signed [ACC_W-1:0] tree [LEVELS + 1][NPAD];

    always_ff @(posedge clk) begin
        t0 <= '{v: busy && !rst, g: g, last: job[JW]};
        for (int n = 0; n < NT; n++) begin
            a_r[n] <= job[n * AW +: AW];
            w_r[n] <= w[g][n];
        end
        t1 <= t0;
        if (rst) begin  // valid bits of every tag stage are reset (data regs are not)
            t0.v <= 1'b0;
            t1.v <= 1'b0;
        end
    end

    // products, two register stages: LUT multipliers (default) or DSP48 (USE_DSP=1)
    if (USE_DSP) begin : g_mul_dsp
        (* use_dsp = "yes" *) logic signed [PW-1:0] p [NT];
        (* use_dsp = "yes" *) logic signed [PW-1:0] p2 [NT];
        always_ff @(posedge clk) for (int n = 0; n < NT; n++) begin
            p[n]  <= a_r[n] * w_r[n];     // MREG
            p2[n] <= p[n];                // PREG
        end
        assign prod = p2;
    end else begin : g_mul_lut
        // a = a_hi * 2^H + a_lo (a_lo unsigned): two half-width products, then one add
        localparam int H = AW / 2;
        (* use_dsp = "no" *) logic signed [H+WW:0]      p_lo [NT];
        (* use_dsp = "no" *) logic signed [AW-H+WW-1:0] p_hi [NT];
        logic signed [PW-1:0] p [NT];
        always_ff @(posedge clk) for (int n = 0; n < NT; n++) begin
            p_lo[n] <= $signed({1'b0, a_r[n][H-1:0]}) * w_r[n];
            p_hi[n] <= $signed(a_r[n][AW-1:H]) * w_r[n];
            p[n]    <= (PW'(p_hi[n]) <<< H) + PW'(p_lo[n]);
        end
        assign prod = p;
    end

    tag_t t2;
    always_ff @(posedge clk) begin
        t2 <= t1;
        if (rst) t2.v <= 1'b0;
    end

    always_comb begin
        for (int n = 0; n < NPAD; n++) tree[0][n] = (n < NT) ? ACC_W'(prod[n]) : '0;
        tt[0] = t2;
    end
    for (genvar lv = 0; lv < LEVELS; lv++) begin : g_tree
        always_ff @(posedge clk) begin
            for (int n = 0; n < (NPAD >> (lv + 1)); n++)
                tree[lv + 1][n] <= tree[lv][2 * n] + tree[lv][2 * n + 1];
            for (int n = (NPAD >> (lv + 1)); n < NPAD; n++) tree[lv + 1][n] <= '0;
            tt[lv + 1] <= tt[lv];
            if (rst) tt[lv + 1].v <= 1'b0;
        end
    end

    // bias add
    tag_t tb;
    logic signed [ACC_W-1:0] acc_b;
    always_ff @(posedge clk) begin
        tb    <= tt[LEVELS];
        acc_b <= tree[LEVELS][0] + bias[tt[LEVELS].g];
        if (rst) tb.v <= 1'b0;
    end

    tag_t te;                          // pipeline end
    logic signed [OUTW-1:0] val_e;

    if (LAST) begin : g_last
        assign te    = tb;
        assign val_e = acc_b;
    end else begin : g_requant
        // (acc+bias)*M -> +2^(S-1) -> >>> S (coarse: S[5:3]*8, fine: S[2:0]) -> clamp,
        // one register stage each, so no stage has more than one adder or shifter.
        localparam int RW = ACC_W + 17;          // (acc+bias) * M, M as 17-bit signed
        tag_t tm, tr, t1s, t2s, tc;
        logic signed [RW-1:0] p_m;
        logic signed [RW:0]   p_r, sh1, sh2;
        logic [5:0]           s_m, s_r, s_1;
        logic signed [OUTW-1:0] val_c;
        always_ff @(posedge clk) begin
            tm  <= tb;
            p_m <= acc_b * $signed({1'b0, mul[tb.g]});
            s_m <= shf[tb.g];
            tr  <= tm;
            p_r <= p_m + ((RW + 1)'(1) <<< (s_m - 1'b1));
            s_r <= s_m;
            t1s <= tr;
            sh1 <= p_r >>> {s_r[5:3], 3'b000};
            s_1 <= s_r;
            t2s <= t1s;
            sh2 <= sh1 >>> s_1[2:0];
            tc  <= t2s;
            if (sh2 < 0) val_c <= '0;
            else if (sh2 > (2 ** BA - 1)) val_c <= OUTW'(2 ** BA - 1);
            else val_c <= OUTW'(sh2);
            if (rst) begin
                tm.v <= 1'b0;
                tr.v <= 1'b0;
                t1s.v <= 1'b0;
                t2s.v <= 1'b0;
                tc.v <= 1'b0;
            end
        end
        assign val_e = val_c;
        assign te = tc;
    end

    // ------------------------------------------------------------- collector
    logic signed [OUTW-1:0] vec [OC];
    logic [OC*OUTW:0] of_din, of_dout;
    always_comb begin
        of_wr = te.v && (te.g == GW'(OC - 1));
        for (int oc = 0; oc < OC; oc++)
            of_din[oc * OUTW +: OUTW] = (oc == OC - 1) ? val_e : vec[oc];
        of_din[OC * OUTW] = te.last;
    end
    always_ff @(posedge clk) if (te.v) vec[te.g] <= val_e;

    sync_fifo #(.WIDTH(OC * OUTW + 1), .DEPTH(OUT_DEPTH)) u_out (
        .clk, .rst, .wr_en(of_wr), .din(of_din), .full(of_full),
        .rd_en(of_rd), .dout(of_dout), .empty(of_empty), .count(of_count));

    assign m_valid = !of_empty;
    assign of_rd   = m_valid && m_ready;
    assign m_last  = of_dout[OC * OUTW];
    always_comb for (int oc = 0; oc < OC; oc++) m_data[oc] = of_dout[oc * OUTW +: OUTW];

    // synthesis translate_off
    always_ff @(posedge clk) if (!rst && of_wr && of_full) $error("conv1d_stream: output FIFO overflow (credit bug)");
    bit x_seen = 0;
    always_ff @(posedge clk) if (!rst && !x_seen && ($isunknown({load, of_wr, jf_wr, of_rd, push}))) begin
        x_seen <= 1;
        $display("%m X at %0t: load=%b of_wr=%b jf_wr=%b of_rd=%b push=%b te.v=%b te.g=%b busy=%b g=%b jf_empty=%b credit=%b of_count=%b inflight=%b st=%b to_next=%b",
                 $time, load, of_wr, jf_wr, of_rd, push, te.v, te.g, busy, g, jf_empty, credit_ok, of_count, inflight, st, to_next);
    end
    // synthesis translate_on
endmodule
