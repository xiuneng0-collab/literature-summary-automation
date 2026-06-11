#!/usr/bin/env python
"""Start the reusable Zotero literature-summary workflow.

This runner prepares local Zotero artifacts, creates a dated summary draft,
and writes a Codex task prompt for the actual paper reading/writing step.
It never stores Feishu secrets or private addresses in generated summaries.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TEMPLATES = ROOT / "templates"


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


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=True, text=True, capture_output=True, encoding="utf-8", errors="replace")
    return proc.stdout


def fill_template(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{" + key + "}", value or "待补充")
    return out


def field(fields: dict, *names: str) -> str:
    lowered = {str(k).lower(): v for k, v in fields.items()}
    for name in names:
        if name in fields and fields[name]:
            return str(fields[name])
        if name.lower() in lowered and lowered[name.lower()]:
            return str(lowered[name.lower()])
    return ""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    load_env_file(ROOT / ".env.local")
    load_env_file(ROOT / ".env")

    ap = argparse.ArgumentParser(description="Prepare a Zotero paper for the fixed literature-summary workflow.")
    ap.add_argument("--query", required=True, help="Paper title, DOI, Zotero item key, or partial title.")
    ap.add_argument("--zotero-dir", default=os.environ.get("ZOTERO_DATA_DIR"), type=Path)
    ap.add_argument("--out-root", default=os.environ.get("SUMMARY_OUT_ROOT"), type=Path)
    ap.add_argument("--slug", default=None)
    ap.add_argument("--no-render", action="store_true", help="Skip rendering PDF pages.")
    ap.add_argument("--export-docx", action="store_true", help="Export DOCX if summary.md has already been filled.")
    ap.add_argument("--upload-feishu", action="store_true", help="Upload DOCX to Feishu after export.")
    args = ap.parse_args()

    if not args.zotero_dir:
        raise SystemExit("缺少 Zotero 数据目录。请在 .env.local 设置 ZOTERO_DATA_DIR，或运行时传 --zotero-dir。")
    if not args.zotero_dir.exists():
        raise SystemExit(f"Zotero 数据目录不存在：{args.zotero_dir}")

    out_root = args.out_root or (ROOT / "outputs")
    out_root = Path(out_root)

    prepare_cmd = [
        sys.executable,
        str(SCRIPTS / "prepare_zotero_paper.py"),
        "--zotero-dir",
        str(args.zotero_dir),
        "--query",
        args.query,
        "--out-root",
        str(out_root),
    ]
    if args.slug:
        prepare_cmd.extend(["--slug", args.slug])
    if args.no_render:
        prepare_cmd.append("--no-render")

    print("Preparing Zotero paper artifacts...")
    prepared_stdout = run(prepare_cmd)
    metadata = json.loads(prepared_stdout)

    out_dir = Path(metadata["out_dir"])
    summary_date = datetime.now().strftime("%Y年%m月%d日")
    fields = metadata.get("fields", {})
    attachment = metadata.get("attachment", {})
    creators = metadata.get("creators", [])

    english_title = metadata.get("title") or field(fields, "title") or args.query
    doi = metadata.get("doi") or field(fields, "DOI", "doi")
    doi_url = f"https://doi.org/{doi}" if doi else "待补充"
    authors = ", ".join(creators) if creators else "待补充"
    summary_path = out_dir / "summary.md"
    docx_path = out_dir / f"{out_dir.name}_文献总结_{datetime.now().strftime('%Y%m%d')}.docx"

    values = {
        "summary_date": summary_date,
        "query": args.query,
        "english_title": english_title,
        "chinese_title": "待翻译",
        "doi": doi or "待补充",
        "doi_url": doi_url,
        "journal": field(fields, "publicationTitle", "journalAbbreviation", "proceedingsTitle") or "待补充",
        "impact_factor": "待查询",
        "year_volume": " ".join(x for x in [field(fields, "date", "year"), field(fields, "volume"), field(fields, "issue")] if x) or "待补充",
        "authors": authors,
        "publication_date": field(fields, "date") or "待补充",
        "reference_summary": "待总结",
        "keywords": field(fields, "keywords") or "待补充",
        "author_keywords": "待补充",
        "research_direction": "待归纳",
        "discipline_detail": "待归纳",
        "classification_number": "待判定",
        "concise_content": "待总结",
        "selection_reason": "待说明该文为何属于高质量文献。",
        "method_1": "待总结",
        "method_2": "待总结",
        "method_3": "待总结",
        "method_4": "待总结",
        "figure_1_title": "待命名",
        "figure_1_alt": "待命名",
        "figure_1_path": "figures/figure_1.png",
        "figure_1_note": "待总结",
        "figure_2_title": "待命名",
        "figure_2_alt": "待命名",
        "figure_2_path": "figures/figure_2.png",
        "figure_2_note": "待总结",
        "innovation_1": "待总结",
        "innovation_2": "待总结",
        "innovation_3": "待总结",
        "innovation_4": "待总结",
        "improvement_direction": "待总结",
        "writing_intro": "待总结",
        "writing_method": "待总结",
        "writing_experiment": "待总结",
        "writing_figures": "待总结",
        "local_pdf_path": attachment.get("pdf_path", "待补充"),
        "local_text_path": metadata.get("text_path", "待补充"),
        "local_pages_dir": metadata.get("pages_dir", "待补充"),
        "local_figures_dir": metadata.get("figures_dir", "待补充"),
        "summary_path": str(summary_path),
        "docx_path": str(docx_path),
    }

    if not summary_path.exists():
        template = (TEMPLATES / "summary_template.md").read_text(encoding="utf-8")
        summary_path.write_text(fill_template(template, values), encoding="utf-8")

    task_path = out_dir / "codex_task.md"
    task_template = (TEMPLATES / "codex_task_template.md").read_text(encoding="utf-8")
    task_path.write_text(fill_template(task_template, values), encoding="utf-8")

    print(f"Output folder: {out_dir}")
    print(f"Summary draft: {summary_path}")
    print(f"Codex task prompt: {task_path}")

    if args.export_docx:
        print("Exporting DOCX...")
        run([
            sys.executable,
            str(SCRIPTS / "summary_md_to_docx.py"),
            "--summary",
            str(summary_path),
            "--output",
            str(docx_path),
        ])
        print(f"DOCX: {docx_path}")

    if args.upload_feishu:
        if not os.environ.get("FEISHU_APP_ID") or not os.environ.get("FEISHU_APP_SECRET"):
            raise SystemExit("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET。请写入 .env.local 或系统环境变量。")
        if not docx_path.exists():
            raise SystemExit(f"没有找到 DOCX，请先导出：{docx_path}")
        print("Uploading to Feishu...")
        upload_stdout = run([sys.executable, str(SCRIPTS / "upload_to_feishu.py"), "--file", str(docx_path)])
        print(upload_stdout)


if __name__ == "__main__":
    main()
