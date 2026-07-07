#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重蒸馏 evidence_cards.jsonl — 添加结构化字段

用法:
  python scripts/redistill_cards.py
  python scripts/redistill_cards.py --sqlite /path/to/20120413mssql.sqlite
  python scripts/redistill_cards.py --dry-run

输出: evidence_cards.jsonl（原地覆盖，原文件备份为 .bak）
新增字段: card_kind / dynasty / book / author / prescribed_herbs
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from _sqlite_utils import find_sqlite_path, setup_windows_stdout
from _source_map import DYNASTY_ORDER, identify_source_string
from _text_utils import safe_utf8, extract_herbs as extract_prescribed_herbs

setup_windows_stdout()


def extract_typeid_from_tags(tags) -> int | None:
    """从 tags 列表中提取 TypeID"""
    if not tags:
        return None
    tag_str = str(tags)
    m = re.search(r"TypeID[=: ]*(\d+)", tag_str)
    if m:
        return int(m.group(1))
    return None


def parse_chunk_id(chunk_id: str) -> tuple[str, int] | None:
    """解析 chunk_id → (table_name, record_id)"""
    if not chunk_id:
        return None
    parts = chunk_id.split(":")
    if len(parts) != 2:
        return None
    try:
        return parts[0], int(parts[1])
    except ValueError:
        return None


def build_sqlite_cache(sqlite_path: Path) -> dict[tuple[str, int], dict]:
    """加载 SQLite 数据到内存缓存（仅 zysjyj 表的关键字段）"""
    print(f"加载 SQLite 到缓存: {sqlite_path}", file=sys.stderr)
    conn = sqlite3.connect(str(sqlite_path))
    conn.text_factory = bytes  # SQLite 存储为 UTF-8
    cur = conn.cursor()

    cache: dict[tuple[str, int], dict] = {}

    # zysjyj 表
    print("  缓存 zysjyj...", file=sys.stderr)
    cur.execute(
        "SELECT ID, TypeID, MingCheng, ChuFang, ChuChu, LaiYuan "
        "FROM zysjyj"
    )
    for r in cur.fetchall():
        row_id, typeid, mingcheng, chufang, chuchu, laiyuan = r
        cache[("zysjyj", row_id)] = {
            "typeid": typeid,
            "mingcheng": safe_utf8(mingcheng),
            "chufang": safe_utf8(chufang),
            "chuchu": safe_utf8(chuchu),
            "laiyuan": safe_utf8(laiyuan),
        }

    # zysjllsj 表
    print("  缓存 zysjllsj...", file=sys.stderr)
    cur.execute("SELECT ID, TypeID, BiaoTi, NeiRong FROM zysjllsj")
    for r in cur.fetchall():
        row_id, typeid, biaoti, neirong = r
        cache[("zysjllsj", row_id)] = {
            "typeid": typeid,
            "biaoti": safe_utf8(biaoti),
            "neirong": safe_utf8(neirong),
        }

    # zysjzhsj 表
    print("  缓存 zysjzhsj...", file=sys.stderr)
    cur.execute("SELECT ID, TypeID, BiaoTi, NeiRong FROM zysjzhsj")
    for r in cur.fetchall():
        row_id, typeid, biaoti, neirong = r
        cache[("zysjzhsj", row_id)] = {
            "typeid": typeid,
            "biaoti": safe_utf8(biaoti),
            "neirong": safe_utf8(neirong),
        }

    conn.close()
    print(f"  缓存完成: {len(cache)} 条记录", file=sys.stderr)
    return cache


