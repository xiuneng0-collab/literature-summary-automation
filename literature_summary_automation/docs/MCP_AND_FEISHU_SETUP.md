# Zotero MCP 与飞书 API 配置流程

这份自动化默认使用 Zotero 本地数据库和 PDF，不强制依赖 Zotero MCP。原因是本地方式更稳定，也不会把文献库地址、API key 或内部空间链接写进总结文件。

如果你希望在 Codex、Claude Desktop 或其他 MCP 客户端里直接检索 Zotero，可以额外配置 Zotero MCP。

## Zotero MCP 配置

1. 先确认 Zotero 本地库可用：Zotero 中至少有一个条目带本地 PDF 附件。
2. 打开 Zotero 数据目录，确认存在 `zotero.sqlite` 和 `storage` 文件夹。
3. 选择一个可信的 Zotero MCP server。优先使用你们团队审核过的包或仓库，不要把未知脚本接入带有私人文献库的客户端。
4. 在 MCP 客户端配置里新增 server，通常需要填：

```json
{
  "mcpServers": {
    "zotero": {
      "command": "node",
      "args": ["path/to/your/zotero-mcp-server"],
      "env": {
        "ZOTERO_DATA_DIR": "你的Zotero数据目录"
      }
    }
  }
}
```

5. 重启 MCP 客户端，测试是否能查询 Zotero 条目。

如果 MCP server 要求 Zotero Web API，请只把 token 写到客户端的安全环境变量里，不要写进本自动化文件夹。团队共享时只共享变量名，不共享真实值。

## 飞书 API 配置

1. 进入飞书开放平台，创建企业自建应用。
2. 记录 App ID 和 App Secret，只写入本机 `.env.local` 或系统环境变量。
3. 在权限管理中开通云空间上传权限。常见权限包括：
   - `drive:file:upload`
   - `drive:file`
   - `drive:drive`
4. 发布或安装应用到组织，使权限生效。
5. 如果上传到指定文件夹，在飞书文件夹 URL 中找到文件夹 token，填入 `FEISHU_PARENT_NODE`。不要把完整 URL 写进总结正文。
6. 先用一个测试 docx 运行：

```powershell
python .\scripts\upload_to_feishu.py --file "你的输出目录\test.docx"
```

7. 成功后再把 `-UploadFeishu` 加到自动化命令。

## 安全规则

- `.env.local` 是本机私有文件，不要发给别人。
- README 和模板只能出现变量名或占位符。
- 不在文献总结正文里写飞书文件夹地址、上传接口返回 token 或 App Secret。
- 若任何密钥出现在截图、日志、聊天记录或共享文档中，立即重置。
