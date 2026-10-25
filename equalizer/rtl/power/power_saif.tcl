# power_saif.tcl - power of a routed OOC build with switching activity from its netlist simulation.
# Usage: vivado -mode batch -source power_saif.tcl -tclargs <out_dir with routed.dcp> <activity.saif> <report.rpt>
set dir  [lindex $argv 0]
set saif [lindex $argv 1]
set rpt  [lindex $argv 2]
open_checkpoint [file join $dir routed.dcp]
read_saif -strip_path tb_cnn_eq/dut -out_file [file rootname $rpt]_saif_match.txt $saif
report_power -file $rpt
puts "POWER_REPORT $rpt"
