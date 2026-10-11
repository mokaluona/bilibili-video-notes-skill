param([Parameter(Mandatory)][string]$Plan)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName Microsoft.VisualBasic
$items=Get-Content -LiteralPath $Plan -Raw | ConvertFrom-Json
foreach($item in $items) {
 if(-not (Test-Path -LiteralPath $item.path -PathType Leaf)) {throw 'Cleanup target missing'}
 if((Get-FileHash -LiteralPath $item.path -Algorithm SHA256).Hash.ToLower() -ne $item.sha256) {throw 'Cleanup file changed'}
}
foreach($item in $items) {
 [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($item.path,'OnlyErrorDialogs','SendToRecycleBin')
}
