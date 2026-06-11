#!/usr/bin/env python
"""Prepare a Zotero paper PDF for Codex literature-summary work.

Finds a Zotero item by title/DOI/key, resolves its local PDF attachment,
extracts text, renders pages, and writes a metadata JSON file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-")[:80] or "paper"


def copy_db(zotero_dir: Path) -> Path:
    src = zotero_dir / "zotero.sqlite"
    if not src.exists():
        raise FileNotFoundError(f"Cannot find Zotero database: {src}")
    fd, tmp_name = tempfile.mkstemp(prefix="zotero-summary-", suffix=".sqlite")
    os.close(fd)
    tmp = Path(tmp_name)
    shutil.copy2(src, tmp)
    return tmp


def rows_to_dict(rows):
    out = {}
    for field, value in rows:
        out[field] = value
    return out


def find_item(con: sqlite3.Connection, query: str):
    cur = con.cursor()
    like = f"%{query}%"
    candidates = cur.execute(
        """
        SELECT DISTINCT i.itemID, i.key
        FROM items i
        LEFT JOIN itemData d ON d.itemID=i.itemID
        LEFT JOIN fields f ON f.fieldID=d.fieldID
        LEFT JOIN itemDataValues v ON v.valueID=d.valueID
        WHERE i.key = ?
           OR v.value LIKE ?
        ORDER BY i.itemID DESC
        LIMIT 20
        """,
        (query, like),
    ).fetchall()
    if not candidates:
        return None
    scored = []
    q = query.lower()
    for item_id, key in candidates:
        fields = rows_to_dict(
            cur.execute(
                """
                SELECT f.fieldName, v.value
                FROM itemData d
                JOIN fields f ON f.fieldID=d.fieldID
                JOIN itemDataValues v ON v.valueID=d.valueID
                WHERE d.itemID=?
                """,
                (item_id,),
            ).fetchall()
        )
        hay = " ".join([key or "", *(str(v) for v in fields.values())]).lower()
        score = 0
        if key == query:
            score += 100
        if q in hay:
            score += 50
        if fields.get("title", "").lower() == q:
            score += 100
        scored.append((score, item_id, key, fields))
    scored.sort(reverse=True)
    return scored[0][1:]


def creators_for_item(con: sqlite3.Connection, item_id: int):
    cur = con.cursor()
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


def find_pdf_attachment(con: sqlite3.Connection, zotero_dir: Path, item_id: int):
    cur = con.cursor()
    rows = cur.execute(
        """
        SELECT ia.itemID, i.key, ia.path, ia.contentType
        FROM itemAttachments ia
        JOIN items i ON i.itemID=ia.itemID
        WHERE ia.parentItemID=? AND ia.contentType='application/pdf'
        ORDER BY ia.itemID DESC
        """,
        (item_id,),
    ).fetchall()
    for attachment_id, attachment_key, path, content_type in rows:
        resolved = resolve_attachment_path(zotero_dir, attachment_key, path)
        if resolved and resolved.exists():
            return {
                "attachment_item_id": attachment_id,
                "attachment_key": attachment_key,
                "zotero_path": path,
                "pdf_path": str(resolved),
            }
    # Fallback: search storage recursively by title-ish attachment path.
    for attachment_id, attachment_key, path, content_type in rows:
        filename = path.split("storage:", 1)[-1] if path else ""
        if filename:
            matches = list((zotero_dir / "storage").rglob(filename))
            if matches:
                return {
                    "attachment_item_id": attachment_id,
                    "attachment_key": attachment_key,
                    "zotero_path": path,
                    "pdf_path": str(matches[0]),
                }
    return None


def resolve_attachment_path(zotero_dir: Path, attachment_key: str, path: str | None):
    if not path:
        return None
    if path.startswith("storage:"):
        return zotero_dir / "storage" / attachment_key / path.split("storage:", 1)[1]
    if path.startswith("attachments:"):
        return zotero_dir / path.split("attachments:", 1)[1]
    p = Path(path)
    return p if p.is_absolute() else zotero_dir / p


def which(names):
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def run(cmd):
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def extract_text(pdf: Path, output: Path):
    pdftotext = which(["pdftotext"])
    if not pdftotext:
        raise RuntimeError("pdftotext not found. Install Poppler or TeX Live tools.")
    run([pdftotext, "-layout", "-enc", "UTF-8", str(pdf), str(output)])


def render_pages(pdf: Path, output_dir: Path):
    pdftoppm = which(["pdftoppm"])
    if not pdftoppm:
        raise RuntimeError("pdftoppm not found. Install Poppler or TeX Live tools.")
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "page"
    run([pdftoppm, "-png", "-r", "150", str(pdf), str(prefix)])
    for p in output_dir.glob("page-*.png"):
        m = re.search(r"page-(\d+)\.png$", p.name)
        if m:
            new = output_dir / f"page-{int(m.group(1)):02d}.png"
            if new != p:
                p.rename(new)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--zotero-dir", required=True, type=Path)
    ap.add_argument("--query", required=True, help="Title, DOI, Zotero item key, or partial title")
    ap.add_argument("--out-root", required=True, type=Path)
    ap.add_argument("--slug", default=None)
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    zotero_dir = args.zotero_dir
    tmp_db = copy_db(zotero_dir)
    try:
        con = sqlite3.connect(tmp_db)
        found = find_item(con, args.query)
        if not found:
            raise SystemExit(f"No Zotero item found for query: {args.query}")
        item_id, item_key, fields = found
        creators = creators_for_item(con, item_id)
        attachment = find_pdf_attachment(con, zotero_dir, item_id)
        if not attachment:
            raise SystemExit("Found Zotero item, but no local PDF attachment was found.")
    finally:
        try:
            con.close()
        except Exception:
            pass
        tmp_db.unlink(missing_ok=True)

    title = fields.get("title") or args.query
    slug = args.slug or slugify(title)
    out_dir = args.out_root / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    pages_dir = out_dir / "pdf_pages"
    text_path = out_dir / "zotero_pdf_text.txt"
    pdf_path = Path(attachment["pdf_path"])

    extract_text(pdf_path, text_path)
    if not args.no_render:
        render_pages(pdf_path, pages_dir)

    metadata = {
        "item_id": item_id,
        "item_key": item_key,
        "fields": fields,
        "creators": creators,
        "attachment": attachment,
        "title": title,
        "doi": fields.get("DOI") or fields.get("doi"),
        "out_dir": str(out_dir),
        "text_path": str(text_path),
        "pages_dir": str(pages_dir),
        "figures_dir": str(figures_dir),
    }
    metadata_path = out_dir / "paper_metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
