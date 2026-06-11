#!/usr/bin/env python
"""Check local setup for the literature-summary automation.

This script prints only presence/status information. It never prints API keys,
App Secret values, tenant tokens, or private Feishu folder URLs.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.lstrip("\ufeff").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def status(ok: bool, label: str, detail: str = "") -> bool:
    mark = "OK" if ok else "缺少"
    suffix = f" - {detail}" if detail else ""
    print(f"[{mark}] {label}{suffix}")
    return ok


def have_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def zotero_stats(zotero_dir: Path) -> tuple[int, int]:
    db = zotero_dir / "zotero.sqlite"
    fd, tmp_name = tempfile.mkstemp(prefix="zotero-doctor-", suffix=".sqlite")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy2(db, tmp)
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        rows = cur.execute(
            """
            SELECT a.key, ia.path
            FROM itemAttachments ia
            JOIN items a ON a.itemID=ia.itemID
            WHERE ia.contentType='application/pdf'
            """
        ).fetchall()
        total = len(rows)
        missing = 0
        for key, raw_path in rows:
            if not raw_path:
                missing += 1
                continue
            if raw_path.startswith("storage:"):
                pdf = zotero_dir / "storage" / key / raw_path.split("storage:", 1)[1]
            elif raw_path.startswith("attachments:"):
                pdf = zotero_dir / raw_path.split("attachments:", 1)[1]
            else:
                p = Path(raw_path)
                pdf = p if p.is_absolute() else zotero_dir / p
            if not pdf.exists():
                missing += 1
        con.close()
        return total, missing
    finally:
        tmp.unlink(missing_ok=True)


def test_feishu() -> bool:
    if not have_module("requests"):
        print("[缺少] requests - 无法测试飞书 API，请先运行 python -m pip install requests")
        return False
    import requests

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        print("[缺少] 飞书凭据 - FEISHU_APP_ID 或 FEISHU_APP_SECRET 未配置")
        return False
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=20,
    )
    data = r.json()
    if data.get("code") != 0:
        print(f"[缺少] 飞书 token 测试失败 - code={data.get('code')} msg={data.get('msg')}")
        return False
    token = data["tenant_access_token"]
    parent = os.environ.get("FEISHU_PARENT_NODE", "").strip()
    if parent:
        rr = requests.get(
            f"https://open.feishu.cn/open-apis/drive/explorer/v2/folder/{parent}/children?page_size=1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        folder_data = rr.json()
        if folder_data.get("code") != 0:
            print(f"[缺少] 飞书目标文件夹不可访问 - code={folder_data.get('code')} msg={folder_data.get('msg')}")
            return False
        print("[OK] 飞书 API 和目标文件夹可访问")
        return True
    print("[OK] 飞书 API 可用；未配置目标文件夹，将上传到应用可访问根目录")
    return True


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    load_env_file(ROOT / ".env.local")
    load_env_file(ROOT / ".env")

    ap = argparse.ArgumentParser(description="检查 Zotero/飞书/本地依赖是否配置完成。")
    ap.add_argument("--test-feishu", action="store_true", help="尝试调用飞书 API 验证凭据和目标文件夹。")
    args = ap.parse_args()

    print("文献总结自动化配置自检")
    print("=" * 32)

    ok = True
    ok &= status(sys.version_info >= (3, 10), "Python 版本", sys.version.split()[0])
    ok &= status(have_module("docx"), "python-docx", "缺少时运行 python -m pip install python-docx")
    ok &= status(have_module("requests"), "requests", "缺少时运行 python -m pip install requests")
    ok &= status(command_available("pdftotext"), "pdftotext/Poppler", "用于从 PDF 提取文本")
    ok &= status(command_available("pdftoppm"), "pdftoppm/Poppler", "用于渲染 PDF 页面截图")

    zotero_raw = os.environ.get("ZOTERO_DATA_DIR", "").strip()
    zotero_dir = Path(zotero_raw) if zotero_raw else None
    ok &= status(bool(zotero_dir), "ZOTERO_DATA_DIR", "在 .env.local 中填写 Zotero 数据目录")
    if zotero_dir:
        ok &= status(zotero_dir.exists(), "Zotero 数据目录", str(zotero_dir))
        ok &= status((zotero_dir / "zotero.sqlite").exists(), "zotero.sqlite", "Zotero 本地数据库")
        ok &= status((zotero_dir / "storage").exists(), "storage 文件夹", "Zotero PDF 附件目录")
        if (zotero_dir / "zotero.sqlite").exists() and (zotero_dir / "storage").exists():
            try:
                total, missing = zotero_stats(zotero_dir)
                status(total > 0, "Zotero PDF 附件记录", f"共 {total} 条，缺失 {missing} 条")
                if missing:
                    print("  提示：可运行 python .\\scripts\\check_zotero_attachments.py --all --repair --download")
            except Exception as exc:
                print(f"[缺少] Zotero 附件统计失败 - {exc}")
                ok = False

    out_root = os.environ.get("SUMMARY_OUT_ROOT", "").strip()
    status(bool(out_root), "SUMMARY_OUT_ROOT", out_root or "未配置时脚本会使用默认输出目录")

    feishu_id = bool(os.environ.get("FEISHU_APP_ID"))
    feishu_secret = bool(os.environ.get("FEISHU_APP_SECRET"))
    feishu_parent = bool(os.environ.get("FEISHU_PARENT_NODE"))
    status(feishu_id, "FEISHU_APP_ID", "只显示是否存在，不显示值")
    status(feishu_secret, "FEISHU_APP_SECRET", "只显示是否存在，不显示值")
    status(feishu_parent, "FEISHU_PARENT_NODE", "可选；建议配置文献库文件夹 token")

    if args.test_feishu:
        ok &= test_feishu()
    elif not (feishu_id and feishu_secret):
        print("  提示：不配置飞书也可以生成 Word；上传前再补飞书配置。")
    else:
        print("  提示：可运行 python .\\scripts\\config_doctor.py --test-feishu 验证飞书上传权限。")

    print("=" * 32)
    if ok:
        print("自检完成：基础配置可用。")
        return 0
    print("自检完成：仍有缺项，请按上方提示补齐。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
