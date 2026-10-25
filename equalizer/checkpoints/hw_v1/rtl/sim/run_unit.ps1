# run_unit.ps1 - compile and run the conv1d_stream unit test bench (tb_conv1d_unit) in Vivado xsim.
# Usage: powershell -File rtl\sim\run_unit.ps1
param([string]$Vivado = "D:\AMD\2025.2\Vivado\bin")
$ErrorActionPreference = "Stop"
$rtl = Split-Path -Parent $PSScriptRoot
$work = Join-Path $PSScriptRoot "work_unit"
New-Item -ItemType Directory -Force $work | Out-Null
Push-Location $work
try {
    $src = @("$rtl\src\sync_fifo.sv", "$rtl\src\add_tree.sv", "$rtl\src\conv1d_stream.sv", "$rtl\sim\tb_conv1d_unit.sv")
    & "$Vivado\xvlog.bat" -sv @src | Tee-Object xvlog_out.log | Out-Null
    if ($LASTEXITCODE -ne 0) { Get-Content xvlog_out.log | Select-String "ERROR|WARNING"; throw "xvlog failed" }
    & "$Vivado\xelab.bat" tb_conv1d_unit -s unit_snap -timescale 1ns/1ps -debug off | Tee-Object xelab_out.log | Out-Null
    if ($LASTEXITCODE -ne 0) { Get-Content xelab_out.log | Select-String "ERROR"; throw "xelab failed" }
    & "$Vivado\xsim.bat" unit_snap -R | Tee-Object xsim_out.log |
        Select-String "PASS|FAIL|MISMATCH|TLAST|EXTRA|TIMEOUT|not done|ERROR|Fatal|overflow| X at "
} finally { Pop-Location }
