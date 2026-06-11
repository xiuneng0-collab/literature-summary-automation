# 从零配置使用说明

这份说明给第一次拿到自动化包的人使用。目标是：即使 Zotero 和飞书都没配好，也能一步步完成“指定文献 -> 生成 Word 总结 -> 上传飞书”。

## 先记住三件事

1. 没有飞书配置，也能先生成 Word。
2. 没有 Zotero 本地 PDF，脚本无法读取论文正文，需要先把 PDF 放进 Zotero。
3. 真实 App Secret 只写入 `.env.local`，不要写进聊天、README、截图或共享文档。

## 最省心入口

拿到文件夹后，先双击：

```text
START_HERE.bat
```

它会自动创建 `.env.local`、提示你填写配置、运行自检，并引导你输入论文题名或 DOI。

## 第一步：安装基础软件

### Python

安装 Python 3.10 或更高版本。安装时勾选 `Add Python to PATH`。

检查：

```powershell
python --version
```

安装 Python 包：

```powershell
python -m pip install python-docx requests
```

### Poppler

安装 Poppler，并把 Poppler 的 `bin` 目录加入系统 PATH。

检查：

```powershell
pdftotext -v
pdftoppm -v
```

如果这两个命令不可用，脚本不能从 PDF 提取文本和页面截图。

## 第二步：配置 Zotero

### 找到 Zotero 数据目录

打开 Zotero：

`编辑 -> 设置 -> 高级 -> 文件和文件夹 -> 数据目录位置`

记下这个目录。这个目录里应该能看到：

- `zotero.sqlite`
- `storage`

### 确认论文 PDF 在 Zotero 里

在 Zotero 中打开目标条目，确认下面有 PDF 附件，并且能双击打开。

如果 Zotero 弹出“在此路径无法找到附件”，先在自动化包里运行：

```powershell
python .\scripts\check_zotero_attachments.py --all
```

尝试自动修复：

```powershell
python .\scripts\check_zotero_attachments.py --all --repair --download
```

如果报告显示 `NO_PDF_ATTACHMENT_ROW`，说明 Zotero 条目下面没有 PDF 附件，需要手动拖入 PDF 或重新抓取带 PDF 的网页。

## 第三步：创建本机配置文件

在 `literature_summary_automation` 文件夹打开 PowerShell：

```powershell
Copy-Item .\.env.example .\.env.local
```

打开 `.env.local`，先填 Zotero 和输出目录：

```text
ZOTERO_DATA_DIR=你的Zotero数据目录
SUMMARY_OUT_ROOT=你的输出目录
```

如果暂时不上传飞书，飞书项可以先空着。

## 第四步：先跑自检

```powershell
python .\scripts\config_doctor.py
```

如果要验证飞书 API：

```powershell
python .\scripts\config_doctor.py --test-feishu
```

自检只显示“有没有配置”和“能不能访问”，不会打印 App Secret。

## 第五步：生成文献总结

用论文题名、DOI 或 Zotero item key 指定文献：

```powershell
.\run_summary.ps1 -Query "论文题名或 DOI"
```

脚本会生成：

- `paper_metadata.json`
- `zotero_pdf_text.txt`
- `pdf_pages/`
- `figures/`
- `summary.md`
- `codex_task.md`

然后让 Codex 按 `codex_task.md` 完成总结，并导出 Word。

## 第六步：配置飞书上传

### 创建飞书应用

在飞书开放平台创建企业自建应用，复制：

- App ID
- App Secret

给应用开通云空间相关权限，常用权限包括：

- `drive:file:upload`
- `drive:file`
- `drive:drive`

发布或安装应用，使权限生效。

### 配置上传文件夹

在飞书云文档里创建或打开目标文件夹，比如“文献库”。

复制文件夹链接，例如：

```text
https://your-team.feishu.cn/drive/folder/这里是一串文件夹token?from=from_copylink
```

其中 `这里是一串文件夹token` 就是文件夹 token。真实 token 只写进 `.env.local`，不要写进说明文档或总结正文。

在 `.env.local` 中填写：

```text
FEISHU_APP_ID=你的AppID
FEISHU_APP_SECRET=你的AppSecret
FEISHU_PARENT_NODE=你的文件夹token
FEISHU_PARENT_TYPE=explorer
```

验证：

```powershell
python .\scripts\config_doctor.py --test-feishu
```

## 第七步：上传 Word

如果 `summary.md` 已经写好：

```powershell
.\run_summary.ps1 -Query "同一篇论文题名或 DOI" -ExportDocx -UploadFeishu
```

也可以直接上传某个 Word：

```powershell
python .\scripts\upload_to_feishu.py --file "你的Word文件路径.docx"
```

## 常见卡点

- `Missing Zotero directory`：没有填写 `ZOTERO_DATA_DIR`。
- `pdftotext not found`：没有安装 Poppler 或没有加入 PATH。
- `no local PDF attachment was found`：Zotero 条目没有本地 PDF。
- `Missing environment variable: FEISHU_APP_ID`：没有填写飞书 App ID。
- 飞书上传后找不到：检查 `FEISHU_PARENT_NODE` 是否填的是文件夹 token；不填会上传到应用可访问根目录。
- App Secret 暴露过：立即到飞书开放平台重置，再更新 `.env.local`。

## 日常一句话流程

配置完成后，使用者只需要说：

```text
请总结 Zotero 里的这篇文献并上传飞书。
```

或者运行：

```powershell
.\run_summary.ps1 -Query "论文题名或 DOI" -ExportDocx -UploadFeishu
```
