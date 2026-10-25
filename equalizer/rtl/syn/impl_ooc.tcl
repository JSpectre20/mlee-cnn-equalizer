# impl_ooc.tcl - out-of-context synthesis + place & route of cnn_eq_top for one model.
# Usage: vivado -mode batch -source rtl/syn/impl_ooc.tcl -tclargs <model> <clock_period_ns> [use_dsp 0|1] [part]
set model   [lindex $argv 0]
set period  [lindex $argv 1]
set use_dsp [expr {[llength $argv] > 2 ? [lindex $argv 2] : 0}]
set part    [expr {[llength $argv] > 3 ? [lindex $argv 3] : "xc7z020clg400-1"}]
set here    [file dirname [file normalize [info script]]]
set rtl     [file dirname $here]
set out     [file join $here "out_${model}_${period}ns_dsp${use_dsp}"]
file mkdir $out

read_verilog -sv [list \
    [file join $rtl gen $model cnn_eq_pkg.sv] \
    [file join $rtl src sync_fifo.sv] \
    [file join $rtl src add_tree.sv] \
    [file join $rtl src dfe_stream.sv] \
    [file join $rtl src conv1d_stream.sv] \
    [file join $rtl src cnn_eq_core.sv] \
    [file join $rtl src cnn_eq_top.sv]]

synth_design -top cnn_eq_top -part $part -mode out_of_context -flatten_hierarchy rebuilt -generic USE_DSP=$use_dsp
create_clock -name aclk -period $period [get_ports aclk]
report_utilization -file [file join $out synth_util.rpt]

opt_design
place_design
phys_opt_design
route_design

report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 4 -file [file join $out util_hier.rpt]
report_timing_summary -max_paths 10 -file [file join $out timing.rpt]
report_power -file [file join $out power.rpt]
write_checkpoint -force [file join $out routed.dcp]

set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set fmax [expr {1000.0 / ($period - $wns)}]
set fh [open [file join $out summary.txt] w]
puts $fh "model $model part $part use_dsp $use_dsp period_ns $period WNS_ns $wns fmax_MHz [format %.1f $fmax]"
close $fh
puts "SUMMARY model $model use_dsp $use_dsp WNS $wns ns -> Fmax [format %.1f $fmax] MHz"
