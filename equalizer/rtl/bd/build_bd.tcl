# build_bd.tcl - PYNQ-Z2 system: Zynq PS + AXI DMA + CNN equalizer, synthesised and implemented
# in context (timing with the PS, DMA and interconnect around the core).
# Usage (from rtl/bd): vivado -mode batch -source build_bd.tcl -tclargs <model> [fclk_mhz 200] [use_dsp 1] [tag] [dma_mhz 100]
#   fclk_mhz: equalizer clock (FCLK1); dma_mhz: DMA / interconnect / HP0 clock (FCLK0).
#   Board files: C:/FPGA_boards (pynq-z2/A.0).
# Output: rtl/bd/proj_<model>_<fclk>_dsp<d>[_<tag>]/ (project, bitstream, .hwh) and reports in its rpt/ folder.
set model   [lindex $argv 0]
set fclk    [expr {[llength $argv] > 1 ? [lindex $argv 1] : 200}]
set use_dsp [expr {[llength $argv] > 2 ? [lindex $argv 2] : 1}]
set tag     [expr {[llength $argv] > 3 && [lindex $argv 3] ne "" ? "_[lindex $argv 3]" : ""}]
set dma_mhz [expr {[llength $argv] > 4 ? [lindex $argv 4] : 100}]
set here    [file dirname [file normalize [info script]]]
set rtl     [file dirname $here]
set name    "proj_${model}_${fclk}_dsp${use_dsp}${tag}"
set pdir    [file join $here $name]
set rdir    [file join $pdir rpt]

set_param board.repoPaths [list C:/FPGA_boards]
create_project -force $name $pdir -part xc7z020clg400-1
set_property board_part tul.com.tw:pynq-z2:part0:1.0 [current_project]
file mkdir $rdir

add_files -norecurse [list \
    [file join $rtl gen $model cnn_eq_pkg.sv] \
    [file join $rtl src sync_fifo.sv] \
    [file join $rtl src add_tree.sv] \
    [file join $rtl src dfe_stream.sv] \
    [file join $rtl src conv1d_stream.sv] \
    [file join $rtl src cnn_eq_core.sv] \
    [file join $rtl src cnn_eq_top.sv] \
    [file join $here cnn_eq_axi.v]]
update_compile_order -fileset sources_1

create_bd_design "system"
# PS with the PYNQ-Z2 preset; FCLK0 drives everything in the PL; HP0 for the DMA
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 ps7]
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 -config {make_external "FIXED_IO, DDR" apply_board_preset "1"} $ps
# two clock domains: FCLK0 (dma_mhz) for the DMA / interconnect / HP0, FCLK1 (fclk) for the equalizer
set_property -dict [list CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ $dma_mhz CONFIG.PCW_EN_CLK1_PORT {1} \
    CONFIG.PCW_FPGA1_PERIPHERAL_FREQMHZ $fclk CONFIG.PCW_USE_S_AXI_HP0 {1} CONFIG.PCW_S_AXI_HP0_DATA_WIDTH {64}] $ps

set rst_eq [create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 rst_eq]
connect_bd_net [get_bd_pins ps7/FCLK_CLK1] [get_bd_pins rst_eq/slowest_sync_clk]
connect_bd_net [get_bd_pins ps7/FCLK_RESET0_N] [get_bd_pins rst_eq/ext_reset_in]

set eq [create_bd_cell -type module -reference cnn_eq_axi eq]
set_property CONFIG.USE_DSP $use_dsp $eq
connect_bd_net [get_bd_pins ps7/FCLK_CLK1] [get_bd_pins eq/aclk]
connect_bd_net [get_bd_pins rst_eq/peripheral_aresetn] [get_bd_pins eq/aresetn]

# DMA moves 32-bit words (4 input samples / 2 output symbols) over a 64-bit memory port (= HP0 width)
set dma [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1 dma]
set_property -dict [list CONFIG.c_include_sg {0} CONFIG.c_sg_length_width {23} \
    CONFIG.c_m_axi_mm2s_data_width {64} CONFIG.c_m_axis_mm2s_tdata_width {32} \
    CONFIG.c_m_axi_s2mm_data_width {64} CONFIG.c_s_axis_s2mm_tdata_width {32} \
    CONFIG.c_mm2s_burst_size {64} CONFIG.c_s2mm_burst_size {64}] $dma

# control: PS GP0 -> DMA lite (FCLK0) + equalizer AXI-Lite (FCLK1, clock crossing in the interconnect)
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list Clk_master Auto Clk_slave Auto Clk_xbar Auto \
    Master /ps7/M_AXI_GP0 Slave /dma/S_AXI_LITE intc_ip Auto master_apm 0] [get_bd_intf_pins dma/S_AXI_LITE]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list Clk_master Auto Clk_slave Auto Clk_xbar Auto \
    Master /ps7/M_AXI_GP0 Slave /eq/s_axil intc_ip Auto master_apm 0] [get_bd_intf_pins eq/s_axil]
