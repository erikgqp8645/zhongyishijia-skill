#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建中药→方剂反向索引 herb_index.jsonl

用法:
  python scripts/build_herb_index.py
  python scripts/build_herb_index.py --sqlite /path/to/20120413mssql.sqlite
  python scripts/build_herb_index.py --output references/text_distillation/herb_index.jsonl

输出格式（JSONL，每行一个中药条目）:
  {"herb": "细辛", "sqlite_id": 1234, "formula_ids": [5678, 9012, ...]}
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

# Windows 终端修复
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass


def find_sqlite_path(sqlite_arg: str | None) -> Path:
    """按优先级查找 SQLite 文件位置"""
    candidates = []
    if sqlite_arg:
        candidates.append(Path(sqlite_arg))
    candidates.extend([
        Path.home() / ".cache" / "zhongyishijia" / "20120413mssql.sqlite",
        Path.home() / ".local" / "share" / "zhongyishijia" / "20120413mssql.sqlite",
        Path(__file__).resolve().parent.parent / "references" / "raw" / "20120413mssql.sqlite",
    ])
    for c in candidates:
        if c and c.exists() and c.is_file():
            return c
    raise FileNotFoundError(
        "找不到 20120413mssql.sqlite。请：\n"
        "1. 设置环境变量：export ZHONGYISHIJIA_SQLITE=/path/to/20120413mssql.sqlite\n"
        "2. 或放到 ~/.cache/zhongyishijia/20120413mssql.sqlite\n"
        "3. 或使用 --sqlite 参数指定路径"
    )


def extract_herbs_from_chufang(chufang: str) -> list[str]:
    """从处方字段提取中药名称列表"""
    if not chufang:
        return []
    herbs: list[str] = []
    # 按逗号/句号分割
    parts = re.split(r"[,，。.]+", chufang)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # 匹配中药名：开头连续中文字符（排除剂量词）
        m = re.match(r"^([一-龥]{2,10})", part)
        if m:
            name = m.group(1)
            # 排除明显的非药名
            if name not in NOISE_HERBS:
                herbs.append(name)
    return herbs


# 非药名过滤词
NOISE_HERBS: set[str] = {"一方", "一众人钱", "各等分", "各等份", "等分", "一方各", "兼给", "各半"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="构建中药→方剂反向索引 herb_index.jsonl",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/build_herb_index.py
  python scripts/build_herb_index.py --sqlite C:/path/to/20120413mssql.sqlite
        """,
    )
    parser.add_argument(
        "--sqlite",
        help="SQLite 文件路径（默认自动查找）",
    )
    parser.add_argument(
        "--output",
        default="../references/text_distillation/herb_index.jsonl",
        help="输出 JSONL 路径（默认 ../references/text_distillation/herb_index.jsonl）",
    )
    args = parser.parse_args()

    sqlite_path = find_sqlite_path(args.sqlite)
    output_path = (Path(__file__).resolve().parent / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"读取 SQLite: {sqlite_path}", file=sys.stderr)

    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.cursor()

    # 扫描所有 TypeID=39 的方剂
    print("扫描方剂记录...", file=sys.stderr)
    cur.execute("SELECT ID, MingCheng, ChuFang FROM zysjyj WHERE TypeID=39")
    rows = cur.fetchall()
    print(f"共 {len(rows)} 条方剂记录", file=sys.stderr)

    # 反向索引: herb_name → set of formula_ids
    herb_map: dict[str, set[int]] = defaultdict(set)

    for r in rows:
        formula_id = r[0]
        chufang = r[2] or ""
        herbs = extract_herbs_from_chufang(chufang)
        for herb in herbs:
            herb_map[herb].add(formula_id)

    conn.close()

    print(f"共提取 {len(herb_map)} 味中药", file=sys.stderr)

    # 写入 JSONL
    print(f"写入 {output_path}...", file=sys.stderr)
    with open(output_path, "w", encoding="utf-8") as f:
        for herb, formula_ids in sorted(herb_map.items()):
            record = {
                "herb": herb,
                "sqlite_id": min(formula_ids),  # 主记录 ID（不代表唯一性）
                "in_formula_ids": sorted(formula_ids),
                "count": len(formula_ids),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"✓ 写入完成：{len(herb_map)} 条记录", file=sys.stderr)


if __name__ == "__main__":
    main()
