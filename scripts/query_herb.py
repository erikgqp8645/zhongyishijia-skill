#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按中药查方剂 — 查询一味中药的历代本草论述及含此药的所有方剂

用法:
  python scripts/query_herb.py <中药名>
  python scripts/query_herb.py 细辛
  python scripts/query_herb.py 麻黄 --sqlite C:/path/to/20120413mssql.sqlite
  python scripts/query_herb.py 桂枝 --max-formulas 30

输出格式: 双段 Markdown
  第一段：本药历代本草论述（按朝代排序）
  第二段：含此药的方剂列表（按朝代排序）
"""

from __future__ import annotations

import argparse
import io
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

# Windows 终端修复: 确保 stdout 输出 UTF-8
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

from _source_map import DYNASTY_ORDER, identify_source_string


def find_sqlite_path(sqlite_arg: Optional[str] = None) -> Path:
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
        "3. 或放到 <project>/references/raw/20120413mssql.sqlite\n"
        "4. 或使用 --sqlite 参数指定路径"
    )


def parse_sources(source_str: str) -> list[str]:
    """从多出处字符串中解析出独立出处列表"""
    # 去掉前缀标记（"1.出自" "1." 等）
    text = re.sub(r"^\d+[\.、]", "", source_str)
    # 按 "。/" 或独立章节分割
    parts = re.split(r"(?:[②③④⑤⑥⑦⑧⑨⑩]+\s*出自|[②③④⑤⑥⑦⑧⑨⑩]+\s*《)", text)
    sources = []
    for p in parts:
        p = p.strip()
        if p and len(p) > 2:
            sources.append(p)
    # 备用：直接找书名号内容
    if not sources:
        books = re.findall(r"《([^》]+)》", source_str)
        sources = [f"《{b}》" for b in books if b]
    return sources


def query_herb(
    herb: str,
    sqlite_path: Path,
    max_herb_rows: int = 20,
    max_formula_rows: int = 100,
) -> tuple[list[dict], list[dict]]:
    """查询一味中药的本草论述和含此药的方剂"""
    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.cursor()

    herb_rows: list[dict] = []
    formula_rows: list[dict] = []

    # ── 第 1 段：本药历代本草论述（TypeID=40 = 单味药）─────────────
    cur.execute(
        "SELECT MingCheng, ChuChu, LaiYuan, GongNengZZ, XingWei, GuiJing, FuFang "
        "FROM zysjyj WHERE TypeID=40 AND MingCheng=?",
        (herb,),
    )
    for r in cur.fetchall():
        # r: (MingCheng, ChuChu, LaiYuan, GongNengZZ, XingWei, GuiJing, FuFang)
        source_str = r[1] or ""        # ChuChu
        indication = r[3] or ""         # GongNengZZ
        nature = r[4] or ""             # XingWei
        meridian = r[5] or ""           # GuiJing
        classic_formulas = r[6] or ""   # FuFang

        dyn, book, author = identify_source_string(source_str)

        herb_rows.append({
            "herb": herb,
            "dynasty": dyn,
            "book": book,
            "author": author,
            "source_str": source_str[:200],
            "nature": nature,
            "meridian": meridian,
            "indication": indication,
            "classic_formulas": classic_formulas,
        })

    # ── 第 2 段：含此药的所有方剂（TypeID=39 = 中成药/方剂）────────
    cur.execute(
        "SELECT ID, MingCheng, ChuFang, GongNengZZ, ChuChu "
        "FROM zysjyj WHERE TypeID=39 AND ChuFang LIKE ?",
        (f"%{herb}%",),
    )
    for r in cur.fetchall():
        # r: (ID, MingCheng, ChuFang, GongNengZZ, ChuChu)
        formula_name = r[1] or ""
        prescription = r[2] or ""
        indication = r[3] or ""
        source_str = r[4] or ""

        dyn, book, author = identify_source_string(source_str, extra=prescription)

        formula_rows.append({
            "formula": formula_name,
            "dynasty": dyn,
            "book": book,
            "author": author,
            "prescription": prescription,
            "indication": indication,
        })

    conn.close()

    # 按朝代排序
    herb_rows.sort(key=lambda x: (DYNASTY_ORDER.get(x["dynasty"], 99), x["dynasty"], x["book"]))
    formula_rows.sort(key=lambda x: (DYNASTY_ORDER.get(x["dynasty"], 99), x["dynasty"], x["book"], x["formula"]))

    return herb_rows[:max_herb_rows], formula_rows[:max_formula_rows]


def esc(text: str, limit: int = 0) -> str:
    """转义 | 和换行符，并在指定长度截断（转义在截断之前执行）"""
    text = re.sub(r"[|]", "｜", text)
    text = text.replace("\n", " ").replace("\r", " ")  # 换行符转为空格
    if limit > 0 and len(text) > limit:
        text = text[:limit] + "…"
    return text


def render(herb: str, herb_rows: list[dict], formula_rows: list[dict]) -> None:
    """渲染 Markdown 输出"""
    print(f"# 「{herb}」历代本草与方剂论述汇总\n")

    # ── 第 1 段 ──────────────────────────────────────────────
    print(f"## 一、{herb}本药历代本草论述\n")
    if herb_rows:
        print("| 朝代 | 著作 | 作者 | 性味 | 归经 | 功能主治 |")
        print("|:----:|:----:|:----:|:----:|:----:|:--------|")
        for row in herb_rows:
            nature = esc(row["nature"] or "", 40) or "—"
            meridian = esc(row["meridian"] or "", 40) or "—"
            indication = esc(row["indication"] or "", 60) or "—"
            book = esc(row["book"] or "", 30)
            print(f"| {row['dynasty']} | {book} | {row['author']} | {nature} | {meridian} | {indication} |")

        # 经典含方节选
        cf = herb_rows[0].get("classic_formulas", "")
        if cf and len(cf) > 5:
            print(f"\n**经典含方**（节选）：{cf[:200]}\n")
    else:
        print("未找到本草记录。\n")

    # ── 第 2 段 ──────────────────────────────────────────────
    total = len(formula_rows)
    print(f"## 二、含「{herb}」的方剂（共 {total} 条，按朝代排序）\n")
    if formula_rows:
        print("| 朝代 | 著作 | 作者 | 方剂名 | 处方组成（节选） | 主治（节选） |")
        print("|:----:|:----:|:----:|:----:|:--------|:--------|")
        for row in formula_rows:
            prescription = esc(row["prescription"] or "", 50) or "—"
            indication = esc(row["indication"] or "", 50) or "—"
            formula = esc(row["formula"] or "", 20)
            book = esc(row["book"] or "", 25)
            dynasty = row["dynasty"] or "待考"
            author = row["author"] or ""
            print(f"| {dynasty} | {book} | {author} | {formula} | {prescription} | {indication} |")
    else:
        print("未找到含此药的方剂。\n")

    print()
    print("---")
    print(f"*数据来源：中医世家知识库 20120413mssql.sqlite（原始 SQLite）*")
    print(f"*查询药材：{herb}*")
    print(f"*本草论述：{len(herb_rows)} 条 | 含药方剂：{total} 条*")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="按中药查方剂 — 查询一味中药的历代本草论述及含此药的所有方剂",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/query_herb.py 细辛
  python scripts/query_herb.py 麻黄
  python scripts/query_herb.py 桂枝 --max-formulas 30
  python scripts/query_herb.py 人参 --sqlite C:/path/to/20120413mssql.sqlite
        """,
    )
    parser.add_argument("herb", help="要查询的中药材名称（如：细辛、麻黄、桂枝）")
    parser.add_argument(
        "--sqlite",
        help="SQLite 文件路径（默认自动查找）",
    )
    parser.add_argument(
        "--max-formulas",
        type=int,
        default=100,
        help="最多输出多少条方剂（默认 100）",
    )
    parser.add_argument(
        "--max-herb-rows",
        type=int,
        default=20,
        help="最多输出多少条本草论述（默认 20）",
    )
    args = parser.parse_args()

    try:
        sqlite_path = find_sqlite_path(args.sqlite)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"正在查询「{args.herb}」...", file=sys.stderr)
    herb_rows, formula_rows = query_herb(
        args.herb,
        sqlite_path,
        max_herb_rows=args.max_herb_rows,
        max_formula_rows=args.max_formulas,
    )
    print(f"找到 {len(herb_rows)} 条本草记录，{len(formula_rows)} 条方剂记录\n", file=sys.stderr)

    render(args.herb, herb_rows, formula_rows)


if __name__ == "__main__":
    main()
