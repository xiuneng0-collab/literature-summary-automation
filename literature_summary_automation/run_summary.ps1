param(
  [Parameter(Mandatory = $true)]
  [string]$Query,

  [string]$ZoteroDir = "",
  [string]$OutRoot = "",
  [string]$Slug = "",
  [string]$LatestJson = "",

  [switch]$NoRender,
  [switch]$CheckAttachments,
  [switch]$RepairAttachments,
  [switch]$DownloadMissing,
  [switch]$RelinkPaths,
  [switch]$AllAttachments,
  [switch]$ExportDocx,
  [switch]$UploadFeishu
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Root "scripts\run_literature_summary.py"
$CheckScript = Join-Path $Root "scripts\check_zotero_attachments.py"

if ($CheckAttachments -or $RepairAttachments -or $AllAttachments) {
  $CheckArgs = @("--query", $Query)
  if ($ZoteroDir -ne "") {
    $CheckArgs += @("--zotero-dir", $ZoteroDir)
  }
  if ($LatestJson -ne "") {
    $CheckArgs += @("--latest-json", $LatestJson)
  }
  if ($RepairAttachments) {
    $CheckArgs += "--repair"
  }
  if ($DownloadMissing) {
    $CheckArgs += "--download"
  }
  if ($RelinkPaths) {
    $CheckArgs += "--relink-paths"
  }
  if ($AllAttachments) {
    $CheckArgs += "--all"
  }
  python $CheckScript @CheckArgs
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}

$ArgsList = @("--query", $Query)

if ($ZoteroDir -ne "") {
  $ArgsList += @("--zotero-dir", $ZoteroDir)
}
if ($OutRoot -ne "") {
  $ArgsList += @("--out-root", $OutRoot)
}
if ($Slug -ne "") {
  $ArgsList += @("--slug", $Slug)
}
if ($NoRender) {
  $ArgsList += "--no-render"
}
if ($ExportDocx) {
  $ArgsList += "--export-docx"
}
if ($UploadFeishu) {
  $ArgsList += "--upload-feishu"
}

python $Script @ArgsList
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
