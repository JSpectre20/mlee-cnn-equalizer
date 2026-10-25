# run_sim.ps1 - compile and run tb_cnn_eq in Vivado xsim for one exported model.
# Usage: powershell -File rtl\sim\run_sim.ps1 -Model ours_bce_w6 [-Stall 30] [-UseDsp 1]
param(
    [Parameter(Mandatory = $true)][string]$Model,
    [int]$Stall = 0,
    [int]$UseDsp = 0,
    [string]$ConvSrc = "",      # alternative conv1d_stream.sv (e.g. rtl\history\conv1d_stream_r2.sv)
    [string]$Vivado = "D:\AMD\2025.2\Vivado\bin"
)
$ErrorActionPreference = "Stop"
$rtl = Split-Path -Parent $PSScriptRoot
if (-not $ConvSrc) { $ConvSrc = "$rtl\src\conv1d_stream.sv" }
$ConvSrc = (Resolve-Path $ConvSrc).Path
$gen = Join-Path $rtl "gen\$Model"
$work = Join-Path $PSScriptRoot "work_$Model"
New-Item -ItemType Directory -Force $work | Out-Null
Push-Location $work
try {
    $src = @("$gen\cnn_eq_pkg.sv", "$rtl\src\sync_fifo.sv", "$rtl\src\add_tree.sv", $ConvSrc,
             "$rtl\src\cnn_eq_core.sv", "$rtl\src\cnn_eq_top.sv", "$rtl\sim\tb_cnn_eq.sv")
    Set-Content tb_dsp.svh "localparam bit USE_DSP = $UseDsp;" -Encoding ascii
    & "$Vivado\xvlog.bat" -sv -i $gen -i $work @src | Tee-Object xvlog_out.log | Out-Null
    if ($LASTEXITCODE -ne 0) { Get-Content xvlog_out.log | Select-String "ERROR|WARNING"; throw "xvlog failed" }
    & "$Vivado\xelab.bat" tb_cnn_eq -s tb_snap -timescale 1ns/1ps -debug off | Tee-Object xelab_out.log | Out-Null
    if ($LASTEXITCODE -ne 0) { Get-Content xelab_out.log | Select-String "ERROR"; throw "xelab failed" }
    Copy-Item "$gen\params.mem", "$gen\test_in.mem", "$gen\test_out.mem" -Destination $work -Force
    & "$Vivado\xsim.bat" tb_snap -R -testplusarg "stall$Stall" | Tee-Object xsim_out.log |
        Select-String "PASS|FAIL|MISMATCH|TIMEOUT|cycles|loaded|ERROR|Fatal|EXTRA|FRAMES"
} finally { Pop-Location }
