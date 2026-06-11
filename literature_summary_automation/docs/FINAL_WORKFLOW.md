# 最终工作流：指定文献 -> 总结 -> Word -> 飞书

这份文档给日常使用者看，只保留必须知道的步骤。真实 API、App Secret、飞书文件夹地址、Zotero 私人路径只放在本机 `.env.local`，不要发给别人。

## 角色分工

- 使用者：指定哪篇文献，确认 Zotero 里有 PDF。
- 自动化脚本：找 Zotero PDF、检查附件路径、提取文本、生成页面截图、导出 Word、上传飞书。
- Codex：根据 `codex_task.md` 读论文、挑图、写完整中文总结。

## 固定规则

- API 不需要每次提供。第一次把飞书 App ID、App Secret、目标文件夹 token 写入本机 `.env.local` 后，后面脚本自动读取。
- MCP 可以辅助操作 Zotero，但本工作流不强制依赖 MCP；默认直接读本机 Zotero 数据库和 PDF，更稳定。
- 飞书上传默认进入 `.env.local` 里 `FEISHU_PARENT_NODE` 指向的文件夹。换文件夹只改 `.env.local`，不要改脚本。
- 每篇总结标题自动带当天日期，格式为 `YYYY年MM月DD日`。
- 总结、README、封面、发布文案里都不要出现 App Secret、tenant token、完整飞书文件夹链接或私人 Zotero 路径。

## 第一次使用

1. 双击 `START_HERE.bat`。
2. 如果提示没有 `.env.local`，让它自动创建。
3. 按提示打开 `.env.local`，填写本机配置：

```text
ZOTERO_DATA_DIR=你的 Zotero 数据目录
SUMMARY_OUT_ROOT=你的总结输出目录
FEISHU_APP_ID=你的飞书 App ID
FEISHU_APP_SECRET=你的飞书 App Secret
FEISHU_PARENT_NODE=你的飞书文件夹 token
FEISHU_PARENT_TYPE=explorer
```

4. 回到窗口运行自检。
5. 自检缺什么，就按 `docs/CHECKLIST.md` 补什么。

飞书暂时没配好也可以先用，最多只能生成 Word，不能上传。

## 日常使用

1. 在 Zotero 里确认目标文献的 PDF 能双击打开。
2. 双击 `START_HERE.bat`。
3. 输入论文题名、DOI 或 Zotero item key。
4. 默认选择检查 Zotero PDF 路径。
5. 如果脚本提示路径坏了，再选择自动修复或下载。
6. 脚本会生成一个论文输出文件夹，里面有 `codex_task.md`。
7. 对 Codex 说：

```text
请打开刚才输出文件夹里的 codex_task.md，按模板完成文献总结，导出 Word，并上传飞书。
```

8. Codex 完成后，Word 文档会在输出文件夹里；如果飞书配置正确，也会上传到指定文件夹。

## 最短命令

已经配置好以后，也可以不用双击入口，直接运行：

```powershell
.\run_summary.ps1 -Query "论文题名或 DOI" -CheckAttachments
```

总结写好后导出并上传：

```powershell
.\run_summary.ps1 -Query "同一篇论文题名或 DOI" -ExportDocx -UploadFeishu
```

## 换电脑使用

1. 把干净 zip 解压到新电脑。
2. 不要复制旧电脑的 `.env.local`。
3. 在新电脑双击 `START_HERE.bat`，重新填写 `.env.local`。
4. 安装 Python 依赖和 Poppler。
5. 确认 Zotero 数据目录里有 `zotero.sqlite` 和 `storage`。
6. 运行自检，全部通过后再总结文献。

## 交付前检查

分享给别人前确认：

- 包里没有 `.env.local`。
- 包里没有真实飞书完整链接。
- 包里没有 App Secret、tenant token、上传返回 token。
- README 和文档只写占位示例。
- 使用者拿到后先看 `docs/NO_CONFIG_START.md`。

## 出问题时怎么判断

- 找不到 Zotero：先看 `.env.local` 的 `ZOTERO_DATA_DIR`。
- 找不到 PDF：先在 Zotero 里双击 PDF；打不开就运行附件检查。
- 提取不了 PDF：检查 Poppler 的 `pdftotext` 和 `pdftoppm`。
- 上传不了飞书：先运行 `python .\scripts\config_doctor.py --test-feishu`。
- 飞书上传后找不到：检查 `FEISHU_PARENT_NODE` 是否是文件夹 token，不是完整 URL。
