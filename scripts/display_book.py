#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
伤寒论内容展示脚本

用法:
  python scripts/display_book.py 0098
  python scripts/display_book.py 0098 --no-content
  python scripts/display_book.py 0098 --chapter 1
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass


def find_book_json(cell_id: str) -> Path:
    """在 references/books_json/ 中查找指定 Cell_ID 的书籍"""
    books_dir = Path(__file__).resolve().parent.parent / "references" / "books_json"
    # 精确匹配: 0009_xxx.json
    pattern = f"{cell_id.zfill(4)}_*.json"
    matches = list(books_dir.glob(pattern))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"找不到 Cell_ID={cell_id} 的书籍JSON")


def display_book(cell_id: str, show_content: bool = True, chapter_filter: int | None = None):
    """展示书籍内容"""
    book_path = find_book_json(cell_id)
    with open(book_path, encoding="utf-8") as f:
        book = json.load(f)

    title = book["title"].replace("《", "").replace("》", "")
    print(f"{'='*60}")
    print(f"  《{title}》")
    print(f"{'='*60}")
    print(f"  共 {book['record_count']} 条 · {book['chapter_count']} 章节")
    print(f"  来源: {book['path']}")
    print()

    for ch in book["chapters"]:
        bm2 = ch["chapter"]
        if chapter_filter is not None and bm2 != chapter_filter:
            continue

        # 打印章节名（从第一个条目的标题推断）
        first_title = ""
        for sec in ch.get("sections", []):
            for e in sec.get("entries", []):
                first_title = e.get("title", "").strip()
                if first_title:
                    break
            if first_title:
                break

        print(f"{'─'*60}")
        print(f"  【章节 BM2={bm2}】  {first_title}")
        print(f"{'─'*60}")

        for sec in ch.get("sections", []):
            bm3 = sec["bm3"]
            entries = sec.get("entries", [])

            # 节标题（bm3=0通常是章节名，跳过）
            if bm3 == 0:
                # 显示所有 bm3=0 的条目（通常是章节标题或卷名）
                for e in entries:
                    t = e.get("title", "").strip()
                    c = e.get("content", "").strip()
                    if t:
                        print(f"\n  ▎{t}")
                    if c and show_content:
                        print(f"    {c[:200]}{'…' if len(c) > 200 else ''}")
                continue

            # bm3 > 0 是正文条目
            for e in entries:
                bm4 = e.get("bm4", "")
                entry_title = e.get("title", "").strip()
                entry_content = e.get("content", "").strip()

                if entry_title:
                    print(f"\n  ◆ {entry_title}")
                if entry_content and show_content:
                    # 内容分段落显示，每行约50字
                    lines = [entry_content[i:i+50] for i in range(0, len(entry_content), 50)]
                    for line in lines:
                        print(f"    {line}")
        print()


def main():
    parser = argparse.ArgumentParser(description="展示伤寒论完整内容")
    parser.add_argument("cell_id", default="0098", nargs="?", help="Cell_ID（默认 0098=伤寒论）")
    parser.add_argument("--no-content", action="store_true", help="只显示标题，不显示正文")
    parser.add_argument("--chapter", type=int, default=None, help="只看指定章节 BM2")
    args = parser.parse_args()

    display_book(
        cell_id=args.cell_id.zfill(4),
        show_content=not args.no_content,
        chapter_filter=args.chapter,
    )


if __name__ == "__main__":
    main()
