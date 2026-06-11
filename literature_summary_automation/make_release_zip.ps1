param(
  [string]$ZipPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootItem = Get-Item -LiteralPath $Root
$Parent = Split-Path -Parent $RootItem.FullName

if ($ZipPath -eq "") {
  $ZipPath = Join-Path $Parent "literature_summary_automation.zip"
}

$ReleaseRoot = Join-Path $Parent "_literature_summary_release_tmp"
$ReleaseFolder = Join-Path $ReleaseRoot "literature_summary_automation"

if (Test-Path -LiteralPath $ReleaseRoot) {
  $resolved = (Resolve-Path -LiteralPath $ReleaseRoot).Path
  if (-not $resolved.StartsWith($Parent, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "拒绝删除异常路径：$resolved"
  }
  Remove-Item -LiteralPath $ReleaseRoot -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $ReleaseFolder | Out-Null

$excludeNames = @(
  ".env",
  ".env.local",
  "__pycache__",
  "outputs",
  "reports"
)

$excludePatterns = @(
  "*.pyc",
  "*.log",
  "*_secret*",
  "*tenant_access_token*"
)

Get-ChildItem -LiteralPath $Root -Force | ForEach-Object {
  if ($excludeNames -contains $_.Name) {
    return
  }
  foreach ($pattern in $excludePatterns) {
    if ($_.Name -like $pattern) {
      return
    }
  }
  Copy-Item -LiteralPath $_.FullName -Destination $ReleaseFolder -Recurse -Force
}

if (Test-Path -LiteralPath $ZipPath) {
  Remove-Item -LiteralPath $ZipPath -Force
}

Compress-Archive -LiteralPath $ReleaseFolder -DestinationPath $ZipPath -Force
Write-Host "Clean release zip created: $ZipPath"
Write-Host "Excluded: .env, .env.local, outputs, reports, logs, cache files"

Remove-Item -LiteralPath $ReleaseRoot -Recurse -Force
