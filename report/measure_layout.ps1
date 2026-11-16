# For every figure / table of report/MLEE_Report.docx: the page it starts on, and the page and vertical position (pt)
# of the last line before it. Output: one line "kind|number|page|prev_page|prev_y" per float, in document order.
param([string]$Docx = "$PSScriptRoot\MLEE_Report.docx")
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {
    $d = $w.Documents.Open((Resolve-Path $Docx).Path, $false, $true)
    $d.Repaginate()
    $ps = $d.Paragraphs
    $n = $ps.Count
    for ($i = 2; $i -le $n; $i++) {
        $p = $ps.Item($i)
        $t = $p.Range.Text
        if ($t -match '^(Figure|Table) (\d+):') {
            $kind = $Matches[1]; $num = $Matches[2]
            $start = if ($kind -eq 'Figure') { $i - 1 } else { $i }      # figure: the picture paragraph above its caption
            if ($start -lt 2) { continue }
            $page = $ps.Item($start).Range.Information(3)
            $prev = $ps.Item($start - 1).Range
            $last = $prev.Characters.Last
            "{0}|{1}|{2}|{3}|{4}" -f $kind, $num, $page, $last.Information(3), $last.Information(6)
        }
    }
    $d.Close([ref]0)
} finally {
    $w.Quit()
}
