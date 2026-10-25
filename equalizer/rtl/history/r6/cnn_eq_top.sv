// cnn_eq_top.sv - CNN equalizer with AXI-Lite parameters/control and AXI-Stream data.
// Register map and parameter layout: rtl/WEIGHT_FORMAT.md.
`timescale 1ns/1ps
module cnn_eq_top
    import cnn_eq_pkg::*;
#(
    parameter bit USE_DSP = 0     // conv multipliers in DSP48 (1) or LUTs (0)
) (
    input  logic        aclk,
    input  logic        aresetn,
    // AXI-Lite slave (32-bit)
    input  logic [15:0] s_axil_awaddr,
    input  logic        s_axil_awvalid,
    output logic        s_axil_awready,
    input  logic [31:0] s_axil_wdata,
    input  logic [3:0]  s_axil_wstrb,
    input  logic        s_axil_wvalid,
    output logic        s_axil_wready,
    output logic [1:0]  s_axil_bresp,
    output logic        s_axil_bvalid,
    input  logic        s_axil_bready,
    input  logic [15:0] s_axil_araddr,
    input  logic        s_axil_arvalid,
    output logic        s_axil_arready,
    output logic [31:0] s_axil_rdata,
    output logic [1:0]  s_axil_rresp,
    output logic        s_axil_rvalid,
    input  logic        s_axil_rready,
    // AXI-Stream slave: input samples
    input  logic [7:0]  s_axis_tdata,
    input  logic        s_axis_tvalid,
    output logic        s_axis_tready,
    input  logic        s_axis_tlast,
    // AXI-Stream master: output symbols
    output logic [15:0] m_axis_tdata,
    output logic        m_axis_tvalid,
    input  logic        m_axis_tready,
    output logic        m_axis_tlast
);
    localparam logic [31:0] ID = 32'h4E45_5131;  // "NEQ1"
    wire rst = !aresetn;

    // ---------------------------------------------------------- AXI-Lite write
    logic [31:0] pmem [N_PARAM];
    logic [31:0] ctrl;
    logic        aw_hs, w_hs;
    logic [15:0] awaddr_q;
    logic [31:0] wdata_q;
    logic        have_aw, have_w;

    assign s_axil_awready = !have_aw && !s_axil_bvalid;
    assign s_axil_wready  = !have_w  && !s_axil_bvalid;
    assign s_axil_bresp   = 2'b00;

    always_ff @(posedge aclk) begin
        if (rst) begin
            have_aw <= 1'b0;
            have_w  <= 1'b0;
            s_axil_bvalid <= 1'b0;
            ctrl <= '0;
        end else begin
            if (s_axil_awvalid && s_axil_awready) begin awaddr_q <= s_axil_awaddr; have_aw <= 1'b1; end
            if (s_axil_wvalid && s_axil_wready)   begin wdata_q  <= s_axil_wdata;  have_w  <= 1'b1; end
            if (have_aw && have_w) begin
                if (awaddr_q[15:14] == 2'b01) begin
                    if (awaddr_q[13:2] < N_PARAM) pmem[awaddr_q[13:2]] <= wdata_q;
                end else if (awaddr_q == 16'h000C) begin
                    ctrl <= wdata_q;
                end
                have_aw <= 1'b0;
                have_w  <= 1'b0;
                s_axil_bvalid <= 1'b1;
            end
            if (s_axil_bvalid && s_axil_bready) s_axil_bvalid <= 1'b0;
        end
    end

    // -------------------------------------------------------------- datapath
    logic signed [15:0] core_data;
    cnn_eq_core #(.USE_DSP(USE_DSP)) u_core (
        .clk(aclk), .rst(rst || ctrl[0]), .pmem,
        .s_valid(s_axis_tvalid), .s_ready(s_axis_tready), .s_data(s_axis_tdata[B_IN-1:0]), .s_last(s_axis_tlast),
        .m_valid(m_axis_tvalid), .m_ready(m_axis_tready), .m_data(core_data), .m_last(m_axis_tlast));
    assign m_axis_tdata = core_data;

    // -------------------------------------------------------------- counters
    logic [31:0] frames_in, frames_out, busy_cyc, in_beats, out_beats;
    always_ff @(posedge aclk) begin
        if (rst || ctrl[0]) begin
            frames_in <= '0; frames_out <= '0; busy_cyc <= '0; in_beats <= '0; out_beats <= '0;
        end else begin
            if (s_axis_tvalid && s_axis_tready) begin
                in_beats <= in_beats + 1'b1;
                if (s_axis_tlast) frames_in <= frames_in + 1'b1;
            end
            if (m_axis_tvalid && m_axis_tready) begin
                out_beats <= out_beats + 1'b1;
                if (m_axis_tlast) frames_out <= frames_out + 1'b1;
            end
            if (frames_in != frames_out || (s_axis_tvalid && s_axis_tready)) busy_cyc <= busy_cyc + 1'b1;
        end
    end

    // ----------------------------------------------------------- AXI-Lite read
    assign s_axil_arready = !s_axil_rvalid;
    assign s_axil_rresp   = 2'b00;
    always_ff @(posedge aclk) begin
        if (rst) begin
            s_axil_rvalid <= 1'b0;
        end else if (s_axil_arvalid && s_axil_arready) begin
            s_axil_rvalid <= 1'b1;
            case (s_axil_araddr)
                16'h0000: s_axil_rdata <= ID;
                16'h0004: s_axil_rdata <= {8'(L), 8'(K), 8'(C), 8'(VP)};
                16'h0008: s_axil_rdata <= N_PARAM;
                16'h000C: s_axil_rdata <= ctrl;
                16'h0010: s_axil_rdata <= frames_out;
                16'h0014: s_axil_rdata <= busy_cyc;
                16'h0018: s_axil_rdata <= in_beats;
                16'h001C: s_axil_rdata <= out_beats;
                default:  s_axil_rdata <= '0;
            endcase
        end else if (s_axil_rvalid && s_axil_rready) begin
            s_axil_rvalid <= 1'b0;
        end
    end
endmodule
