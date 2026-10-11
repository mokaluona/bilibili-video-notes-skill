param([Parameter(Mandatory)][string]$InputDocx,[Parameter(Mandatory)][string]$OutputPdf)
$ErrorActionPreference='Stop'
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
$document=$null
try {
 $document=$word.Documents.Open($InputDocx,$false,$true)
 $document.Repaginate()
 $document.ExportAsFixedFormat($OutputPdf,17)
} finally {
 if($null -ne $document) { $document.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
 if($word.Documents.Count -eq 0) { $word.Quit() }
 [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
