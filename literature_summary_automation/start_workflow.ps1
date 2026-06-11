param(
  [switch]$SkipDoctor
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

try {
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
  # Older PowerShell hosts may not allow encoding changes. Continue anyway.
}

function Ask-YesNo {
  param(
    [string]$Question,
    [bool]$DefaultYes = $true
  )

  $suffix = if ($DefaultYes) { "[Y/n]" } else { "[y/N]" }
  while ($true) {
    $answer = (Read-Host "$Question $suffix").Trim()
    if ($answer -eq "") {
      return $DefaultYes
    }
    if ($answer -match "^(y|yes|是|好|1)$") {
      return $true
    }
    if ($answer -match "^(n|no|否|不|0)$") {
      return $false
    }
    Write-Host "请输入 y 或 n。" -ForegroundColor Yellow
  }
}

function Run-Command {
  param(
    [string]$Title,
    [string[]]$CommandArgs
  )

  Write-Host ""
  Write-Host "== $Title ==" -ForegroundColor Cyan
  & $CommandArgs[0] $CommandArgs[1..($CommandArgs.Count - 1)]
  if ($LASTEXITCODE -ne 0) {
    throw "步骤失败：$Title"
  }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 文献总结自动化：Zotero -> Word -> 飞书" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "这个入口不会显示 App Secret，也不会把飞书地址写入总结。"
Write-Host ""

if (-not (Test-Path -LiteralPath ".\.env.local")) {
  Write-Host "第一次使用：没有找到 .env.local。" -ForegroundColor Yellow
  Copy-Item -LiteralPath ".\.env.example" -Destination ".\.env.local"
  Write-Host "已从 .env.example 创建 .env.local，请填写本机 Zotero 路径和飞书配置。"
  if (Ask-YesNo "现在打开 .env.local 吗？" $true) {
    notepad ".\.env.local"
    Write-Host "填好并保存后，回到这个窗口继续。"
    Read-Host "按 Enter 继续" | Out-Null
  }
}

if (-not $SkipDoctor) {
  if (Ask-YesNo "先运行配置自检吗？" $true) {
    & python ".\scripts\config_doctor.py"
    if ($LASTEXITCODE -ne 0) {
      Write-Host ""
      Write-Host "自检还有缺项。你仍然可以继续准备文献，但缺 Zotero/PDF/Poppler 时会失败。" -ForegroundColor Yellow
      if (-not (Ask-YesNo "继续吗？" $false)) {
        exit 1
      }
    }
  }
}

Write-Host ""
Write-Host "请输入要总结的论文题名、DOI 或 Zotero item key。"
$Query = (Read-Host "论文").Trim()
if ($Query -eq "") {
  Write-Host "没有输入论文，已退出。" -ForegroundColor Yellow
  exit 1
}

$runArgs = @(".\run_summary.ps1", "-Query", $Query)

if (Ask-YesNo "先检查这篇文献的 Zotero PDF 路径吗？" $true) {
  $runArgs += "-CheckAttachments"
  if (Ask-YesNo "如果路径坏了，允许自动修复本机已有 PDF 吗？" $false) {
    $runArgs += "-RepairAttachments"
    if (Ask-YesNo "如果本机没有 PDF，允许按 DOI/链接尝试下载吗？" $false) {
      $runArgs += "-DownloadMissing"
    }
  }
}

Run-Command "准备文献材料" $runArgs

Write-Host ""
Write-Host "下一步，把上面输出的 codex_task.md 交给 Codex 完成真正的阅读总结。" -ForegroundColor Green
Write-Host "可以直接对 Codex 说："
Write-Host "请打开刚才输出文件夹里的 codex_task.md，按模板完成文献总结，导出 Word，并上传飞书。"

Write-Host ""
if (Ask-YesNo "如果 summary.md 已经写好，现在导出 Word 吗？" $false) {
  $exportArgs = @(".\run_summary.ps1", "-Query", $Query, "-ExportDocx")
  if (Ask-YesNo "导出后上传飞书吗？" $true) {
    $exportArgs += "-UploadFeishu"
  }
  Run-Command "导出/上传总结" $exportArgs
}

Write-Host ""
Write-Host "完成。常见问题看 docs\CHECKLIST.md；新电脑配置看 docs\NO_CONFIG_START.md。" -ForegroundColor Green
