param([Parameter(Mandatory)][string]$Plan)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName Microsoft.VisualBasic
$items=Get-Content -LiteralPath $Plan -Raw | ConvertFrom-Json
function Assert-PlainFile($path) {
 $entry=Get-Item -LiteralPath $path -Force
 if($entry.PSIsContainer) {throw 'Cleanup target is not a file'}
 while($null -ne $entry) {
  if(($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'Reparse target prohibited'}
  if($entry -is [IO.FileInfo]) {$entry=$entry.Directory} else {$entry=$entry.Parent}
 }
}
foreach($item in $items) {
 Assert-PlainFile $item.path
 if(-not (Test-Path -LiteralPath $item.path -PathType Leaf)) {throw 'Cleanup target missing'}
 if((Get-FileHash -LiteralPath $item.path -Algorithm SHA256).Hash.ToLower() -ne $item.sha256) {throw 'Cleanup file changed'}
}
foreach($item in $items) {
 Assert-PlainFile $item.path
 if((Get-FileHash -LiteralPath $item.path -Algorithm SHA256).Hash.ToLower() -ne $item.sha256) {throw 'Cleanup file changed before recycling'}
 [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($item.path,'OnlyErrorDialogs','SendToRecycleBin')
}
