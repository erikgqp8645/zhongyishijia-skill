#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桂枝人参汤 — 标准化方剂/条文查询脚本

用法:
  python scripts/formula_query.py <关键词>
  python scripts/formula_query.py 桂枝人参汤
  python scripts/formula_query.py 小柴胡汤

  # 完整报告模式（生成结构化 Markdown 文档）
  python scripts/formula_query.py 甘草泻心汤 --full-report

输出格式:
  - 默认: 按朝代从古至今排序的 Markdown 表格
  - --full-report: 完整结构化 Markdown 文档（含病机归纳、方剂演变、临床应用）
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

from _sqlite_utils import setup_windows_stdout
from _source_map import (
    DYNASTY_ORDER,
    SOURCE_MAP,
    TYPEID_MAP,
    identify_source,
    sort_key,
)

setup_windows_stdout()

# ── 模板路径 ──
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "templates" / "formula_report_template.md"


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


def get_time_span(matches: list[dict]) -> str:
    """推断时间跨度"""
    dynasties = set()
    for card in matches:
        dyn, _, _ = identify_source(card)
        if dyn != "待考":
            dynasties.add(dyn)
    if not dynasties:
        return "待考"
    # 按朝代顺序排序
    sorted_dyns = sorted(dynasties, key=lambda d: DYNASTY_ORDER.get(d, 99))
    if len(sorted_dyns) <= 2:
        return "、".join(sorted_dyns)
    return f"{sorted_dyns[0]}—{sorted_dyns[-1]}"


def group_by_dynasty(matches: list[dict]) -> dict[str, list[dict]]:
    """按朝代分组"""
    groups = defaultdict(list)
    for card in matches:
        dyn, book, author = identify_source(card)
        groups[dyn].append(card)
    return dict(groups)


def load_template() -> str:
    """加载报告模板"""
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    # 内联备用模板
    return ""


def generate_dynasty_sections(groups: dict[str, list[dict]], max_per_dynasty: int = 15) -> str:
    """生成朝代章节内容"""
    sections = []
    dynasty_names = {
        "东汉": "二、东汉时期",
        "晋": "三、晋代",
        "南北朝": "四、南北朝时期",
        "隋": "四、隋代",
        "唐": "五、唐代",
        "宋": "六、宋代",
        "金": "六、金代",
        "元": "七、元代",
        "明": "八、明代",
        "清": "九、清代",
        "民国": "十、民国时期",
        "现代": "十一、现代",
        "日本江户": "六、日本江户时期",
        "待考": "十二、其他/待考",
    }

    dynasty_order_sorted = sorted(groups.keys(), key=lambda d: DYNASTY_ORDER.get(d, 99))

    for idx, dyn in enumerate(dynasty_order_sorted):
        cards = groups[dyn][:max_per_dynasty]
        if not cards:
            continue

        section_title = dynasty_names.get(dyn, f"（{dyn}）")
        # 计算章节编号
        section_num = idx + 2  # 从二开始

        lines = [f"### {section_title}", ""]

        # 按书籍分组
        by_book = defaultdict(list)
        for card in cards:
            _, book, author = identify_source(card)
            by_book[(book, author)].append(card)

        for (book, author), book_cards in by_book.items():
            lines.append(f"#### {book} {author}".strip())
            lines.append("")

            for card in book_cards[:5]:  # 每本书最多5条
                summary = clean_summary(card.get("summary", ""), max_len=500)
                lines.append(f"> {summary}")
                lines.append("")

        sections.append("\n".join(lines))

    return "\n\n---\n\n".join(sections)


def generate_index_table(groups: dict[str, list[dict]]) -> str:
    """生成证据索引表"""
    rows = []
    dynasty_order_sorted = sorted(groups.keys(), key=lambda d: DYNASTY_ORDER.get(d, 99))

    for dyn in dynasty_order_sorted:
        for card in groups[dyn]:
            _, book, author = identify_source(card)
            card_id = card.get("card_id", "")
            rows.append(f"| {dyn} | {book} | {author} | {card_id} |")

    return "\n".join(rows) if rows else "| | | | |"


# ── 完整报告生成 ──

def generate_full_report(keyword: str, matches: list[dict]) -> str:
    """生成完整的 Markdown 报告"""
    template = load_template()
    if not template:
        print("错误: 找不到报告模板文件", file=sys.stderr)
        return ""

    # 排序
    matches.sort(key=sort_key)

    # 分组
    groups = group_by_dynasty(matches)

    # 替换占位符
    report = template
    report = report.replace("{formula_name}", keyword)
    report = report.replace("{card_count}", str(len(matches)))
    report = report.replace("{time_span}", get_time_span(matches))
    report = report.replace("{dynasty_sections}", generate_dynasty_sections(groups))
    report = report.replace("{dynasty_index}", generate_index_table(groups))
    report = report.replace("{query_date}", date.today().isoformat())

    return report


# ── 主流程 ──

def main() -> None:
    parser = argparse.ArgumentParser(
        description="中医方剂/条文标准化查询 — 按朝代排序输出医家论述",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/formula_query.py 桂枝人参汤
  python scripts/formula_query.py 小柴胡汤
  python scripts/formula_query.py 甘草泻心汤 --full-report
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
    parser.add_argument(
        "--full-report",
        action="store_true",
        help="生成完整结构化 Markdown 报告（保存到当前目录）",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="完整报告输出路径（默认: {方剂名}历代注解.md）",
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

    # 完整报告模式
    if args.full_report:
        report = generate_full_report(args.keyword, matches)
        if not report:
            return

        # 确定输出路径
        output_path = args.output
        if not output_path:
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', args.keyword)
            output_path = f"{safe_name}历代注解.md"

        Path(output_path).write_text(report, encoding="utf-8")
        print(f"✅ 完整报告已保存至: {output_path}")
        return

    # 默认表格模式
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
