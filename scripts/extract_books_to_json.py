#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 SQLite 中的书籍（zysjcell 有书名标记的）全部提取为 JSON，每本书一个文件。

用法:
  python scripts/extract_books_to_json.py
  python scripts/extract_books_to_json.py --output references/books_json
  python scripts/extract_books_to_json.py --cell-id 98   # 只提取单本（调试）
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import sqlite3
import sys
from pathlib import Path

# Windows 终端 UTF-8 修复
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass


def find_sqlite_path(sqlite_arg: str | None) -> Path:
    candidates = []
    if sqlite_arg:
        candidates.append(Path(sqlite_arg))
    candidates.extend([
        Path.home() / ".cache" / "zhongyishijia" / "20120413mssql.sqlite",
        Path(__file__).resolve().parent.parent / "references" / "raw" / "20120413mssql.sqlite",
    ])
    for c in candidates:
        if c and c.exists() and c.is_file():
            return c
    raise FileNotFoundError("找不到 20120413mssql.sqlite，请使用 --sqlite 参数指定路径。")


def b(val) -> str:
    """将 SQLite 原始值（bytes/str）转为 UTF-8 字符串"""
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)


def esc(text: str, limit: int = 0) -> str:
    """HTML 实体解码 + 清理 | 和换行"""
    text = html.unescape(text)
    text = re.sub(r"[|\n\r]", " ", text)
    text = text.strip()
    if limit > 0 and len(text) > limit:
        text = text[:limit] + "…"
    return text


def slugify(title: str) -> str:
    """书名转为安全的文件名 slug"""
    # 去除《》和特殊字符
    s = re.sub(r'[《》「」【】]', '', title)
    s = re.sub(r'[^\w一-鿿\s-]', '', s)
    s = re.sub(r'[\s]+', '_', s.strip())
    return s[:80]  # 限制长度


def extract_all_books(sqlite_path: Path, output_dir: Path, cell_id: int | None = None):
    """批量提取所有书籍为 JSON 文件"""
    conn = sqlite3.connect(str(sqlite_path))
    conn.text_factory = bytes
    cur = conn.cursor()

    # 查询书籍列表（有书名标记的 Cell_ID）
    if cell_id is not None:
        query = """
            SELECT DISTINCT c.Cell_ID, c.Cell_BiaoTi, c.Cell_WenJianJia
            FROM zysjcell c
            JOIN zysjllsj l ON l.TypeID = c.Cell_ID
            WHERE c.Cell_BiaoTi LIKE '《%》%' AND c.Cell_ID = ?
            ORDER BY c.Cell_BiaoTi
        """
        cur.execute(query, (cell_id,))
    else:
        query = """
            SELECT DISTINCT c.Cell_ID, c.Cell_BiaoTi, c.Cell_WenJianJia
            FROM zysjcell c
            JOIN zysjllsj l ON l.TypeID = c.Cell_ID
            WHERE c.Cell_BiaoTi LIKE '《%》%'
            ORDER BY c.Cell_BiaoTi
        """
        cur.execute(query)

    books = cur.fetchall()
    print(f"找到 {len(books)} 本书", file=sys.stderr)

    output_dir.mkdir(parents=True, exist_ok=True)

    for book_idx, (cell_id_val, title_raw, path_raw) in enumerate(books):
        cell_id_int = cell_id_val
        title = b(title_raw)
        path = b(path_raw)

        # 查询该书的所有内容，按 BM1/BM2/BM3/BM4 排序
        cur.execute("""
            SELECT l.BM1, l.BM2, l.BM3, l.BM4, l.BiaoTi, l.NeiRong
            FROM zysjllsj l
            WHERE l.TypeID = ?
            ORDER BY l.BM1, l.BM3, l.BM4
        """, (cell_id_int,))
        rows = cur.fetchall()

        if not rows:
            continue

        # 按 BM2（章）分组
        chapters: dict[int, dict] = {}
        for r in rows:
            bm1, bm2, bm3, bm4, biaoti_raw, neirong_raw = r
            bt = esc(b(biaoti_raw))
            nr = esc(b(neirong_raw), 2000)  # 内容截断到2000字

            if bm2 not in chapters:
                chapters[bm2] = {"bm2": bm2, "sections": {}}

            if bm3 not in chapters[bm2]["sections"]:
                chapters[bm2]["sections"][bm3] = {"bm3": bm3, "entries": []}

            chapters[bm2]["sections"][bm3]["entries"].append({
                "bm4": bm4,
                "title": bt,
                "content": nr,
            })

        # 转换为有序列表
        chapters_list = []
        for bm2 in sorted(chapters.keys()):
            ch = chapters[bm2]
            sections_list = []
            for bm3 in sorted(ch["sections"].keys()):
                sec = ch["sections"][bm3]
                sections_list.append(sec)
            chapters_list.append({
                "chapter": bm2,
                "sections": sections_list,
            })

        book_obj = {
            "cell_id": cell_id_int,
            "title": title,
            "path": path,
            "record_count": len(rows),
            "chapter_count": len(chapters_list),
            "chapters": chapters_list,
        }

        # 文件名
        slug = slugify(title)
        filename = f"{cell_id_int:04d}_{slug}.json"
        out_path = output_dir / filename

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(book_obj, f, ensure_ascii=False, indent=2)

        print(f"  [{book_idx+1}/{len(books)}] {title} → {out_path.name} ({len(rows)} 条)", file=sys.stderr)

    conn.close()
    print(f"\n完成！共提取 {len(books)} 本书到 {output_dir}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="将 SQLite 中的书籍提取为 JSON，每本书一个文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--sqlite",
        help="SQLite 文件路径（默认自动查找）",
    )
    parser.add_argument(
        "--output",
        default="references/books_json",
        help="输出目录（默认 references/books_json）",
    )
    parser.add_argument(
        "--cell-id",
        type=int,
        default=None,
        help="只提取指定 Cell_ID 的书（调试用）",
    )
    args = parser.parse_args()

    sqlite_path = find_sqlite_path(args.sqlite)
    output_dir = Path(args.output).resolve()

    print(f"SQLite: {sqlite_path}", file=sys.stderr)
    print(f"输出: {output_dir}", file=sys.stderr)

    extract_all_books(sqlite_path, output_dir, args.cell_id)


if __name__ == "__main__":
    main()