# data: DMA masters -> HP0 (FCLK0)
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list Clk_master Auto Clk_slave Auto Clk_xbar Auto \
    Master /dma/M_AXI_MM2S Slave /ps7/S_AXI_HP0 intc_ip Auto master_apm 0] [get_bd_intf_pins ps7/S_AXI_HP0]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list Clk_master Auto Clk_slave Auto Clk_xbar Auto \
    Master /dma/M_AXI_S2MM Slave /ps7/S_AXI_HP0 intc_ip Auto master_apm 0] [get_bd_intf_pins dma/M_AXI_S2MM]

# streams: DMA (32 b, FCLK0) <-> clock converter <-> width converter <-> equalizer (8 b in / 16 b out, FCLK1)
set rst_dma [get_bd_pins -of_objects [get_bd_cells -filter {VLNV =~ "*proc_sys_reset*" && NAME != "rst_eq"}] -filter {NAME == peripheral_aresetn}]
set cc_in  [create_bd_cell -type ip -vlnv xilinx.com:ip:axis_clock_converter:1.1 cc_in]
set dw_in  [create_bd_cell -type ip -vlnv xilinx.com:ip:axis_dwidth_converter:1.1 dw_in]
set dw_out [create_bd_cell -type ip -vlnv xilinx.com:ip:axis_dwidth_converter:1.1 dw_out]
set cc_out [create_bd_cell -type ip -vlnv xilinx.com:ip:axis_clock_converter:1.1 cc_out]
set_property CONFIG.M_TDATA_NUM_BYTES {1} $dw_in
set_property CONFIG.M_TDATA_NUM_BYTES {4} $dw_out
connect_bd_intf_net [get_bd_intf_pins dma/M_AXIS_MM2S] [get_bd_intf_pins cc_in/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins cc_in/M_AXIS]    [get_bd_intf_pins dw_in/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins dw_in/M_AXIS]    [get_bd_intf_pins eq/s_axis]
connect_bd_intf_net [get_bd_intf_pins eq/m_axis]       [get_bd_intf_pins dw_out/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins dw_out/M_AXIS]   [get_bd_intf_pins cc_out/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins cc_out/M_AXIS]   [get_bd_intf_pins dma/S_AXIS_S2MM]
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins cc_in/s_axis_aclk] [get_bd_pins cc_out/m_axis_aclk]
connect_bd_net [lindex $rst_dma 0]         [get_bd_pins cc_in/s_axis_aresetn] [get_bd_pins cc_out/m_axis_aresetn]
connect_bd_net [get_bd_pins ps7/FCLK_CLK1] [get_bd_pins cc_in/m_axis_aclk] [get_bd_pins cc_out/s_axis_aclk] \
    [get_bd_pins dw_in/aclk] [get_bd_pins dw_out/aclk]
connect_bd_net [get_bd_pins rst_eq/peripheral_aresetn] [get_bd_pins cc_in/m_axis_aresetn] [get_bd_pins cc_out/s_axis_aresetn] \
    [get_bd_pins dw_in/aresetn] [get_bd_pins dw_out/aresetn]

assign_bd_address
validate_bd_design
save_bd_design
# one global synthesis instead of a separate out-of-context run per IP: on an 8 GB machine
# parallel per-IP runs (~1.6 GB each) die silently in synth_design
set_property synth_checkpoint_mode None [get_files system.bd]
make_wrapper -files [get_files system.bd] -top
add_files -norecurse [file join $pdir $name.gen sources_1 bd system hdl system_wrapper.v]
set_property top system_wrapper [current_fileset]
update_compile_order -fileset sources_1

set_property strategy Performance_ExplorePostRoutePhysOpt [get_runs impl_1]
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
open_run impl_1
report_utilization -file [file join $rdir util.rpt]
report_utilization -hierarchical -hierarchical_depth 3 -file [file join $rdir util_hier.rpt]
report_timing_summary -max_paths 10 -file [file join $rdir timing.rpt]
report_power -file [file join $rdir power.rpt]

# PYNQ overlay files: <name>.bit + <name>.hwh
set bit [glob -nocomplain [file join $pdir $name.runs impl_1 *.bit]]
set hwh [glob -nocomplain [file join $pdir $name.gen sources_1 bd system hw_handoff system.hwh]]
set ov  [file join $pdir overlay]
file mkdir $ov
if {[llength $bit]} { file copy -force [lindex $bit 0] [file join $ov cnn_eq.bit] }
if {[llength $hwh]} { file copy -force [lindex $hwh 0] [file join $ov cnn_eq.hwh] }

set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set fh [open [file join $rdir summary.txt] w]
puts $fh "model $model fclk_MHz $fclk dma_MHz $dma_mhz use_dsp $use_dsp WNS_ns $wns bit [llength $bit] hwh [llength $hwh]"
close $fh
puts "SUMMARY bd model $model fclk $fclk dma $dma_mhz use_dsp $use_dsp WNS $wns ns"
