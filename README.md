# 文献总结自动化工具

这是一个给小白用户用的文献总结工具。

你只需要指定一篇 Zotero 里的论文，它会帮你：

1. 检查 Zotero 里的 PDF 能不能打开
2. 提取论文内容
3. 生成文献总结模板
4. 导出 Word 文档
5. 配置好飞书后，自动上传到飞书文件夹

## 怎么使用

### 第一步：下载

点 GitHub 页面右上角绿色按钮：

`Code -> Download ZIP`

下载后解压。

### 第二步：打开工具文件夹

进入这个文件夹：

`literature_summary_automation`

### 第三步：双击启动

双击：

`START_HERE.bat`

后面按照窗口提示操作就行。

## 第一次使用要填什么

第一次运行时，会自动生成 `.env.local` 文件。

你只需要填写：

```text
ZOTERO_DATA_DIR=你的 Zotero 数据目录
SUMMARY_OUT_ROOT=总结文件保存位置
![Uploading 71db33ed142398a4e41661e25d8c33cd.jpg…]()

FEISHU_APP_ID=你的飞书 App ID
FEISHU_APP_SECRET=你的飞书 App Secret
FEISHU_PARENT_NODE=飞书文件夹 token
FEISHU_PARENT_TYPE=explorer
