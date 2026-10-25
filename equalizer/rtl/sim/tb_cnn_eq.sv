// tb_cnn_eq.sv - self-checking test bench for cnn_eq_top.
//
// 1. Loads params.mem into the parameter memory over AXI-Lite and checks ID/SHAPE.
// 2. Streams TB_FRAMES frames from test_in.mem (TLAST at each frame end).
// 3. Compares every output beat with test_out.mem (bit-exact vs eqsim IntegerModel)
//    and checks TLAST positions and the frame counter.
// Data files (params.mem, test_in.mem, test_out.mem) are read from the run directory.
// Plusarg: +stall<0..90>  percent of cycles with TVALID/TREADY low (no '=': the
// Windows .bat wrappers of xsim split arguments at '=').
`timescale 1ns/1ps
module tb_cnn_eq;
    import cnn_eq_pkg::*;
    `include "tb_cfg.svh"
    `include "tb_dsp.svh"   // localparam bit USE_DSP (+ optional `define NETLIST / TB_HALF_NS), written by the run script
`ifndef TB_HALF_NS
    `define TB_HALF_NS 5    // 100 MHz; the power runs use 2.5 (200 MHz)
`endif

    localparam int N_IN  = TB_FRAMES * TB_FRAME_SAMPLES;
    localparam int N_OUT = TB_FRAMES * TB_FRAME_SYM;

    logic aclk = 0, aresetn = 0;
    always #(`TB_HALF_NS) aclk = ~aclk;

    logic [15:0] awaddr, araddr;
    logic awvalid, awready, wvalid, wready, bvalid, bready, arvalid, arready, rvalid, rready;
    logic [31:0] wdata, rdata;
    logic [1:0] bresp, rresp;
    logic [7:0] s_tdata;
    logic s_tvalid, s_tready, s_tlast;
    logic [15:0] m_tdata;
    logic m_tvalid, m_tready, m_tlast;

`ifdef NETLIST   // post-route functional netlist (no parameters, no RTL hierarchy)
    cnn_eq_top dut (
`else
    cnn_eq_top #(.USE_DSP(USE_DSP)) dut (
`endif
        .aclk, .aresetn,
        .s_axil_awaddr(awaddr), .s_axil_awvalid(awvalid), .s_axil_awready(awready),
        .s_axil_wdata(wdata), .s_axil_wstrb(4'hF), .s_axil_wvalid(wvalid), .s_axil_wready(wready),
        .s_axil_bresp(bresp), .s_axil_bvalid(bvalid), .s_axil_bready(bready),
        .s_axil_araddr(araddr), .s_axil_arvalid(arvalid), .s_axil_arready(arready),
        .s_axil_rdata(rdata), .s_axil_rresp(rresp), .s_axil_rvalid(rvalid), .s_axil_rready(rready),
        .s_axis_tdata(s_tdata), .s_axis_tvalid(s_tvalid), .s_axis_tready(s_tready), .s_axis_tlast(s_tlast),
        .m_axis_tdata(m_tdata), .m_axis_tvalid(m_tvalid), .m_axis_tready(m_tready), .m_axis_tlast(m_tlast));

    logic [31:0] params [N_PARAM];
    logic [7:0]  vin  [N_IN];
    logic [15:0] vout [N_OUT];
    int stall;

    task automatic axil_write(input logic [15:0] a, input logic [31:0] d);
        @(posedge aclk);
        awaddr <= a; awvalid <= 1; wdata <= d; wvalid <= 1; bready <= 1;
        fork
            begin do @(posedge aclk); while (!awready); awvalid <= 0; end
            begin do @(posedge aclk); while (!wready);  wvalid  <= 0; end
        join
        do @(posedge aclk); while (!bvalid);
        bready <= 0;
    endtask

    task automatic axil_read(input logic [15:0] a, output logic [31:0] d);
        @(posedge aclk);
        araddr <= a; arvalid <= 1; rready <= 1;
        do @(posedge aclk); while (!arready);
        arvalid <= 0;
        while (!rvalid) @(posedge aclk);
        d = rdata;
        @(posedge aclk);
        rready <= 0;
    endtask

    int n_sent = 0, n_recv = 0, n_err = 0, n_last_err = 0;
    longint t_first_in = -1, t_last_out = -1, cyc = 0;
    always @(posedge aclk) cyc++;

    // source
    initial begin : source
        s_tvalid = 0; s_tlast = 0; s_tdata = 0;
        wait (aresetn);
        @(posedge aclk);
        wait (s_tready !== 1'bx);
        #1;
        wait (tb_cnn_eq.params_loaded);
        while (n_sent < N_IN) begin
            if (stall == 0 || $urandom_range(99) >= stall) begin
                s_tvalid <= 1;
                s_tdata  <= vin[n_sent];
                s_tlast  <= ((n_sent + 1) % TB_FRAME_SAMPLES) == 0;
                @(posedge aclk);
                if (s_tready) begin
                    if (t_first_in < 0) t_first_in = cyc;
                    n_sent++;
`ifdef NETLIST
                    if (n_sent % 256 == 0) $display("progress: %0d / %0d samples sent, %0d outputs (t = %0t)", n_sent, N_IN, n_recv, $time);
