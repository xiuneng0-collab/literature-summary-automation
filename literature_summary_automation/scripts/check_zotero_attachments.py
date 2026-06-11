#!/usr/bin/env python
"""Check and optionally repair Zotero PDF attachment paths.

By default, repair mode does not edit zotero.sqlite. It restores missing PDFs
to the exact storage path already recorded by Zotero. With --relink-paths, the
script first backs up zotero.sqlite and then updates paths only when the real
PDF is already inside the same Zotero attachment folder.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
except ImportError:  # pragma: no cover - handled at runtime
    requests = None


PDF_CTYPES = {"application/pdf", "application/x-pdf"}
USER_AGENT = "Mozilla/5.0 ZoteroAttachmentCheck/1.0"


class PdfLinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        attr = dict(attrs)
        href = attr.get("href")
        if not href:
            return
        text = " ".join(str(v) for v in attr.values()).lower()
        href_l = href.lower()
        if "pdf" in href_l or "pdf" in text:
            self.links.append(urljoin(self.base_url, href))


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


def copy_db(zotero_dir: Path) -> Path:
    src = zotero_dir / "zotero.sqlite"
    if not src.exists():
        raise FileNotFoundError(f"找不到 Zotero 数据库：{src}")
    fd, tmp_name = tempfile.mkstemp(prefix="zotero-attachment-check-", suffix=".sqlite")
    os.close(fd)
    tmp = Path(tmp_name)
    shutil.copy2(src, tmp)
    return tmp


def rows_to_dict(rows) -> dict[str, str]:
    return {str(k): str(v) for k, v in rows if v is not None}


def item_fields(cur: sqlite3.Cursor, item_id: int | None) -> dict[str, str]:
    if item_id is None:
        return {}
    rows = cur.execute(
        """
        SELECT f.fieldName, v.value
        FROM itemData d
        JOIN fields f ON f.fieldID=d.fieldID
        JOIN itemDataValues v ON v.valueID=d.valueID
        WHERE d.itemID=?
        """,
        (item_id,),
    ).fetchall()
    return rows_to_dict(rows)


def creators_for_item(cur: sqlite3.Cursor, item_id: int | None) -> list[str]:
    if item_id is None:
        return []
    rows = cur.execute(
        """
        SELECT c.firstName, c.lastName
        FROM itemCreators ic
        JOIN creators c ON c.creatorID=ic.creatorID
        WHERE ic.itemID=?
        ORDER BY ic.orderIndex
        """,
        (item_id,),
    ).fetchall()
    names = []
    for first, last in rows:
        name = " ".join(x for x in [first, last] if x)
        if name:
            names.append(name)
    return names


def resolve_attachment_path(zotero_dir: Path, attachment_key: str, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    if raw_path.startswith("storage:"):
        return zotero_dir / "storage" / attachment_key / raw_path.split("storage:", 1)[1]
    if raw_path.startswith("attachments:"):
        return zotero_dir / raw_path.split("attachments:", 1)[1]
    p = Path(raw_path)
    return p if p.is_absolute() else zotero_dir / p


def normalize_name(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[\s_：:;,.，。/\\()（）\\[\\]{}'\"`~!！?？-]+", "", value)
    return value


def selected_parent_keys(cur: sqlite3.Cursor, queries: list[str]) -> set[str]:
    keys: set[str] = set()
    for query in queries:
        like = f"%{query}%"
        rows = cur.execute(
            """
            SELECT DISTINCT i.key
            FROM items i
            LEFT JOIN itemData d ON d.itemID=i.itemID
            LEFT JOIN fields f ON f.fieldID=d.fieldID
            LEFT JOIN itemDataValues v ON v.valueID=d.valueID
            WHERE i.key=? OR v.value LIKE ?
            """,
            (query, like),
        ).fetchall()
        keys.update(row[0] for row in rows if row[0])
    return keys


def latest_keys_and_urls(path: Path | None) -> tuple[set[str], dict[str, str]]:
    if not path or not path.exists():
        return set(), {}
    data = json.loads(path.read_text(encoding="utf-8"))
    keys: set[str] = set()
    urls: dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        key = row.get("parentKey")
        if not key:
            continue
        keys.add(str(key))
        if row.get("pdf"):
            urls[str(key)] = str(row["pdf"])
    return keys, urls


def all_pdf_records(cur: sqlite3.Cursor, zotero_dir: Path) -> list[dict]:
    rows = cur.execute(
        """
        SELECT p.itemID, p.key, a.itemID, a.key, ia.path, ia.contentType
        FROM itemAttachments ia
        JOIN items a ON a.itemID=ia.itemID
        LEFT JOIN items p ON p.itemID=ia.parentItemID
        WHERE ia.contentType='application/pdf'
        ORDER BY ia.itemID DESC
        """
    ).fetchall()
    out = []
    for parent_id, parent_key, attachment_id, attachment_key, raw_path, content_type in rows:
        fields = item_fields(cur, parent_id)
        expected = resolve_attachment_path(zotero_dir, attachment_key, raw_path)
        out.append(
            {
                "parent_id": parent_id,
                "parentKey": parent_key,
                "attachment_id": attachment_id,
                "attachmentKey": attachment_key,
                "path": raw_path,
                "contentType": content_type,
                "expectedPath": str(expected) if expected else "",
                "exists": bool(expected and expected.exists()),
                "title": fields.get("title", ""),
                "doi": fields.get("DOI") or fields.get("doi") or "",
                "url": fields.get("url", ""),
                "journal": fields.get("publicationTitle", ""),
                "date": fields.get("date", ""),
                "creators": creators_for_item(cur, parent_id),
            }
        )
    return out


def parents_without_pdf(cur: sqlite3.Cursor, keys: set[str]) -> list[dict]:
    if not keys:
        return []
    qmarks = ",".join("?" for _ in keys)
    rows = cur.execute(
        f"""
        SELECT i.itemID, i.key
        FROM items i
        WHERE i.key IN ({qmarks})
          AND NOT EXISTS (
            SELECT 1
            FROM itemAttachments ia
            WHERE ia.parentItemID=i.itemID
              AND ia.contentType='application/pdf'
          )
        """,
        tuple(keys),
    ).fetchall()
    out = []
    for item_id, key in rows:
        fields = item_fields(cur, item_id)
        out.append(
            {
                "parent_id": item_id,
                "parentKey": key,
                "title": fields.get("title", ""),
                "doi": fields.get("DOI") or fields.get("doi") or "",
                "url": fields.get("url", ""),
                "status": "NO_PDF_ATTACHMENT_ROW",
            }
        )
    return out


def candidate_roots(zotero_dir: Path, extra_roots: list[Path]) -> list[Path]:
    roots = [zotero_dir / "storage", Path.home() / "Downloads", Path.home() / "Desktop", *extra_roots]
    seen = set()
    out = []
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return out


def pdfs_in_dir(path: Path) -> list[Path]:
    try:
        if not path.exists() or not path.is_dir():
            return []
        return sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    except (OSError, PermissionError):
        return []


def storage_path_for(actual_pdf: Path, expected: Path) -> str | None:
    """Return a Zotero storage: path when the PDF is inside the attachment folder."""
    try:
        if actual_pdf.parent.resolve() != expected.parent.resolve():
            return None
    except OSError:
        return None
    return f"storage:{actual_pdf.name}"


def find_local_pdf(record: dict, roots: list[Path]) -> Path | None:
    expected = Path(record["expectedPath"])
    same_folder_pdfs = [p for p in pdfs_in_dir(expected.parent) if p.resolve() != expected.resolve()]
    if len(same_folder_pdfs) == 1:
        return same_folder_pdfs[0]
    filename = expected.name
    normalized_filename = normalize_name(filename)
    normalized_title = normalize_name(record.get("title") or "")
    best: Path | None = None
    for root in roots:
        try:
            for p in root.rglob("*.pdf"):
                if p.resolve() == expected.resolve():
                    continue
                name_norm = normalize_name(p.name)
                if p.name == filename or name_norm == normalized_filename:
                    return p
                if normalized_title and normalized_title in name_norm:
                    best = best or p
        except (OSError, PermissionError):
            continue
    return best


def backup_db(zotero_dir: Path) -> Path:
    src = zotero_dir / "zotero.sqlite"
    if not src.exists():
        raise FileNotFoundError(f"Cannot find Zotero database: {src}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = zotero_dir / f"zotero.sqlite.codex-pathfix-{stamp}.bak"
    shutil.copy2(src, dest)
    return dest


def relink_record(zotero_dir: Path, record: dict, actual_pdf: Path) -> tuple[bool, str]:
    expected = Path(record["expectedPath"])
    new_path = storage_path_for(actual_pdf, expected)
    if not new_path:
        return False, "SKIPPED_RELINK_OUTSIDE_ATTACHMENT_FOLDER"
    if new_path == record.get("path"):
        return False, "SKIPPED_RELINK_UNCHANGED"
    con = sqlite3.connect(zotero_dir / "zotero.sqlite", timeout=10)
    try:
        cur = con.cursor()
        cur.execute(
            "UPDATE itemAttachments SET path=? WHERE itemID=?",
            (new_path, record["attachment_id"]),
        )
        con.commit()
    finally:
        con.close()
    record["oldPath"] = record.get("path")
    record["path"] = new_path
    record["expectedPath"] = str(expected.parent / actual_pdf.name)
    record["exists"] = True
    return True, "RELINKED_TO_EXISTING_FILE"


def doi_pdf_candidates(doi: str, url: str) -> list[str]:
    out = []
    doi = doi.strip()
    if doi:
        out.append(f"https://doi.org/{doi}")
    if url:
        out.append(url)
    # Common MDPI DOI pattern, e.g. 10.3390/s23031352 -> sensors-23-01352.pdf.
    m = re.match(r"10\.3390/([a-z]+)(\d+)$", doi, re.I)
    if m:
        journal_code, digits = m.groups()
        if len(digits) >= 7:
            volume = str(int(digits[:-6]))
            issue = str(int(digits[-6:-4]))
            article = str(int(digits[-4:]))
            journal_map = {
                "s": ("sensors", "1424-8220"),
                "electronics": ("electronics", "2079-9292"),
                "rs": ("remotesensing", "2072-4292"),
            }
            journal = journal_map.get(journal_code.lower(), (journal_code.lower(), ""))[0]
            issn = journal_map.get(journal_code.lower(), ("", ""))[1]
            article_file = f"{int(article):05d}"
            out.insert(
                0,
                f"https://mdpi-res.com/d_attachment/{journal}/{journal}-{int(volume):02d}-{article_file}/article_deploy/{journal}-{int(volume):02d}-{article_file}.pdf",
            )
            out.insert(
                1,
                f"https://mdpi-res.com/d_attachment/{journal}/{journal}-{int(volume)}-{article_file}/article_deploy/{journal}-{int(volume)}-{article_file}.pdf",
            )
            if issn:
                out.append(f"https://www.mdpi.com/{issn}/{int(volume)}/{int(issue)}/{int(article)}/pdf")
    return list(dict.fromkeys(out))


def fetch_pdf_links(url: str) -> list[str]:
    if not requests:
        return []
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25, allow_redirects=True)
    except requests.RequestException:
        return []
    ctype = r.headers.get("content-type", "").split(";")[0].lower()
    if ctype in PDF_CTYPES or r.content.startswith(b"%PDF"):
        return [r.url]
    parser = PdfLinkParser(r.url)
    try:
        parser.feed(r.text)
    except Exception:
        return []
    return parser.links


def download_pdf(urls: list[str], dest: Path) -> tuple[bool, str]:
    if not requests:
        return False, "缺少 requests：请运行 python -m pip install requests"
    tried: list[str] = []
    expanded: list[str] = []
    for url in urls:
        expanded.append(url)
        expanded.extend(fetch_pdf_links(url))
    for url in list(dict.fromkeys(expanded)):
        tried.append(url)
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60, allow_redirects=True)
        except requests.RequestException as exc:
            continue
        ctype = r.headers.get("content-type", "").split(";")[0].lower()
        looks_pdf = ctype in PDF_CTYPES or r.content.startswith(b"%PDF") or mimetypes.guess_type(url)[0] in PDF_CTYPES
        if r.status_code == 200 and looks_pdf and len(r.content) > 1024:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return True, r.url
    return False, "下载失败或返回的不是 PDF；已尝试：" + " | ".join(tried[:6])


def repair_record(
    record: dict,
    roots: list[Path],
    pdf_url_map: dict[str, str],
    allow_download: bool,
    relink_paths: bool,
    zotero_dir: Path,
) -> dict:
    expected = Path(record["expectedPath"])
    if expected.exists():
        record["status"] = "OK"
        return record
    local = find_local_pdf(record, roots)
    if local:
        if relink_paths:
            ok, status = relink_record(zotero_dir, record, local)
            if ok:
                record["status"] = status
                record["repairSource"] = str(local)
                return record
            record["relinkNote"] = status
        expected.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local, expected)
        record["status"] = "FIXED_BY_LOCAL_COPY"
        record["repairSource"] = str(local)
        record["exists"] = expected.exists()
        return record
    if allow_download:
        urls = []
        if record.get("parentKey") in pdf_url_map:
            urls.append(pdf_url_map[record["parentKey"]])
        urls.extend(doi_pdf_candidates(record.get("doi", ""), record.get("url", "")))
        ok, source = download_pdf(urls, expected)
        if ok:
            record["status"] = "FIXED_BY_DOWNLOAD"
            record["repairSource"] = source
            record["exists"] = expected.exists()
            return record
        record["status"] = "MISSING_DOWNLOAD_FAILED"
        record["repairNote"] = source
        return record
    record["status"] = "MISSING"
    return record


def write_reports(report: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    json_path = out_dir / f"zotero_attachment_check_{stamp}.json"
    md_path = out_dir / f"zotero_attachment_check_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# Zotero 附件检查报告（{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}）",
        "",
        f"- 检查范围：{report['scope']}",
        f"- PDF 附件记录：{report['summary']['total_pdf_records']}",
        f"- 可直接打开：{report['summary']['ok']}",
        f"- 已修复：{report['summary']['fixed']}",
        f"- 仍缺失：{report['summary']['missing']}",
        f"- 无 PDF 附件记录：{report['summary']['no_pdf_attachment_rows']}",
        "",
        "## 仍需处理",
    ]
    unresolved = [r for r in report["records"] if r.get("status", "").startswith("MISSING")]
    for r in unresolved:
        lines.append(f"- `{r.get('parentKey')}` {r.get('title')} -> `{r.get('expectedPath')}`")
    if not unresolved:
        lines.append("- 无")
    if report["no_pdf_attachment_rows"]:
        lines.extend(["", "## 没有 PDF 附件记录"])
        for r in report["no_pdf_attachment_rows"]:
            lines.append(f"- `{r.get('parentKey')}` {r.get('title')} DOI: {r.get('doi') or '无'}")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parents[1]
    load_env_file(root / ".env.local")
    load_env_file(root / ".env")

    ap = argparse.ArgumentParser(description="检查并可选修复 Zotero PDF 附件路径。")
    ap.add_argument("--zotero-dir", default=os.environ.get("ZOTERO_DATA_DIR"), type=Path)
    ap.add_argument("--latest-json", type=Path, help="最近抓取列表 JSON，包含 parentKey 和可选 pdf URL。")
    ap.add_argument("--query", action="append", default=[], help="额外检查某个 Zotero key、标题或 DOI。可重复传入。")
    ap.add_argument("--all", action="store_true", help="检查 Zotero 全库 PDF 附件。")
    ap.add_argument("--repair", action="store_true", help="把找到或下载到的 PDF 放回 Zotero 记录的 storage 路径。")
    ap.add_argument("--download", action="store_true", help="修复时允许从 latest-json 的 pdf URL、DOI 或条目 URL 下载。")
    ap.add_argument("--relink-paths", action="store_true", help="备份 zotero.sqlite 后，把同一附件目录内已存在 PDF 的数据库路径改成真实文件名。")
    ap.add_argument("--search-root", action="append", default=[], type=Path, help="额外查找 PDF 的本地目录。可重复传入。")
    ap.add_argument("--report-dir", default=root / "reports", type=Path)
    args = ap.parse_args()

    if not args.zotero_dir:
        raise SystemExit("缺少 Zotero 数据目录。请在 .env.local 设置 ZOTERO_DATA_DIR，或运行时传 --zotero-dir。")
    if not args.zotero_dir.exists():
        raise SystemExit(f"Zotero 数据目录不存在：{args.zotero_dir}")

    latest_keys, pdf_url_map = latest_keys_and_urls(args.latest_json)
    tmp_db = copy_db(args.zotero_dir)
    try:
        con = sqlite3.connect(tmp_db)
        cur = con.cursor()
        keys = set(latest_keys)
        keys.update(selected_parent_keys(cur, args.query))
        records = all_pdf_records(cur, args.zotero_dir)
        if not args.all:
            records = [r for r in records if r.get("parentKey") in keys]
        no_pdf_rows = parents_without_pdf(cur, keys)
    finally:
        try:
            con.close()
        except Exception:
            pass
        tmp_db.unlink(missing_ok=True)

    roots = candidate_roots(args.zotero_dir, args.search_root)
    db_backup = ""
    if args.relink_paths:
        db_backup = str(backup_db(args.zotero_dir))
    checked = []
    for record in records:
        if record["exists"]:
            record["status"] = "OK"
        elif args.repair:
            record = repair_record(
                record,
                roots,
                pdf_url_map,
                allow_download=args.download,
                relink_paths=args.relink_paths,
                zotero_dir=args.zotero_dir,
            )
        else:
            record["status"] = "MISSING"
        checked.append(record)

    summary = {
        "total_pdf_records": len(checked),
        "ok": sum(1 for r in checked if r["status"] == "OK"),
        "fixed": sum(1 for r in checked if r["status"].startswith("FIXED")),
        "missing": sum(1 for r in checked if r["status"].startswith("MISSING")),
        "no_pdf_attachment_rows": len(no_pdf_rows),
    }
    scope_bits = []
    if args.all:
        scope_bits.append("全库")
    if latest_keys:
        scope_bits.append(f"最近抓取 JSON：{len(latest_keys)} 条")
    if args.query:
        scope_bits.append("查询：" + "；".join(args.query))
    report = {
        "scope": " + ".join(scope_bits) or "未指定范围",
        "zotero_dir": str(args.zotero_dir),
        "repair": bool(args.repair),
        "download": bool(args.download),
        "relink_paths": bool(args.relink_paths),
        "db_backup": db_backup,
        "summary": summary,
        "records": checked,
        "no_pdf_attachment_rows": no_pdf_rows,
    }
    json_path, md_path = write_reports(report, args.report_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()
