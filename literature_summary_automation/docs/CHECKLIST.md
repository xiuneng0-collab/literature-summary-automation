# 缺什么怎么办

第一次使用、Zotero 和飞书都没配好时，先看 [从零配置使用说明](NO_CONFIG_START.md)。

也可以先运行自检：

```powershell
python .\scripts\config_doctor.py
```

## Python 不可用

现象：运行 `python --version` 报错。

处理：安装 Python 3.10 或更高版本，并勾选 Add Python to PATH。重新打开 PowerShell 后再试。

## 缺少 Python 包

现象：提示 `ModuleNotFoundError: No module named 'docx'` 或 `requests`。

处理：

```powershell
python -m pip install python-docx requests
```

## 缺少 Poppler

现象：提示 `pdftotext not found` 或 `pdftoppm not found`。

处理：安装 Poppler，并把 `bin` 目录加入系统 PATH。重新打开 PowerShell 后检查：

```powershell
pdftotext -v
pdftoppm -v
```

## 找不到 Zotero 数据库

现象：提示 `Cannot find Zotero database`。

处理：打开 Zotero，进入 `编辑 -> 设置 -> 高级 -> 文件和文件夹`，查看数据目录位置。把该目录填到 `.env.local` 的 `ZOTERO_DATA_DIR`，或者运行时传：

```powershell
.\run_summary.ps1 -Query "论文题名" -ZoteroDir "你的Zotero数据目录"
```

## 找到了条目但没有 PDF

现象：提示 `no local PDF attachment was found`。

处理：在 Zotero 中确认该条目下面有本地 PDF 附件，并能正常打开。若 PDF 存在但被移动过，右键附件重新定位文件，或重新拖入 PDF。

也可以先运行自动检查：

```powershell
.\run_summary.ps1 -Query "论文题名或 DOI" -CheckAttachments
```

如果报告显示 `MISSING`，并且你确认可以从 DOI 或最近抓取 JSON 的 PDF URL 恢复：

```powershell
.\run_summary.ps1 -Query "论文题名或 DOI" -RepairAttachments -DownloadMissing
```

修复模式只把 PDF 放回 Zotero 数据库已记录的位置，不改数据库。修复后回到 Zotero 直接双击原附件即可打开。

## 新抓取文献批量检查

现象：刚抓取的一批文献里，有些能打开，有些弹出“在此路径无法找到附件”。

处理：

```powershell
python .\scripts\check_zotero_attachments.py `
  --latest-json "..\zotero_added_latest.json" `
  --repair `
  --download
```

报告在 `reports/` 目录。如果某条显示 `NO_PDF_ATTACHMENT_ROW`，说明 Zotero 条目下面还没有 PDF 附件记录，需要手动拖入 PDF 或重新抓取带 PDF 的页面。

## Zotero 正在锁数据库

现象：偶发数据库读取失败。

处理：脚本会复制数据库再读取。若仍失败，先关闭 Zotero，等几秒再运行。

## 飞书上传失败

现象：提示缺少 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`，或 API 返回权限错误。

处理：

1. 确认 `.env.local` 或系统环境变量里有 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`。
2. 确认飞书开放平台应用已启用云空间相关权限，常用权限包括 `drive:file:upload`、`drive:file` 或 `drive:drive`。
3. 如果要上传到指定文件夹，确认 `FEISHU_PARENT_NODE` 是文件夹 token，不是浏览器完整 URL。
4. 如果截图、日志或聊天中暴露过 App Secret，立即在飞书开放平台重置密钥。

## 不想暴露 API 和内部地址

处理：

- 只把真实密钥写入 `.env.local`，不要写入 README、模板、总结正文或聊天消息。
- 分享文件夹前删除 `.env.local`、日志、生成的上传结果 JSON。
- 给别人看飞书配置时，只截取权限名称和按钮，不截 App Secret、tenant token、文件夹 URL。
