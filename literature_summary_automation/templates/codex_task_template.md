# Codex 文献总结任务（{summary_date}）

请按本文件夹的固定模板，完成一篇高质量文献总结。

## 输入文献

- 查询词：`{query}`
- Zotero 条目标题：`{english_title}`
- DOI：`{doi}`
- 本地 PDF：`{local_pdf_path}`
- 提取文本：`{local_text_path}`
- PDF 页面截图目录：`{local_pages_dir}`
- 截图输出目录：`{local_figures_dir}`
- Markdown 草稿：`{summary_path}`

## 执行要求

1. 阅读 `paper_metadata.json` 和 `zotero_pdf_text.txt`，必要时查看 `pdf_pages` 页面截图。
2. 从本地 PDF 页面截图中挑选最值得学习的图，优先选择方法框架图、系统结构图、实验结果图、部署图、参数表或消融实验表。
3. 将选中的图裁剪到 `figures` 目录，图片必须来自本地 Zotero PDF，不使用网页缩略图。
4. 按 `templates/summary_template.md` 的栏目填满 `summary.md`。
5. 文献总结标题必须保留当天日期：`{summary_date}`。
6. 不逐条列出参考文献，只概括参考文献数量、类型、年份跨度或引用特点。
7. 不写入任何 API key、App Secret、内部地址或私人空间链接。
8. 完成后运行 Word 导出脚本生成 `.docx`；如果用户明确要求上传飞书，再运行飞书上传。

## 推荐导出命令

```powershell
python .\scripts\summary_md_to_docx.py `
  --summary "{summary_path}" `
  --output "{docx_path}"
```

## 推荐飞书上传命令

```powershell
python .\scripts\upload_to_feishu.py --file "{docx_path}"
```
