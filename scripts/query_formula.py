#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桂枝人参汤 — 标准化方剂/条文查询脚本

用法:
  python scripts/query_formula.py <关键词>
  python scripts/query_formula.py 桂枝人参汤
  python scripts/query_formula.py 小柴胡汤

输出格式: 按朝代从古至今排序的 Markdown 表格
  朝代 | 著作 | 作者 | 原文论述摘要 | 卡片类型
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys

# Windows 终端修复: 确保 stdout 输出 UTF-8
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass
from pathlib import Path
from typing import Optional

from _source_map import (
    DYNASTY_ORDER,
    SOURCE_MAP,
    TYPEID_MAP,
    identify_source,
    sort_key,
)


def clean_summary(text: str, max_len: int = 300) -> str:
    """清理摘要: 去 HTML 标签, 解 HTML 实体, 截取合理长度"""
    text = html.unescape(text)
    text = text.replace("[br]", " ").replace("[b]", "").replace("[/b]", "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def search_cards(keyword: str, cards_path: Path) -> list[dict]:
    """搜索 evidence_cards.jsonl"""
    matches = []
    for line in cards_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = " ".join(
            str(item.get(k) or "") for k in ["card_type", "title", "summary", "source_ref"]
        )
        if keyword in text:
            matches.append(item)
    return matches


# ── 主流程 ──

def main() -> None:
    parser = argparse.ArgumentParser(
        description="中医方剂/条文标准化查询 — 按朝代排序输出医家论述",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/query_formula.py 桂枝人参汤
  python scripts/query_formula.py 小柴胡汤
  python scripts/query_formula.py "协热利"
        """,
    )
    parser.add_argument("keyword", help="要查询的方剂名/条文名/关键词")
    parser.add_argument(
        "--references-dir",
        default="../references",
        help="references 目录路径 (默认 ../references)",
    )
    parser.add_argument(
        "--max-cards",
        type=int,
        default=10,
        help="每个朝代最多输出多少条 (默认 10)",
    )
    args = parser.parse_args()

    base = (Path(__file__).resolve().parent / args.references_dir).resolve()
    cards_path = base / "text_distillation" / "evidence_cards.jsonl"

    if not cards_path.exists():
        print(f"错误: 找不到数据文件 {cards_path}")
        print("请检查 --references-dir 参数")
        return

    print(f"正在搜索「{args.keyword}」...", file=__import__("sys").stderr)
    matches = search_cards(args.keyword, cards_path)
    print(f"找到 {len(matches)} 条相关记录\n", file=__import__("sys").stderr)

    if not matches:
        print(f"未找到与「{args.keyword}」相关的记录。")
        return

    # 排序
    matches.sort(key=sort_key)

    # ── 输出标题 ──
    print(f"# 「{args.keyword}」历代医家论述汇总\n")
    print(f"> 共检索到 **{len(matches)} 条** 相关证据卡片，以下按朝代从古至今排列\n")
    print()
    print("| 朝代 | 著作 | 作者 | 原文论述摘要 | 卡片类型 |")
    print("|:----:|:----:|:----:|:-----------|:--------:|")

    # 按朝代分组去重输出
    prev_dynasty = ""
    count_in_dynasty = 0
    for card in matches:
        dyn, book, author = identify_source(card)

        # 新朝代标记
        if dyn != prev_dynasty:
            prev_dynasty = dyn
            count_in_dynasty = 0

        # 限流
        count_in_dynasty += 1
        if count_in_dynasty > args.max_cards:
            continue

        title = card.get("title", "")
        summary = card.get("summary", "")
        card_type = card.get("card_type", "")

        summary_clean = clean_summary(summary)
        summary_clean = summary_clean.replace("|", "｜")

        print(f"| {dyn} | {book} | {author} | {summary_clean} | {card_type} |")

    print()
    print("---")
    print(f"*数据来源：中医世家知识库 evidence_cards.jsonl（317,580 张卡片）*")
    print(f"*查询关键词：{args.keyword}*")


if __name__ == "__main__":
    main()
