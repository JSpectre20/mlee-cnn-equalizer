# run_power.ps1 - power of a routed OOC build with simulated switching activity (SAIF).
#   1. write the post-route functional netlist of rtl/syn/<OutDir>/routed.dcp
#   2. simulate it with tb_cnn_eq (NETLIST mode, 200 MHz clock, no stalls) on rtl/gen/<Model> vectors;
#      activity is logged only after the parameters are loaded (streaming phase)
#   3. report_power on the routed design with that activity
# Usage: powershell -File rtl\power\run_power.ps1 -Model ours_bce_dfe_w8_short -OutDir out_ours_bce_dfe_w8_5.0ns_dsp1_r8c
#   (-Model selects the test vectors: the _short sets, 8 x 64 symbols, keep the gate-level simulation short;
#    the netlist of an OutDir is reused while it is newer than its routed.dcp)
# Output: rtl/power/work_<OutDir>/ (netlist, saif, sim log) and rtl/power/power_<OutDir>.rpt
param(
    [Parameter(Mandatory = $true)][string]$Model,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [string]$Vivado = "D:\AMD\2025.2\Vivado\bin"
)
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$rtl  = Split-Path -Parent $here
$gen  = Join-Path $rtl "gen\$Model"
$syn  = Join-Path $rtl "syn\$OutDir"
$work = Join-Path $here "work_$OutDir"
New-Item -ItemType Directory -Force $work | Out-Null
Push-Location $work
try {
    if (-not (Test-Path netlist.v) -or (Get-Item netlist.v).LastWriteTime -lt (Get-Item "$syn\routed.dcp").LastWriteTime) {
        & "$Vivado\vivado.bat" -mode batch -nojournal -log export.log -source "$here\export_netlist.tcl" -tclargs $syn "$work\netlist.v" | Out-Null
    }
    if (-not (Test-Path netlist.v)) { throw "netlist export failed (see export.log)" }

    Set-Content tb_dsp.svh "localparam bit USE_DSP = 0;`n``define NETLIST`n``define TB_HALF_NS 2.5" -Encoding ascii
    $glbl = Join-Path (Split-Path -Parent $Vivado) "data\verilog\src\glbl.v"
    & "$Vivado\xvlog.bat" netlist.v $glbl | Tee-Object xvlog_nl.log | Out-Null
    if ($LASTEXITCODE -ne 0) { Get-Content xvlog_nl.log | Select-String "ERROR"; throw "xvlog (netlist) failed" }
    & "$Vivado\xvlog.bat" -sv -i $gen -i $work "$gen\cnn_eq_pkg.sv" "$rtl\sim\tb_cnn_eq.sv" | Tee-Object xvlog_tb.log | Out-Null
    if ($LASTEXITCODE -ne 0) { Get-Content xvlog_tb.log | Select-String "ERROR"; throw "xvlog (tb) failed" }
    & "$Vivado\xelab.bat" tb_cnn_eq glbl -L unisims_ver -s nl_snap -timescale 1ns/1ps -debug typical | Tee-Object xelab_out.log | Out-Null
    if ($LASTEXITCODE -ne 0) { Get-Content xelab_out.log | Select-String "ERROR"; throw "xelab failed" }
    Copy-Item "$gen\params.mem", "$gen\test_in.mem", "$gen\test_out.mem" -Destination $work -Force

    @"
add_condition -name loaded {/tb_cnn_eq/params_loaded == 1} { stop }
run all
remove_condition loaded
open_saif activity.saif
log_saif [get_objects -r /tb_cnn_eq/dut/*]
run all
close_saif
quit
"@ | Set-Content saif.tcl -Encoding ascii
    & "$Vivado\xsim.bat" nl_snap -tclbatch saif.tcl -testplusarg stall0 -onfinish stop | Tee-Object xsim_out.log |
        Select-String "PASS|FAIL|MISMATCH|TIMEOUT|cycles|ERROR|progress"
    if (-not (Test-Path activity.saif)) { throw "no SAIF written" }

    $rpt = Join-Path $here "power_$OutDir.rpt"
    & "$Vivado\vivado.bat" -mode batch -nojournal -log power.log -source "$here\power_saif.tcl" -tclargs $syn "$work\activity.saif" $rpt | Out-Null
    Select-String -Path power.log -Pattern "read_saif|matched|Matched" | Select-Object -First 4 | % { $_.Line }
    Get-Content $rpt | Select-String "Total On-Chip Power|Dynamic \(W\)|Device Static|Confidence Level" | % { $_.Line }
} finally { Pop-Location }