`endif
                end
            end else begin
                s_tvalid <= 0;
                @(posedge aclk);
            end
        end
        s_tvalid <= 0;
    end

    // sink
    always @(posedge aclk) begin
        if (!aresetn) m_tready <= 0;
        else m_tready <= (stall == 0) || ($urandom_range(99) >= stall);
        if (aresetn && m_tvalid && m_tready) begin
            if (n_recv < N_OUT) begin
                if (m_tdata !== vout[n_recv]) begin
                    n_err++;
                    if (n_err <= 10) $display("MISMATCH out[%0d]: got %h expected %h", n_recv, m_tdata, vout[n_recv]);
                end
                if (m_tlast !== (((n_recv + 1) % TB_FRAME_SYM) == 0)) n_last_err++;
            end else begin
                n_err++;
                $display("EXTRA output beat %0d", n_recv);
            end
            n_recv++;
            t_last_out = cyc;
        end
    end

    logic params_loaded = 0;
    initial begin
        logic [31:0] r;
        if (!$value$plusargs("stall%d", stall)) stall = 0;
        $readmemh("params.mem", params);
        $readmemh("test_in.mem", vin);
        $readmemh("test_out.mem", vout);
        awvalid = 0; wvalid = 0; bready = 0; arvalid = 0; rready = 0;
        repeat (10) @(posedge aclk);
`ifdef NETLIST
        wait (glbl.GSR === 1'b0);    // netlist flip-flops ignore their inputs during the 100 ns global set/reset
        repeat (10) @(posedge aclk);
`endif
        aresetn = 1;
        repeat (5) @(posedge aclk);
        axil_read(16'h0000, r);
        if (r !== 32'h4E455131) $fatal(1, "bad ID %h", r);
        axil_read(16'h0004, r);
        if (r !== {8'(L), 8'(K), 8'(C), 8'(VP)}) $fatal(1, "bad SHAPE %h", r);
        for (int i = 0; i < N_PARAM; i++) axil_write(16'h4000 + 16'(4 * i), params[i]);
        params_loaded = 1;
        $display("loaded %0d parameter words; streaming %0d frames x %0d samples, stall=%0d%%", N_PARAM, TB_FRAMES, TB_FRAME_SAMPLES, stall);
        fork
            wait (n_recv >= N_OUT);
            begin
                repeat (200 * N_IN + 10000) @(posedge aclk);
                $display("TIMEOUT: received %0d of %0d, sent %0d", n_recv, N_OUT, n_sent);
`ifndef NETLIST
                $display("  L0: st=%0d n_in=%0d created=%0d of=%0d infl=%0d busy=%0d",
                    dut.u_core.g_layer[0].u_conv.st, dut.u_core.g_layer[0].u_conv.n_in, dut.u_core.g_layer[0].u_conv.created,
                    dut.u_core.g_layer[0].u_conv.of_count, dut.u_core.g_layer[0].u_conv.inflight, dut.u_core.g_layer[0].u_conv.busy);
                $display("  L1: st=%0d n_in=%0d created=%0d of=%0d infl=%0d busy=%0d",
                    dut.u_core.g_layer[1].u_conv.st, dut.u_core.g_layer[1].u_conv.n_in, dut.u_core.g_layer[1].u_conv.created,
                    dut.u_core.g_layer[1].u_conv.of_count, dut.u_core.g_layer[1].u_conv.inflight, dut.u_core.g_layer[1].u_conv.busy);
                $display("  LAST: st=%0d n_in=%0d created=%0d of=%0d infl=%0d busy=%0d",
                    dut.u_core.u_last.st, dut.u_core.u_last.n_in, dut.u_core.u_last.created,
                    dut.u_core.u_last.of_count, dut.u_core.u_last.inflight, dut.u_core.u_last.busy);
`endif
            end
        join_any
        repeat (50) @(posedge aclk);  // catch extra beats
        axil_read(16'h0010, r);
        if (r != TB_FRAMES) begin $display("FRAMES counter %0d != %0d", r, TB_FRAMES); n_err++; end
        $display("cycles first-in..last-out: %0d for %0d samples (%.3f samples/cycle)", t_last_out - t_first_in, N_IN,
                 real'(N_IN) / real'(t_last_out - t_first_in));
        if (n_err == 0 && n_last_err == 0 && n_recv == N_OUT)
            $display("PASS: %0d outputs bit-exact, TLAST correct", n_recv);
        else
            $display("FAIL: %0d mismatches, %0d TLAST errors, %0d/%0d outputs", n_err, n_last_err, n_recv, N_OUT);
        $finish;
    end
endmodule
