# 文献总结自动化包

这个文件夹把“指定一篇高质量文献 -> 从 Zotero 找本地 PDF -> 提取文本和页面截图 -> 生成当天日期标题的总结草稿 -> 导出 Word -> 可选上传飞书”固化成一套可重复流程。

真实 API、飞书地址、App Secret、Zotero 私人路径不写进模板和说明。使用者只在自己的 `.env.local` 或系统环境变量里配置。

## 最推荐用法

不会命令行的使用者，直接双击：

```text
START_HERE.bat
```

它会按顺序提示：

1. 创建或检查 `.env.local`。
2. 运行配置自检。
3. 输入论文题名、DOI 或 Zotero item key。
4. 检查 Zotero PDF 路径。
5. 生成 `summary.md` 和 `codex_task.md`。
6. 提示把 `codex_task.md` 交给 Codex 完成总结、导出 Word、上传飞书。

完整日常流程看 [最终工作流](docs/FINAL_WORKFLOW.md)。

## 文件夹结构

```text
literature_summary_automation/
  START_HERE.bat
  start_workflow.ps1
  run_summary.ps1
  make_release_zip.ps1
  .env.example
  scripts/
    run_literature_summary.py
    prepare_zotero_paper.py
    summary_md_to_docx.py
    upload_to_feishu.py
  templates/
    summary_template.md
    codex_task_template.md
  docs/
    FINAL_WORKFLOW.md
    CHECKLIST.md
    MCP_AND_FEISHU_SETUP.md
    NO_CONFIG_START.md
```

如果 Zotero 和飞书都还没有配置，请先看：

[从零配置使用说明](docs/NO_CONFIG_START.md)

也可以先运行自检：

```powershell
python .\scripts\config_doctor.py
```

## 第一次配置

1. 复制配置样例：

```powershell
Copy-Item .\.env.example .\.env.local
```

2. 打开 `.env.local`，只填写本机真实配置：

```text
ZOTERO_DATA_DIR=你的Zotero数据目录
SUMMARY_OUT_ROOT=你的输出目录
FEISHU_APP_ID=你的AppID
FEISHU_APP_SECRET=你的AppSecret
FEISHU_PARENT_NODE=可选文件夹token
```

3. 安装依赖：

```powershell
python -m pip install python-docx requests
```

4. 安装 Poppler，并确认 `pdftotext`、`pdftoppm` 可用：

```powershell
pdftotext -v
pdftoppm -v
```

## 日常使用

最简单方式是双击 `START_HERE.bat`。

如果你习惯命令行，也可以在本文件夹打开 PowerShell，按论文题名、DOI 或 Zotero item key 指定文献：

```powershell
.\run_summary.ps1 -Query "论文英文题名或 DOI"
```

如果 Zotero 弹出“在此路径无法找到附件”，先运行附件检查：

```powershell
.\run_summary.ps1 -Query "论文英文题名或 DOI" -CheckAttachments
```

如果确认要自动修复缺失 PDF，让脚本把本机已有 PDF 或可下载 PDF 放回 Zotero 记录的 storage 路径：

```powershell
.\run_summary.ps1 -Query "论文英文题名或 DOI" -RepairAttachments -DownloadMissing
```

检查最近抓取的一批文献：

```powershell
.\run_summary.ps1 `
  -Query "任意一个要顺带检查的题名" `
  -LatestJson "..\zotero_added_latest.json" `
  -CheckAttachments
```

修复最近抓取的一批文献：

```powershell
python .\scripts\check_zotero_attachments.py `
  --latest-json "..\zotero_added_latest.json" `
  --repair `
  --download
```

脚本会生成一个输出文件夹，里面包括：

- `paper_metadata.json`：Zotero 条目信息和 PDF 路径。
- `zotero_pdf_text.txt`：从本地 PDF 提取的全文文本。
- `pdf_pages/`：PDF 页面截图。
- `figures/`：后续裁剪论文图的位置。
- `summary.md`：带当天年月日标题的总结草稿。
- `codex_task.md`：交给 Codex 执行总结的固定任务说明。

然后把 `codex_task.md` 交给 Codex，或直接说：

```text
请按 你的输出目录\某篇论文\codex_task.md 完成文献总结，导出 Word。
```

## 导出 Word

当 `summary.md` 已经填好后运行：

```powershell
.\run_summary.ps1 -Query "同一篇论文题名或 DOI" -ExportDocx
```

也可以直接运行：

```powershell
python .\scripts\summary_md_to_docx.py `
  --summary "你的输出目录\某篇论文\summary.md" `
  --output "你的输出目录\某篇论文\文献总结_20260611.docx"
```

## 上传飞书

确认 `.env.local` 已填写 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`，并且飞书应用有云空间上传权限后：

```powershell
.\run_summary.ps1 -Query "同一篇论文题名或 DOI" -ExportDocx -UploadFeishu
```

如果上传失败，先看 [缺什么怎么办](docs/CHECKLIST.md)。

## Zotero 附件检查报告

附件检查会在 `reports/` 下生成 JSON 和 Markdown 报告，记录：

- 哪些 PDF 能直接在 Zotero 打开。
- 哪些 PDF 路径失效。
- 哪些已通过本地文件复制修复。
- 哪些已通过 DOI 或 PDF URL 下载修复。
- 哪些条目没有 PDF 附件记录，需要手动补 PDF。

修复模式不直接改 Zotero 数据库，只恢复数据库已经指向的 PDF 文件位置。

## Zotero MCP 和飞书配置

完整配置流程放在 [Zotero MCP 与飞书 API 配置流程](docs/MCP_AND_FEISHU_SETUP.md)。

本自动化默认不强制依赖 Zotero MCP，因为直接读本地 Zotero 数据库更稳定。需要 MCP 时，再按文档把 MCP server 接到你自己的客户端里。

## 固定总结格式

模板在 [summary_template.md](templates/summary_template.md)。标题已经内置当天年月日：

```text
英文题名 文献总结（YYYY年MM月DD日）
```

总结必须包含基本信息表、实验方法、论文截图、创新点、可改进方向、可借鉴写法和资料来源。

## 打包给别的电脑

不要直接压缩整个工作目录，因为里面可能有 `.env.local` 或个人输出文件。请运行：

```powershell
.\make_release_zip.ps1
```

它会生成干净的 `literature_summary_automation.zip`，自动排除 `.env.local`、`.env`、`outputs/`、`reports/`、日志和缓存文件。
