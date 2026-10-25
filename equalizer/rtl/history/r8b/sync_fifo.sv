// sync_fifo.sv - first-word-fall-through synchronous FIFO.
// dout is valid whenever !empty; pop with rd_en. count is the current occupancy.
`timescale 1ns/1ps
module sync_fifo #(
    parameter int WIDTH = 8,
    parameter int DEPTH = 4          // any value >= 2
) (
    input  logic             clk,
    input  logic             rst,
    input  logic             wr_en,
    input  logic [WIDTH-1:0] din,
    output logic             full,
    input  logic             rd_en,
    output logic [WIDTH-1:0] dout,
    output logic             empty,
    output logic [$clog2(DEPTH+1)-1:0] count
);
    localparam int AW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    logic [WIDTH-1:0] mem [DEPTH];
    logic [AW-1:0] wp, rp;

    assign full  = (count == DEPTH);
    assign empty = (count == 0);
    assign dout  = mem[rp];

    wire do_wr = wr_en && !full;
    wire do_rd = rd_en && !empty;

    always_ff @(posedge clk) begin
        if (do_wr) mem[wp] <= din;
        if (rst) begin
            wp <= '0;
            rp <= '0;
            count <= '0;
        end else begin
            if (do_wr) wp <= (wp == AW'(DEPTH - 1)) ? '0 : wp + 1'b1;
            if (do_rd) rp <= (rp == AW'(DEPTH - 1)) ? '0 : rp + 1'b1;
            count <= count + (do_wr ? 1'b1 : 1'b0) - (do_rd ? 1'b1 : 1'b0);
        end
    end
endmodule
