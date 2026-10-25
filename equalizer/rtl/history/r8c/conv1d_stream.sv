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
//           window is captured as a "job". The newest job is held back in `pend`
//           until the next one is created (or the frame ends), so the frame's last
//           job can carry the frame-end flag; it is then handed straight to the
//           engine. If the engine cannot take it, the push that would replace it
//           waits (back-pressure), so no job queue is needed.
//   engine  issues one channel group per cycle: one output channel, or with PACK
//           two channels (2q, 2q+1) that share each multiplier. Each group takes
//           FOLD cycles, multiplying taps f*NM .. f*NM+NM-1 in fold phase f, so the
//           layer has NM = ceil(IC*K / FOLD) multipliers (DSP48 with PACK: one DSP
//           computes (w_hi * 2^PW + w_lo) * a, i.e. both channels' products).
//           Products go through registered adder trees (add_tree.sv), a fold
//           accumulator and, with PACK, a 2:1 serializer, so bias / requant always
//           see one output channel per cycle.
//   collect assembles the OC results of a position and pushes them into the
//           output FIFO. Jobs are only started when the FIFO is guaranteed to
//           have room for them (credit = OUT_DEPTH - occupancy - in flight).
//
// Input values are DW-bit codes in an AW-bit signed container: signed for the
// first layer (IN_SIGNED=1, ADC codes), unsigned activations 0..2^DW-1 otherwise.
// Hidden layers output clamp(((acc+bias)*M + 2^(S-1)) >>> S, 0, 2^BA-1) in an
// AW-bit signed container; the last layer (LAST=1) outputs z = acc + bias.
`timescale 1ns/1ps
module conv1d_stream #(
    parameter int IC     = 1,
    parameter int OC     = 3,
    parameter int K      = 9,
    parameter int STRIDE = 1,
    parameter int AW     = 9,     // activation container width (signed), ports
    parameter int DW     = AW,    // significant input bits (<= AW)
    parameter bit IN_SIGNED = 1,  // inputs signed (first layer) or unsigned activations
    parameter int WW     = 8,     // weight width (signed)
    parameter int ACC_W  = 24,    // accumulator / bias width (signed)
    parameter int BA     = 8,     // output activation bits (hidden layers)
    parameter bit LAST   = 0,
    parameter bit USE_DSP = 0,    // 1: conv multipliers in DSP48; 0: in LUTs
    parameter bit PACK   = 0,     // (USE_DSP, FOLD >= 2) two output channels per DSP
    parameter int FOLD   = 1,     // cycles per channel group: ceil(IC*K / FOLD) multipliers
    parameter int MUL2_PW = 14,   // LUT products of >= MUL2_PW bits get a second register stage
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
    localparam int JW     = NT * DW;                  // packed window width
    localparam int NM     = (NT + FOLD - 1) / FOLD;   // multipliers; fold phase f uses taps f*NM + m
    localparam int LEVELS = (NM > 1) ? $clog2(NM) : 0;
    localparam int NL     = PACK ? 2 : 1;             // channels per group (lanes)
    localparam int NG     = (OC + NL - 1) / NL;       // channel groups per job
    localparam int GW     = (NG > 1) ? $clog2(NG) : 1;
    localparam int CW     = (OC > 1) ? $clog2(OC) : 1;
    localparam int FW     = (FOLD > 1) ? $clog2(FOLD) : 1;
    localparam int PW     = DW + WW;                  // product width (signed)
    // product register stages: LUT 1 or 2 (hi/lo split for wide products); DSP MREG+PREG; packed DSP ADREG+MREG+PREG
    localparam int MUL_ST = PACK ? 3 : (USE_DSP || PW >= MUL2_PW) ? 2 : 1;

    // synthesis translate_off
    initial begin
        if (PACK && !(USE_DSP && FOLD >= 2)) $fatal(1, "conv1d_stream: PACK needs USE_DSP and FOLD >= 2");
        if (PACK && (WW + PW + 1 > 25 || DW + 1 > 18)) $fatal(1, "conv1d_stream: packed operands exceed DSP48E1 ports");
    end
    // synthesis translate_on

    // ------------------------------------------------------------------ window
    logic [DW-1:0] win [K][IC];                       // win[0] oldest ... win[K-1] newest
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

    // engine handshake (engine section below)
    logic busy, credit_ok;
    logic [GW-1:0] g;              // channel group being issued
    logic [FW-1:0] f;              // fold phase
    wire issue_end = (g == GW'(NG - 1)) && (f == FW'(FOLD - 1));
    wire can_load  = credit_ok && (!busy || issue_end);

    // window after shifting in `x` (x = input beat or zeros during flush)
    logic push;                    // shift the window this cycle
    logic [DW-1:0] push_x [IC];
    logic [DW-1:0] win_n [K][IC];
    always_comb begin
        for (int k = 0; k < K - 1; k++) win_n[k] = win[k + 1];
        win_n[K - 1] = push_x;
        for (int ic = 0; ic < IC; ic++)
            for (int k = 0; k < K; k++)
                win_next_packed[(ic * K + k) * DW +: DW] = win_n[k][ic];
    end

    // a push that creates a job must hand the held-back job to the engine in the same cycle
    wire push_ok = !(to_next == 1 && pend_valid && !can_load);
    wire job_now = push && (to_next == 1);
    assign s_ready = (st == RUN) && push_ok;

    logic load, load_last;         // hand `pend` to the engine (load_last: it is the frame's last job)
    always_comb begin
        push = 1'b0;
        for (int ic = 0; ic < IC; ic++) push_x[ic] = '0;
        if (st == RUN && s_valid && s_ready) begin
            push = 1'b1;
            for (int ic = 0; ic < IC; ic++) push_x[ic] = s_data[ic][DW-1:0];
        end else if (st == FLUSH && rem != 0 && push_ok) begin
            push = 1'b1;
        end
        load_last = (st == FINAL) && pend_valid && can_load;
        load      = (job_now && pend_valid) || load_last;
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
                FINAL: if (!pend_valid || can_load) begin  // last job handed over with the frame-end flag; new frame
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
    logic [JW:0]      job;         // {frame-last, window}
    logic [7:0]       inflight;
    logic             of_wr, of_full, of_rd, of_empty;
    logic [$clog2(OUT_DEPTH+1)-1:0] of_count;

    // registered credit, one slot conservative: occupancy + in flight grows by at most 1 per cycle
    always_ff @(posedge clk) credit_ok <= !rst && (of_count + inflight + 1 < OUT_DEPTH);

    always_ff @(posedge clk) begin
        if (rst) begin
            busy <= 1'b0;
            g <= '0;
            f <= '0;
            inflight <= '0;
        end else begin
            if (load) begin
                job  <= {load_last, pend};
                g    <= '0;
                f    <= '0;
                busy <= 1'b1;
            end else if (busy) begin
                if (issue_end) busy <= 1'b0;
                else if (f == FW'(FOLD - 1)) begin
                    f <= '0;
                    g <= g + 1'b1;
                end else f <= f + 1'b1;
            end
            inflight <= inflight + (load ? 8'd1 : 8'd0) - (of_wr ? 8'd1 : 8'd0);
        end
    end

    // ---------------------------------------------------- datapath pipeline
    // stage 0: operands; MUL_ST product stages; LEVELS tree stages; fold accumulate (FOLD > 1);
    // pair serializer (PACK); bias; requant (hidden layers).
    typedef struct packed { logic v; logic [GW-1:0] g; logic [FW-1:0] f; logic last; } tag_t;   // issue side
    typedef struct packed { logic v; logic [CW-1:0] c; logic last; } otag_t;                    // one output channel
    tag_t                    t0, t1;
    logic [DW-1:0]           a_r  [NM];
    logic signed [WW-1:0]    w_r  [NL][NM];           // lane l = output channel NL*g + l

    // operands of fold phase f: taps f*NM + m (zero beyond NT); weights of the group's channels
    always_ff @(posedge clk) begin
        t0 <= '{v: busy && !rst, g: g, f: f, last: job[JW]};
        for (int m = 0; m < NM; m++) begin
            a_r[m] <= '0;
            for (int l = 0; l < NL; l++) w_r[l][m] <= '0;
            for (int ph = 0; ph < FOLD; ph++)
                if (FW'(ph) == f && ph * NM + m < NT) begin
                    a_r[m] <= job[(ph * NM + m) * DW +: DW];
                    for (int l = 0; l < NL; l++)
                        for (int gg = 0; gg < NG; gg++)
                            if (GW'(gg) == g && NL * gg + l < OC) w_r[l][m] <= w[NL * gg + l][ph * NM + m];
                end
        end
        t1 <= t0;
        if (rst) begin  // valid bits of every tag stage are reset (data regs are not)
            t0.v <= 1'b0;
            t1.v <= 1'b0;
        end
    end

    // products per lane (+ borrow bits for the packed DSP)
    logic signed [PW-1:0] prod [NL][NM];
    logic                 brw  [NM];       // packed: low lane negative -> high lane reads one too low
    if (PACK) begin : g_mul_pack
        // (w_hi * 2^PW + w_lo) * a = w_hi*a * 2^PW + w_lo*a, |w_lo*a| < 2^(PW-1):
        // low lane = P[PW-1:0] exactly, high lane = P[2PW-1:PW] + (P[PW-1] ? 1 : 0)
        localparam int AWD = WW + PW + 1;                 // pre-adder output (DSP A/D port <= 25 bits)
        localparam int BWD = DW + 1;                      // DSP B port (<= 18 bits)
        localparam int MWD = AWD + BWD;
        // no use_dsp attribute on the pre-adder / operand registers: with "yes" Vivado builds the
        // pre-add in a DSP of its own instead of the multiplier DSP's A+D pre-adder
        logic signed [AWD-1:0] ad [NM];
        logic signed [BWD-1:0] b1 [NM];
        (* use_dsp = "yes" *) logic signed [MWD-1:0] m1 [NM];
        (* use_dsp = "yes" *) logic signed [MWD-1:0] p1 [NM];
        always_ff @(posedge clk) for (int m = 0; m < NM; m++) begin
            ad[m] <= (AWD'(w_r[0][m]) <<< PW) + AWD'(w_r[1][m]);                    // ADREG (pre-adder)
            b1[m] <= IN_SIGNED ? BWD'($signed(a_r[m])) : $signed({1'b0, a_r[m]});  // BREG
            m1[m] <= ad[m] * b1[m];                                               // MREG
            p1[m] <= m1[m];                                                       // PREG
        end
        always_comb for (int m = 0; m < NM; m++) begin
            prod[1][m] = p1[m][PW-1:0];
            prod[0][m] = p1[m][2 * PW - 1:PW];
            brw[m]     = p1[m][PW - 1];
        end
    end else if (USE_DSP) begin : g_mul_dsp
        (* use_dsp = "yes" *) logic signed [PW-1:0] p [NM];
        (* use_dsp = "yes" *) logic signed [PW-1:0] p2 [NM];
        always_ff @(posedge clk) for (int m = 0; m < NM; m++) begin
            p[m]  <= (IN_SIGNED ? $signed(a_r[m]) : $signed({1'b0, a_r[m]})) * w_r[0][m];   // MREG
            p2[m] <= p[m];                                                                // PREG
        end
        always_comb for (int m = 0; m < NM; m++) begin prod[0][m] = p2[m]; brw[m] = 1'b0; end
    end else if (MUL_ST == 1) begin : g_mul_lut1
        // narrow products: one LUT multiplier stage
        (* use_dsp = "no" *) logic signed [PW-1:0] p [NM];
        always_ff @(posedge clk) for (int m = 0; m < NM; m++)
            p[m] <= (IN_SIGNED ? $signed(a_r[m]) : $signed({1'b0, a_r[m]})) * w_r[0][m];
        always_comb for (int m = 0; m < NM; m++) begin prod[0][m] = p[m]; brw[m] = 1'b0; end
    end else begin : g_mul_lut2
        // wide products: a = a_hi * 2^H + a_lo (a_lo unsigned), two half-width products, then one add
        localparam int H  = DW / 2;
        localparam int HW = DW - H + (IN_SIGNED ? 0 : 1);   // signed width of a_hi
        (* use_dsp = "no" *) logic signed [H+WW:0]   p_lo [NM];
        (* use_dsp = "no" *) logic signed [HW+WW-1:0] p_hi [NM];
        logic signed [PW-1:0] p [NM];
        always_ff @(posedge clk) for (int m = 0; m < NM; m++) begin
            p_lo[m] <= $signed({1'b0, a_r[m][H-1:0]}) * w_r[0][m];
            p_hi[m] <= (IN_SIGNED ? $signed(a_r[m][DW-1:H]) : $signed({1'b0, a_r[m][DW-1:H]})) * w_r[0][m];
            p[m]    <= (PW'(p_hi[m]) <<< H) + PW'(p_lo[m]);
        end
        always_comb for (int m = 0; m < NM; m++) begin prod[0][m] = p[m]; brw[m] = 1'b0; end
    end

    // tag delay: t1 is aligned with the first product register; the products appear MUL_ST - 1
    // cycles later and the tree outputs LEVELS cycles after that
    localparam int TD = MUL_ST - 1 + LEVELS;
    tag_t tdl [TD + 1];
    always_comb tdl[0] = t1;
    for (genvar i = 1; i <= TD; i++) begin : g_tdl
        always_ff @(posedge clk) begin
            tdl[i] <= tdl[i - 1];
            if (rst) tdl[i].v <= 1'b0;
        end
    end
    tag_t tt;                                  // aligned with the tree outputs
    assign tt = tdl[TD];

    // adder trees (one per lane; widths grow per level, capped at ACC_W) + borrow count
    logic signed [ACC_W-1:0] tsum [NL];
    for (genvar l = 0; l < NL; l++) begin : g_lane
        logic signed [ACC_W-1:0] q;
        add_tree #(.N(NM), .IW(PW), .OW(ACC_W)) u_tree (.clk, .d(prod[l]), .q);
        if (PACK && l == 0) begin : g_brw
            localparam int BCW = $clog2(NM + 1) + 1;
            logic signed [1:0]     bd [NM];
            logic signed [BCW-1:0] bc;
            always_comb for (int m = 0; m < NM; m++) bd[m] = {1'b0, brw[m]};
            add_tree #(.N(NM), .IW(2), .OW(BCW)) u_cnt (.clk, .d(bd), .q(bc));
            assign tsum[l] = q + ACC_W'(bc);
        end else begin : g_nobrw
            assign tsum[l] = q;
        end
    end

    // fold accumulate: the FOLD partial sums of one channel group arrive on consecutive cycles
    tag_t ta;
    logic signed [ACC_W-1:0] tot [NL];
    if (FOLD > 1) begin : g_fold
        logic signed [ACC_W-1:0] part [NL];
        always_ff @(posedge clk) begin
            for (int l = 0; l < NL; l++) begin
                if (tt.v) part[l] <= (tt.f == 0) ? tsum[l] : part[l] + tsum[l];
                tot[l] <= ((tt.f == 0) ? ACC_W'(0) : part[l]) + tsum[l];
            end
            ta   <= tt;
            ta.v <= tt.v && (tt.f == FW'(FOLD - 1)) && !rst;
        end
    end else begin : g_nofold
        assign ta  = tt;
        assign tot = tsum;
    end

    // one output channel per cycle: with PACK, emit lane 0 (channel 2g) now and lane 1 (2g+1) next
    // cycle; groups complete at most every FOLD >= 2 cycles, so the second slot is always free
    otag_t to;
    logic signed [ACC_W-1:0] tot_o;
    if (PACK) begin : g_ser
        logic                    hold_v;
        otag_t                   hold_t;
        logic signed [ACC_W-1:0] hold_d;
        always_ff @(posedge clk) begin
            if (ta.v) begin
                to    <= '{v: 1'b1, c: CW'(2 * ta.g), last: ta.last};
                tot_o <= tot[0];
                hold_v <= (2 * ta.g + 1 < OC);
                hold_t <= '{v: 1'b1, c: CW'(2 * ta.g + 1), last: ta.last};
                hold_d <= tot[1];
            end else begin
                to    <= hold_t;
                to.v  <= hold_v;
                tot_o <= hold_d;
                hold_v <= 1'b0;
            end
            if (rst) begin
                to.v   <= 1'b0;
                hold_v <= 1'b0;
            end
        end
    end else begin : g_noser
        assign to    = '{v: ta.v, c: CW'(ta.g), last: ta.last};
        assign tot_o = tot[0];
    end

    // bias add
    otag_t tb;
    logic signed [ACC_W-1:0] acc_b;
    always_ff @(posedge clk) begin
        tb    <= to;
        acc_b <= tot_o + bias[to.c];
        if (rst) tb.v <= 1'b0;
    end

    otag_t te;                         // pipeline end
    logic signed [OUTW-1:0] val_e;

    if (LAST) begin : g_last
        assign te    = tb;
        assign val_e = acc_b;
    end else begin : g_requant
        // (acc+bias)*M -> +2^(S-1) -> >>> S (coarse: S[5:3]*8, fine: S[2:0]) -> clamp,
        // one register stage each, so no stage has more than one adder or shifter.
        localparam int RW = ACC_W + 17;          // (acc+bias) * M, M as 17-bit signed
        otag_t tm, tr, t1s, t2s, tc;
        logic signed [RW-1:0] p_m;
        logic signed [RW:0]   p_r, sh1, sh2;
        logic [5:0]           s_m, s_r, s_1;
        logic signed [OUTW-1:0] val_c;
        always_ff @(posedge clk) begin
            tm  <= tb;
            p_m <= acc_b * $signed({1'b0, mul[tb.c]});
            s_m <= shf[tb.c];
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
        of_wr = te.v && (te.c == CW'(OC - 1));
        for (int oc = 0; oc < OC; oc++)
            of_din[oc * OUTW +: OUTW] = (oc == OC - 1) ? val_e : vec[oc];
        of_din[OC * OUTW] = te.last;
    end
    always_ff @(posedge clk) if (te.v) vec[te.c] <= val_e;

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
    always_ff @(posedge clk) if (!rst && !x_seen && ($isunknown({load, of_wr, of_rd, push}))) begin
        x_seen <= 1;
        $display("%m X at %0t: load=%b of_wr=%b of_rd=%b push=%b te.v=%b te.c=%b busy=%b g=%b credit=%b of_count=%b inflight=%b st=%b to_next=%b",
                 $time, load, of_wr, of_rd, push, te.v, te.c, busy, g, credit_ok, of_count, inflight, st, to_next);
    end
    // synthesis translate_on
endmodule
