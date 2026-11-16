# Convert report/MLEE_Report.docx to PDF with Microsoft Word (updates fields such as page numbers).
param([string]$Docx = "$PSScriptRoot\MLEE_Report.docx", [string]$Pdf = "$PSScriptRoot\MLEE_Report.pdf")
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {
    $d = $w.Documents.Open((Resolve-Path $Docx).Path, $false, $true)
    $d.Fields.Update() | Out-Null
    $d.SaveAs([ref]$Pdf, [ref]17)
    $d.Close([ref]0)
    Write-Output "wrote $Pdf"
} finally {
    $w.Quit()
}
