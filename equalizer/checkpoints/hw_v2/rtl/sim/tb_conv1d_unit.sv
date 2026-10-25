// tb_conv1d_unit.sv - self-checking unit test bench for conv1d_stream.
//
// Each ut_conv1d instance drives one conv1d_stream configuration with random
// weights / bias / requant parameters and random frames (length 1..40 plus a few
// long ones, so frames shorter than PAD and lengths that are not multiples of
// STRIDE are covered), with random input gaps and output back-pressure, and
// compares every output beat with a direct reference of the documented semantics:
//   out[p] = sum_{ic,k} W[oc][ic*K+k] * x_pad[ic][p*STRIDE + k],  n_out = ceil(n/STRIDE)
//   hidden: clamp(((acc+bias)*M + 2^(S-1)) >>> S, 0, 2^BA-1);  last: acc + bias
`timescale 1ns/1ps
module ut_conv1d #(
    parameter int IC = 1, OC = 3, K = 9, STRIDE = 1, AW = 7, DW = 6, WW = 6,
    parameter bit IN_SIGNED = 1,                // signed DW-bit inputs, or unsigned 0..2^DW-1
    parameter bit LAST = 0, USE_DSP = 0,
    parameter int FOLD = 1,
    parameter bit PACK = 0,                     // two channels per DSP (USE_DSP, FOLD >= 2)
    parameter int ISTALL = 30, OSTALL = 30,     // % of cycles with input gap / output not ready
    parameter int FRAMES = 80, SEED = 1
) (
    input  logic clk,
    input  logic rst,
    output logic done,
    output int   errors
);
    localparam int ACC_W = 24;
    localparam int BA    = AW - 1;
    localparam int NT    = IC * K;
    localparam int PAD   = K / 2;
    localparam int OUTW  = LAST ? ACC_W : AW;

    logic signed [WW-1:0]    w    [OC][NT];
    logic signed [ACC_W-1:0] bias [OC];
    logic [15:0]             mul  [OC];
    logic [5:0]              shf  [OC];
    logic                    s_valid = 0, s_ready, s_last = 0;
    logic signed [AW-1:0]    s_data [IC];
    logic                    m_valid, m_ready = 0, m_last;
    logic signed [OUTW-1:0]  m_data [OC];

    conv1d_stream #(
        .IC(IC), .OC(OC), .K(K), .STRIDE(STRIDE), .AW(AW), .DW(DW), .IN_SIGNED(IN_SIGNED), .WW(WW),
        .ACC_W(ACC_W), .BA(BA), .LAST(LAST), .USE_DSP(USE_DSP), .FOLD(FOLD), .PACK(PACK)
    ) dut (
        .clk, .rst, .w, .bias, .mul, .shf,
        .s_valid, .s_ready, .s_data, .s_last,
        .m_valid, .m_ready, .m_data, .m_last);

    longint exp_q[$];      // OC values per output position
    bit     exp_last[$];
    int     n_exp = 0, n_got = 0;
    bit     sent_all = 0;

    function automatic longint srand_bits(int bits);
        return longint'($urandom_range((1 << bits) - 1)) - (longint'(1) <<< (bits - 1));
    endfunction

    // reference for one frame x[ic][t], t < n
    task automatic expect_frame(input longint x[][], input int n);
        int n_out = (n + STRIDE - 1) / STRIDE;
        for (int p = 0; p < n_out; p++) begin
            for (int oc = 0; oc < OC; oc++) begin
                longint acc = 0, v;
                for (int ic = 0; ic < IC; ic++)
                    for (int k = 0; k < K; k++) begin
                        int t = p * STRIDE + k - PAD;
                        if (t >= 0 && t < n) acc += longint'(w[oc][ic * K + k]) * x[ic][t];
                    end
                acc += longint'(bias[oc]);
                if (LAST) v = acc;
                else begin
                    v = (acc * longint'(mul[oc]) + (longint'(1) <<< (shf[oc] - 1))) >>> shf[oc];
                    if (v < 0) v = 0;
                    if (v > (1 << BA) - 1) v = (1 << BA) - 1;
                end
                exp_q.push_back(v);
            end
            exp_last.push_back(p == n_out - 1);
            n_exp++;
        end
    endtask

    // parameters: random, with M / S chosen so requant outputs span the clamp range
    initial begin
        int acc_bits;
        process::self().srandom(SEED);
        acc_bits = DW + WW - 2 + $clog2(NT + 1) - 1;
        for (int oc = 0; oc < OC; oc++) begin
            for (int n = 0; n < NT; n++) w[oc][n] = WW'(srand_bits(WW));
            bias[oc] = ACC_W'(srand_bits(DW + WW - 1));
            mul[oc]  = 16'($urandom_range(65535, 32768));
            shf[oc]  = 6'(acc_bits + 16 - BA + $urandom_range(2) - 1);
        end
        for (int ic = 0; ic < IC; ic++) s_data[ic] = '0;
    end

    // driver
    initial begin
        process::self().srandom(SEED + 1000);
        done = 0;
        @(negedge rst);
        repeat (3) @(posedge clk);
        for (int f = 0; f < FRAMES; f++) begin
            int n;
            longint x[][];
            n = (f < 4) ? f + 1 : ($urandom_range(9) == 0) ? $urandom_range(120, 41) : $urandom_range(40, 1);
            x = new[IC];
            for (int ic = 0; ic < IC; ic++) begin
                x[ic] = new[n];
                for (int t = 0; t < n; t++) x[ic][t] = IN_SIGNED ? srand_bits(DW) : longint'($urandom_range((1 << DW) - 1));
            end
            expect_frame(x, n);
            for (int t = 0; t < n; t++) begin
                while ($urandom_range(99) < ISTALL) begin s_valid <= 1'b0; @(posedge clk); end
                s_valid <= 1'b1;
                s_last  <= (t == n - 1);
                for (int ic = 0; ic < IC; ic++) s_data[ic] <= AW'(x[ic][t]);
                @(posedge clk);
                while (!s_ready) @(posedge clk);
            end
            s_valid <= 1'b0;
            if ($urandom_range(3) == 0) repeat ($urandom_range(20)) @(posedge clk);
        end
        sent_all = 1;
    end

    always @(posedge clk) m_ready <= ($urandom_range(99) >= OSTALL);

    // checker
    initial errors = 0;
    always @(posedge clk) if (!rst && m_valid && m_ready) begin
        if (exp_last.size() == 0) begin
            if (errors < 5) $display("%m EXTRA output beat");
            errors++;
        end else begin
            bit el = exp_last.pop_front();
            for (int oc = 0; oc < OC; oc++) begin
                longint e = exp_q.pop_front();
                if (longint'(m_data[oc]) != e) begin
                    if (errors < 5) $display("%m MISMATCH pos %0d oc %0d: got %0d exp %0d", n_got, oc, m_data[oc], e);
                    errors++;
                end
            end
            if (m_last !== el) begin
                if (errors < 5) $display("%m TLAST mismatch at pos %0d: got %b exp %b", n_got, m_last, el);
                errors++;
            end
        end
        n_got++;
    end

    always @(posedge clk) if (sent_all && n_got == n_exp && !done) begin
        repeat (60) @(posedge clk);                 // catch late extra beats
        done = 1;
    end
endmodule

module tb_conv1d_unit;
    logic clk = 0, rst = 1;
    always #2.5 clk = ~clk;
    initial begin repeat (5) @(posedge clk); rst <= 0; end

    localparam int N = 16;
    logic done [N];
    int   errs [N];

    // IC OC K STRIDE AW DW SIGNED WW LAST DSP FOLD PACK: shapes of the exported models plus odd corners
    // (K=1, K=3 with STRIDE=3, odd widths, DW = AW and DW < AW, one- and two-stage LUT products,
    // FOLD 1/2/3 incl. NT not a multiple of FOLD, packed DSPs with even and odd OC). Each shape runs
    // with LUT and DSP multipliers.
    `define UT(i, ic, oc, k, s, aw, dw, sg, ww, last, dsp, fold, pk, ist, ost) \
        ut_conv1d #(.IC(ic), .OC(oc), .K(k), .STRIDE(s), .AW(aw), .DW(dw), .IN_SIGNED(sg), .WW(ww), .LAST(last), .USE_DSP(dsp), \
                    .FOLD(fold), .PACK(pk), .ISTALL(ist), .OSTALL(ost), .SEED(100 + i)) u_``i (.clk, .rst, .done(done[i]), .errors(errs[i]));
    `UT(0,  1, 3,  9, 4, 7, 6, 1, 6, 0, 0, 1, 0,  0,  0)
    `UT(1,  3, 3,  9, 1, 7, 6, 0, 6, 0, 0, 1, 0, 30, 30)
    `UT(2,  3, 4,  9, 2, 7, 6, 0, 6, 1, 0, 2, 0, 30, 60)
    `UT(3,  1, 5,  9, 8, 9, 9, 1, 8, 0, 0, 1, 0, 60, 30)
    `UT(4,  5, 8,  9, 2, 9, 8, 0, 8, 1, 0, 2, 0, 10, 10)
    `UT(5,  3, 3, 15, 1, 7, 6, 0, 6, 0, 0, 2, 0, 30, 30)
    `UT(6,  2, 2,  1, 1, 8, 8, 1, 8, 0, 0, 1, 0, 30, 30)
    `UT(7,  2, 3,  3, 3, 8, 7, 0, 5, 1, 0, 3, 0, 50, 50)
    `UT(8,  1, 3,  9, 4, 7, 6, 1, 6, 0, 1, 1, 0, 30, 30)
    `UT(9,  3, 3,  9, 1, 7, 6, 0, 6, 0, 1, 1, 0,  0,  0)
    `UT(10, 3, 4,  9, 2, 7, 6, 0, 6, 1, 1, 2, 1, 60, 30)
    `UT(11, 1, 5,  9, 8, 9, 9, 1, 8, 0, 1, 1, 0, 30, 60)
    `UT(12, 5, 8,  9, 2, 9, 8, 0, 8, 1, 1, 2, 1, 30, 30)
    `UT(13, 3, 3, 15, 1, 7, 6, 0, 6, 0, 1, 2, 1, 10, 10)
    `UT(14, 2, 2,  1, 1, 8, 8, 1, 8, 0, 1, 1, 0, 50, 50)
    `UT(15, 2, 3,  3, 3, 8, 7, 0, 5, 1, 1, 3, 1, 30, 30)

    initial begin
        int total;
        fork
            begin
                for (int i = 0; i < N; i++) wait (done[i] === 1'b1);
            end
            begin
                #20ms;
                $display("TIMEOUT");
                for (int i = 0; i < N; i++) if (done[i] !== 1'b1) $display("  instance %0d not done", i);
            end
        join_any
        total = 0;
        for (int i = 0; i < N; i++) begin
            if (done[i] !== 1'b1) total++;
            total += errs[i];
        end
        if (total == 0) $display("PASS: all %0d conv1d_stream configurations bit-exact", N);
        else            $display("FAIL: %0d errors", total);
        $finish;
    end
endmodule