def enrich_card(card: dict, cache: dict[tuple[str, int], dict]) -> dict:
    """为单张卡片添加结构化字段"""
    chunk_id = card.get("chunk_id", "")
    parsed = parse_chunk_id(chunk_id)
    if not parsed:
        return card

    table, row_id = parsed
    key = (table, row_id)
    if key not in cache:
        return card

    row = cache[key]

    # ── card_kind ──────────────────────────────────────────
    typeid = row.get("typeid")
    if table == "zysjyj":
        if typeid == 40:
            card["card_kind"] = "herb_material"
        elif typeid == 39:
            card["card_kind"] = "formula"
        else:
            card["card_kind"] = "herb_other"
    elif table == "zysjllsj":
        card["card_kind"] = "clinical_theory"
    elif table == "zysjzhsj":
        card["card_kind"] = "synthesis"
    else:
        card["card_kind"] = "unknown"

    # ── dynasty / book / author ─────────────────────────────
    if table == "zysjyj":
        chuchu = row.get("chuchu", "")
        laiyuan = row.get("laiyuan", "")
        chufang = row.get("chufang", "")
        mingcheng = row.get("mingcheng", "")
        # 优先级: LaiYuan > ChuChu > MingCheng，extra 始终用 ChuFang
        primary = laiyuan if laiyuan else (chuchu if chuchu else mingcheng)
        dyn, book, author = identify_source_string(primary, extra=chufang)
        card["dynasty"] = dyn
        card["book"] = book
        card["author"] = author

        # ── prescribed_herbs（仅 formula）────────────────
        if typeid == 39:
            herbs = extract_prescribed_herbs(chufang)
            card["prescribed_herbs"] = herbs
        else:
            card["prescribed_herbs"] = []
    elif table in ("zysjllsj", "zysjzhsj"):
        card["dynasty"] = "待考"
        card["book"] = ""
        card["author"] = ""
        card["prescribed_herbs"] = []
    else:
        card["dynasty"] = "待考"
        card["book"] = ""
        card["author"] = ""
        card["prescribed_herbs"] = []

    return card


def main() -> None:
    parser = argparse.ArgumentParser(
        description="重蒸馏 evidence_cards.jsonl — 添加结构化字段",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/redistill_cards.py
  python scripts/redistill_cards.py --sqlite /path/to/20120413mssql.sqlite
  python scripts/redistill_cards.py --dry-run  # 只看前 100 条
        """,
    )
    parser.add_argument(
        "--sqlite",
        help="SQLite 文件路径（默认自动查找）",
    )
    parser.add_argument(
        "--cards",
        default="../references/text_distillation/evidence_cards.jsonl",
        help="evidence_cards.jsonl 路径（默认 ../references/text_distillation/evidence_cards.jsonl）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只处理前 100 条并输出到 stdout，不写入文件",
    )
    args = parser.parse_args()

    sqlite_path = find_sqlite_path(args.sqlite)
    cards_path = (Path(__file__).resolve().parent / args.cards).resolve()

    if not cards_path.exists():
        print(f"错误: 找不到 {cards_path}", file=sys.stderr)
        sys.exit(1)

    cache = build_sqlite_cache(sqlite_path)

    if args.dry_run:
        print("=== DRY RUN: 前 100 条 ===", file=sys.stderr)
        count = 0
        with open(cards_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if count >= 100:
                    break
                card = json.loads(line)
                card = enrich_card(card, cache)
                print(json.dumps(card, ensure_ascii=False))
                count += 1
        print(f"=== DRY RUN 完成: {count} 条 ===", file=sys.stderr)
        return

    # 备份
    bak_path = cards_path.with_suffix(".jsonl.bak")
    print(f"备份原文件 → {bak_path}", file=sys.stderr)
    import shutil
    shutil.copy2(cards_path, bak_path)

    # 重蒸馏
    print(f"开始重蒸馏: {cards_path}", file=sys.stderr)
    tmp_path = cards_path.with_suffix(".jsonl.tmp")
    total = 0
    with open(cards_path, encoding="utf-8", errors="replace") as fin, \
         open(tmp_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            try:
                card = json.loads(line)
            except json.JSONDecodeError:
                continue
            card = enrich_card(card, cache)
            fout.write(json.dumps(card, ensure_ascii=False) + "\n")
            total += 1
            if total % 50000 == 0:
                print(f"  已处理 {total} 条...", file=sys.stderr)

    # 替换原文件
    tmp_path.replace(cards_path)
    print(f"✓ 重蒸馏完成: {total} 条卡片已更新", file=sys.stderr)


if __name__ == "__main__":
    main()
