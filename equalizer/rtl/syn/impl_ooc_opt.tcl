# impl_ooc_opt.tcl - impl_ooc.tcl with timing-driven directives, optional retiming and a selectable
# conv1d_stream source (e.g. a snapshot from rtl/history/).
# Usage: vivado -mode batch -source rtl/syn/impl_ooc_opt.tcl -tclargs <model> <clock_period_ns> <use_dsp 0|1> [conv_src] [tag] [retime 0|1] [part]
#   conv_src  path to conv1d_stream.sv ("" or "src" = rtl/src/conv1d_stream.sv), or a directory
#             holding a full RTL snapshot (sync_fifo, conv1d_stream, cnn_eq_core, cnn_eq_top .sv)
#   tag       suffix of the output folder (default "opt")
# Flow: synth (-retiming if retime=1) -> opt Explore -> place ExtraTimingOpt -> phys_opt AggressiveExplore
#       -> route AggressiveExplore -> post-route phys_opt AggressiveExplore.
set model    [lindex $argv 0]
set period   [lindex $argv 1]
set use_dsp  [lindex $argv 2]
set conv_src [expr {[llength $argv] > 3 ? [lindex $argv 3] : ""}]
set tag      [expr {[llength $argv] > 4 ? [lindex $argv 4] : "opt"}]
set retime   [expr {[llength $argv] > 5 ? [lindex $argv 5] : 0}]
set part     [expr {[llength $argv] > 6 ? [lindex $argv 6] : "xc7z020clg400-1"}]
set here     [file dirname [file normalize [info script]]]
set rtl      [file dirname $here]
if {$conv_src eq "" || $conv_src eq "src"} { set conv_src [file join $rtl src conv1d_stream.sv] }
set conv_src [file normalize $conv_src]
set src_dir  [file join $rtl src]
if {[file isdirectory $conv_src]} {
    set src_dir  $conv_src
    set conv_src [file join $src_dir conv1d_stream.sv]
}
set out      [file join $here "out_${model}_${period}ns_dsp${use_dsp}_${tag}"]
file mkdir $out

set srcs [list [file join $rtl gen $model cnn_eq_pkg.sv] [file join $src_dir sync_fifo.sv]]
foreach extra {add_tree.sv dfe_stream.sv} {
    if {[file exists [file join $src_dir $extra]]} { lappend srcs [file join $src_dir $extra] }
}
lappend srcs $conv_src [file join $src_dir cnn_eq_core.sv] [file join $src_dir cnn_eq_top.sv]
read_verilog -sv $srcs

set synth_opts [list -top cnn_eq_top -part $part -mode out_of_context -flatten_hierarchy rebuilt -generic USE_DSP=$use_dsp]
if {$retime} { lappend synth_opts -retiming }
synth_design {*}$synth_opts
create_clock -name aclk -period $period [get_ports aclk]
report_utilization -file [file join $out synth_util.rpt]

opt_design -directive Explore
place_design -directive ExtraTimingOpt
phys_opt_design -directive AggressiveExplore
route_design -directive AggressiveExplore
if {[get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]] < 0} {
    phys_opt_design -directive AggressiveExplore
}

report_utilization -file [file join $out util.rpt]
report_utilization -hierarchical -hierarchical_depth 4 -file [file join $out util_hier.rpt]
report_timing_summary -max_paths 10 -file [file join $out timing.rpt]
report_power -file [file join $out power.rpt]
write_checkpoint -force [file join $out routed.dcp]

set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
set fmax [expr {1000.0 / ($period - $wns)}]
set fh [open [file join $out summary.txt] w]
puts $fh "model $model part $part use_dsp $use_dsp period_ns $period WNS_ns $wns fmax_MHz [format %.1f $fmax] conv_src $conv_src retime $retime flow opt"
close $fh
puts "SUMMARY model $model use_dsp $use_dsp tag $tag WNS $wns ns -> Fmax [format %.1f $fmax] MHz"
