// cnn_eq_core.sv - chain of conv1d_stream layers + symbol serializer.
//
// Shape and widths come from package cnn_eq_pkg (rtl/gen/<model>/cnn_eq_pkg.sv),
// generated per model by scripts/export_rtl.py. Parameters are read from the
// flat parameter memory `pmem` using the offsets in that package
// (layout: scripts/export_rtl.py, build_param_image).
`timescale 1ns/1ps
module cnn_eq_core
    import cnn_eq_pkg::*;
#(
    parameter bit USE_DSP = 0     // conv multipliers in DSP48 (1) or LUTs (0)
) (
    input  logic clk,
    input  logic rst,
    input  logic [31:0] pmem [N_PARAM],
    // input samples (signed B_IN-bit codes), tlast on the last sample of a frame
    input  logic                    s_valid,
    output logic                    s_ready,
    input  logic signed [B_IN-1:0]  s_data,
    input  logic                    s_last,
    // output symbols: z (or u = z + decision feedback when N_FB > 0) saturated to signed 16 bits,
    // decision bit = (m_data > 0)
    output logic                    m_valid,
    input  logic                    m_ready,
    output logic signed [15:0]      m_data,
    output logic                    m_last
);
    localparam int AW = (B_IN > B_A + 1) ? B_IN : B_A + 1;   // activation container width

    // At 1 input sample per clock, layer l starts a job every prod(STRIDE_L[0..l]) cycles.
    // The engine needs (channel groups) x FOLD cycles per job, so the largest FOLD that fits
    // shares each multiplier over FOLD parts of the window (ceil(IC*K/FOLD) multipliers).
    // DSP builds additionally pack two output channels per DSP (groups = ceil(OC/2)) when the
    // packed operands fit the DSP48E1 ports and it saves DSPs.
    function automatic int fold_of(input int l, input int oc, input bit pack);
        int cpj = 1;
        int ng  = pack ? (oc + 1) / 2 : oc;
        for (int i = 0; i <= l; i++) cpj *= STRIDE_L[i];
        return (cpj / ng < 1) ? 1 : cpj / ng;
    endfunction
    function automatic bit pack_of(input int l, input int oc, input int nt, input int dw);
        int fp = fold_of(l, oc, 1'b1);
        int fu = fold_of(l, oc, 1'b0);
        return USE_DSP && fp >= 2 && (2 * B_W + dw + 1 <= 25) && (dw + 1 <= 18) &&
               ((nt + fp - 1) / fp < (nt + fu - 1) / fu);
    endfunction

    // inter-layer streams: stage l is the input of layer l
    logic                 st_valid [L];
    logic                 st_ready [L];
    logic                 st_last  [L];
    logic signed [AW-1:0] st_data  [L][C];

    assign st_valid[0]   = s_valid;
    assign s_ready       = st_ready[0];
    assign st_last[0]    = s_last;
    assign st_data[0][0] = AW'(s_data);
    for (genvar c = 1; c < C; c++) begin : g_pad0
        assign st_data[0][c] = '0;
    end

    // ----------------------------------------------------------- hidden layers
    for (genvar l = 0; l < L - 1; l++) begin : g_layer
        localparam int IC_L = (l == 0) ? 1 : C;
        localparam bit PK_L = pack_of(l, C, IC_L * K, (l == 0) ? B_IN : B_A);
        logic signed [B_W-1:0]   w_l    [C][IC_L * K];
        logic signed [ACC_W-1:0] bias_l [C];
        logic [15:0]             mul_l  [C];
        logic [5:0]              shf_l  [C];
        logic signed [AW-1:0]    sd     [IC_L];
        logic signed [AW-1:0]    md     [C];
        always_comb begin
            for (int oc = 0; oc < C; oc++) begin
                for (int n = 0; n < IC_L * K; n++) w_l[oc][n] = pmem[W_OFF[l] + oc * IC_L * K + n][B_W-1:0];
                bias_l[oc] = pmem[B_OFF[l] + oc][ACC_W-1:0];
                mul_l[oc]  = pmem[M_OFF[l] + oc][15:0];
                shf_l[oc]  = pmem[S_OFF[l] + oc][5:0];
            end
            for (int ic = 0; ic < IC_L; ic++) sd[ic] = st_data[l][ic];
        end
        conv1d_stream #(
            .IC(IC_L), .OC(C), .K(K), .STRIDE(STRIDE_L[l]), .AW(AW),
            .DW((l == 0) ? B_IN : B_A), .IN_SIGNED(l == 0), .WW(B_W),   // ADC codes signed, activations unsigned
            .ACC_W(ACC_W), .BA(B_A), .LAST(1'b0), .USE_DSP(USE_DSP),
            .PACK(PK_L), .FOLD(fold_of(l, C, PK_L))
        ) u_conv (
            .clk, .rst, .w(w_l), .bias(bias_l), .mul(mul_l), .shf(shf_l),
            .s_valid(st_valid[l]), .s_ready(st_ready[l]), .s_data(sd), .s_last(st_last[l]),
            .m_valid(st_valid[l + 1]), .m_ready(st_ready[l + 1]), .m_data(md), .m_last(st_last[l + 1]));
        assign st_data[l + 1] = md;
    end

    // -------------------------------------------------------------- last layer
    localparam bit PK_O = pack_of(L - 1, VP, C * K, B_A);
    logic signed [B_W-1:0]   w_o    [VP][C * K];
    logic signed [ACC_W-1:0] bias_o [VP];
    logic [15:0]             mul_o  [VP];
    logic [5:0]              shf_o  [VP];
    logic signed [AW-1:0]    sd_o   [C];
    logic signed [ACC_W-1:0] z      [VP];
    logic                    z_valid, z_ready, z_last;
    always_comb begin
        for (int oc = 0; oc < VP; oc++) begin
            for (int n = 0; n < C * K; n++) w_o[oc][n] = pmem[W_OFF[L-1] + oc * C * K + n][B_W-1:0];
            bias_o[oc] = pmem[B_OFF[L-1] + oc][ACC_W-1:0];
            mul_o[oc]  = '0;
            shf_o[oc]  = '0;
        end
        for (int ic = 0; ic < C; ic++) sd_o[ic] = st_data[L-1][ic];
    end
    conv1d_stream #(
        .IC(C), .OC(VP), .K(K), .STRIDE(STRIDE_L[L-1]), .AW(AW),
        .DW(B_A), .IN_SIGNED(1'b0), .WW(B_W),
        .ACC_W(ACC_W), .BA(B_A), .LAST(1'b1), .USE_DSP(USE_DSP),
        .PACK(PK_O), .FOLD(fold_of(L - 1, VP, PK_O))
    ) u_last (
        .clk, .rst, .w(w_o), .bias(bias_o), .mul(mul_o), .shf(shf_o),
        .s_valid(st_valid[L-1]), .s_ready(st_ready[L-1]), .s_data(sd_o), .s_last(st_last[L-1]),
        .m_valid(z_valid), .m_ready(z_ready), .m_data(z), .m_last(z_last));

    // --------------------------------------------------------------- serializer
    localparam int VW = (VP > 1) ? $clog2(VP) : 1;
    logic [VW-1:0] v;
    logic signed [ACC_W-1:0] zv;
    logic ser_valid, ser_ready, ser_last;
    assign zv        = z[v];
    assign ser_valid = z_valid;
    assign ser_last  = z_last && (v == VW'(VP - 1));
    assign z_ready   = ser_ready && (v == VW'(VP - 1));
    always_ff @(posedge clk) begin
        if (rst) v <= '0;
        else if (ser_valid && ser_ready) v <= (v == VW'(VP - 1)) ? '0 : v + 1'b1;
    end

    // ------------------------------------------- decision feedback (N_FB > 0) + saturation
    function automatic logic signed [15:0] sat16(input logic signed [63:0] x);
        return (x > 64'sd32767) ? 16'sh7FFF : (x < -64'sd32768) ? 16'sh8000 : x[15:0];
    endfunction
    if (N_FB > 0) begin : g_dfe
        logic signed [ACC_W-1:0] fb [VP][N_FB];
        always_comb
            for (int vv = 0; vv < VP; vv++)
                for (int k = 0; k < N_FB; k++) fb[vv][k] = pmem[FB_OFF + vv * N_FB + k][ACC_W-1:0];
        localparam int UW = ACC_W + N_FB;
        logic signed [UW-1:0] u;
        dfe_stream #(.VP(VP), .N_FB(N_FB), .ZW(ACC_W), .FW(ACC_W)) u_dfe (
            .clk, .rst, .fb,
            .s_valid(ser_valid), .s_ready(ser_ready), .s_z(zv), .s_lane(v), .s_last(ser_last),
            .m_valid, .m_ready, .m_u(u), .m_last);
        assign m_data = sat16(64'(u));
    end else begin : g_nodfe
        assign m_valid   = ser_valid;
        assign ser_ready = m_ready;
        assign m_last    = ser_last;
        assign m_data    = sat16(64'(zv));
    end
endmodule
