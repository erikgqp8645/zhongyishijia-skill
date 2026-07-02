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

# ── 来源→(朝代, 著作, 作者) 映射表 ──────────────────────────
# key 匹配规则: 可以是 source_ref 精确值, 也可以是 summary 关键词
SOURCE_MAP: dict[str, tuple[str, str, str]] = {
    # ── 东汉 ──
    "伤寒论": ("东汉", "《伤寒论》", "张仲景"),
    "金匮要略": ("东汉", "《金匮要略》", "张仲景"),

    # ── 金 ──
    "明理论": ("金", "《明理论》", "成无己"),
    "成无己": ("金", "《明理论》", "成无己"),

    # ── 日本江户 ──
    "药征": ("日本江户", "《药征》", "吉益东洞"),
    "吉益东洞": ("日本江户", "《药征》", "吉益东洞"),

    # ── 明 ──
    "景岳全书": ("明", "《景岳全书》", "张介宾"),
    "伤寒论条辨": ("明", "《伤寒论条辨》", "方有执"),
    "证治准绳": ("明", "《证治准绳》", "王肯堂"),
    "医学入门": ("明", "《医学入门》", "李梴"),

    # ── 清 ──
    "四圣心源": ("清", "《四圣心源》", "黄元御"),
    "伤寒悬解": ("清", "《伤寒悬解》", "黄元御"),
    "医学金针": ("清", "《医学金针》", "黄元御"),
    "伤寒来苏集": ("清", "《伤寒来苏集》", "柯琴"),
    "医宗金鉴": ("清", "《医宗金鉴》", "吴谦"),
    "伤寒论集注": ("清", "《伤寒论集注》", "张隐庵"),
    "伤寒论辨证广注": ("清", "《伤寒论辨证广注》", "汪昂"),
    "本草备要": ("清", "《本草备要》", "汪昂"),
    "伤寒缵论": ("清", "《伤寒缵论》", "张璐"),
    "本经逢原": ("清", "《本经逢原》", "张璐"),
    "伤寒大白": ("清", "《伤寒大白》", "秦之桢"),
    "证治汇补": ("清", "《证治汇补》", "李用粹"),
    "伤寒论纲目": ("清", "《伤寒论纲目》", "沈金鳌"),
    "伤寒论本旨": ("清", "《伤寒论本旨》", "章楠"),
    "伤寒论类方": ("清", "《伤寒论类方》", "徐灵胎"),
    "辨证录": ("清", "《辨证录》", "陈士铎"),
    "医学真传": ("清", "《医学真传》", "高士宗"),
    "药证续编": ("清", "《药证续编》", "村井杶"),
    "伤寒温疫条辨": ("清", "《伤寒温疫条辨》", "杨栗山"),
    "伤寒论经解": ("清", "《伤寒经解》", ""),
    "伤寒论集成": ("清", "《伤寒论集成》", ""),

    # ── 民国 ──
    "曹颖甫": ("民国", "《伤寒金匮发微》", "曹颖甫"),
    "经方实验录": ("民国", "《经方实验录》", "曹颖甫"),

    # ── 现代 ──
    "中国中医药报": ("现代", "《中国中医药报》", ""),
    "方剂学": ("现代", "《方剂学》", ""),
    "方剂歌诀": ("现代", "《方剂歌诀》", ""),
    "中医名词": ("现代", "《中医名词术语》", ""),
    "中医症状": ("现代", "《中医症状鉴别》", ""),
    "中医大辞典": ("现代", "《中医大辞典》", ""),
}

# TypeID → (朝代, 著作, 作者) — 针对 zysjllsj 数据库条目
TYPEID_MAP: dict[str, tuple[str, str, str]] = {
    "58": ("东汉", "《伤寒论》", "张仲景"),
    "98": ("东汉", "《伤寒论》", "张仲景"),
    "103": ("东汉", "《伤寒论》", "张仲景"),
    "124": ("明", "《景岳全书》", "张介宾"),
    "166": ("现代", "《中医大辞典》", ""),
    "195": ("现代", "《中医名词术语》", ""),
    "254": ("清", "《本草备要》", "汪昂"),
    "280": ("清", "《伤寒经解》", ""),
    "337": ("清", "《医宗金鉴》", "吴谦"),
    "472": ("明", "《景岳全书》", "张介宾"),
    "495": ("清", "《本经逢原》", "张璐"),
    "517": ("民国", "《经方实验录》", "曹颖甫"),
    "648": ("清", "《伤寒论集注》", "张隐庵"),
    "691": ("清", "《药证续编》", "村井杶"),
    "700": ("清", "《证治汇补》", "李用粹"),
    "708": ("清", "《伤寒论本旨》", "章楠"),
    "725": ("清", "《伤寒论集注》", "张隐庵"),
    "760": ("清", "《伤寒温疫条辨》", "杨栗山"),
    "769": ("清", "《伤寒来苏集》", "柯琴"),
    "895": ("日本江户", "《药征》", "吉益东洞"),
    "944": ("清", "《伤寒论辨证广注》", "汪昂"),
    "1032": ("民国", "《伤寒金匮发微》", "曹颖甫"),
    "1034": ("清", "《医宗金鉴》", "吴谦"),
    "1101": ("清", "《伤寒论经解》", ""),
    "1293": ("清", "《伤寒悬解》", "黄元御"),
    "1295": ("清", "《四圣心源》", "黄元御"),
}

# 朝代排序权重
DYNASTY_ORDER = {
    "东汉": 0,
    "晋": 1,
    "唐": 2,
    "宋": 3,
    "金": 4,
    "元": 5,
    "日本江户": 6,
    "明": 7,
    "清": 8,
    "民国": 9,
    "现代": 10,
}

# ── 辅助函数 ──

def identify_source(card: dict) -> tuple[str, str, str]:
    """识别卡片对应的朝代、著作、作者"""
    source_ref = card.get("source_ref", "") or ""
    title = card.get("title", "") or ""
    summary = card.get("summary", "") or ""

    # 1. 先检查 source_ref 是否能直接匹配
    for key, info in SOURCE_MAP.items():
        if key in source_ref:
            return info

    # 2. 检查 title 中的关键词
    for key, info in SOURCE_MAP.items():
        if key in title:
            return info

    # 3. 检查 summary 中的关键词
    for key, info in SOURCE_MAP.items():
        if key in summary:
            return info

    # 4. 对于 zysjllsj/TypeID 格式, 从 TypeID 反查
    m = re.search(r"TypeID=(\d+)", source_ref)
    if m:
        tid = m.group(1)
        if tid in TYPEID_MAP:
            return TYPEID_MAP[tid]

    return ("待考", source_ref, "")


def sort_key(card: dict) -> tuple:
    """排序 key: 朝代顺序 → 著作 → 作者"""
    dyn, book, author = identify_source(card)
    return (DYNASTY_ORDER.get(dyn, 99), dyn, book, author)


def clean_summary(text: str, max_len: int = 300) -> str:
    """清理摘要: 去 HTML 标签, 截取合理长度"""
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
