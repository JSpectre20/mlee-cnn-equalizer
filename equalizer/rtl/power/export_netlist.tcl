# export_netlist.tcl - write the post-route functional netlist of an OOC build for activity simulation.
# Usage: vivado -mode batch -source export_netlist.tcl -tclargs <out_dir with routed.dcp> <netlist.v>
set dcp [file join [lindex $argv 0] routed.dcp]
set nl  [lindex $argv 1]
open_checkpoint $dcp
write_verilog -force -mode funcsim $nl
puts "NETLIST $nl"
