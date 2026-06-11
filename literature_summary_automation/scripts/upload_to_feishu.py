#!/usr/bin/env python
"""Upload a file to Feishu/Lark Drive using an internal app."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

import requests


BASE = "https://open.feishu.cn/open-apis"


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


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing environment variable: {name}")
    return value


def get_token(app_id: str, app_secret: str) -> str:
    r = requests.post(
        f"{BASE}/auth/v3/tenant_access_token/internal/",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=20,
    )
    data = r.json()
    if data.get("code") != 0:
        raise SystemExit(json.dumps(data, ensure_ascii=False, indent=2))
    return data["tenant_access_token"]


def get_root_token(token: str) -> str:
    r = requests.get(
        f"{BASE}/drive/explorer/v2/root_folder/meta",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    data = r.json()
    if data.get("code") != 0:
        raise SystemExit(json.dumps(data, ensure_ascii=False, indent=2))
    return data["data"]["token"]


def upload(file_path: Path, token: str, parent_node: str, parent_type: str):
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    data = {
        "file_name": file_path.name,
        "parent_type": parent_type,
        "parent_node": parent_node,
        "size": str(file_path.stat().st_size),
    }
    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f, mime)}
        r = requests.post(
            f"{BASE}/drive/v1/files/upload_all",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files,
            timeout=120,
        )
    result = r.json()
    if result.get("code") != 0:
        raise SystemExit(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = Path(__file__).resolve().parents[1]
    load_env_file(root / ".env.local")
    load_env_file(root / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, type=Path)
    ap.add_argument("--parent-node", default=os.environ.get("FEISHU_PARENT_NODE"))
    ap.add_argument("--parent-type", default=os.environ.get("FEISHU_PARENT_TYPE", "explorer"))
    args = ap.parse_args()
    app_id = require_env("FEISHU_APP_ID")
    app_secret = require_env("FEISHU_APP_SECRET")
    token = get_token(app_id, app_secret)
    parent_node = args.parent_node or get_root_token(token)
    result = upload(args.file, token, parent_node, args.parent_type)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
