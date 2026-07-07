#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
症状/病证 → 高频核心药分析

基于"唐宋古方研读方法论"：同一病证的 N 张有效方剂，
汇总药物并做频次统计，筛选出使用频率最高的前 N 味药物，
作为该病证的核心靶向药，再回归本草溯源印证。

用法:
  python scripts/query_disease.py <症状关键词>
  python scripts/query_disease.py 风疹
  python scripts/query_disease.py 皮肤瘙痒
  python scripts/query_disease.py 中风 --top 5

输出:
  1. 含该症状的方剂列表（去重总览）
  2. 药物频次统计（降序排列）
  3. 高频药的本草原始条文（《神农本草经》/《名医别录》/《药性论》等）
"""

from __future__ import annotations

import argparse
import io
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from _sqlite_utils import find_sqlite_path, setup_windows_stdout
from _text_utils import esc, extract_herbs, s

setup_windows_stdout()


def query_disease(
    disease: str,
    sqlite_path: Path,
    top_n: int = 10,
):
    """查询给定症状，返回（方剂列表，药物频次Counter，高频药条文列表）"""
    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.cursor()

    # 查询含该症状的所有方剂（TypeID=39）
    cur.execute(
        "SELECT ID, MingCheng, ChuFang, GongNengZZ, ChuChu "
        "FROM zysjyj WHERE TypeID=39 AND GongNengZZ LIKE ?",
        (f"%{disease}%",),
    )
    formula_rows = []
    all_herbs: list[str] = []

    for r in cur.fetchall():
        formula_id, mingcheng, chufang, gongneng, chuchu = r
        name = s(mingcheng)
        chufang_str = s(chufang)
        gongneng_str = s(gongneng)
        chuchu_str = s(chuchu)

        herbs = extract_herbs(chufang_str)
        all_herbs.extend(herbs)

        formula_rows.append({
            "id": formula_id,
            "name": name,
            "prescription": chufang_str[:100],
            "indication": gongneng_str[:100],
            "source": chuchu_str[:60],
            "herb_count": len(herbs),
            "herbs": herbs,
        })

    conn.close()

    # 药物频次统计
    herb_counter = Counter(all_herbs)
    top_herbs = herb_counter.most_common(top_n)

    # 对高频药查询本草原始条文（TypeID=40）
    herb_bencao: list[tuple[str, str]] = []
    conn2 = sqlite3.connect(str(sqlite_path))
    cur2 = conn2.cursor()

    for herb_name, _ in top_herbs:
        cur2.execute(
            "SELECT MingCheng, XingWei, GuiJing, GongNengZZ, ChuChu, FuFang "
            "FROM zysjyj WHERE TypeID=40 AND MingCheng=?",
            (herb_name,),
        )
        rows = cur2.fetchall()
        if rows:
            mingcheng, xingwei, guijing, gongneng, chuchu, fufang = (s(v) for v in rows[0])
            # 优先取 ChuChu（历代论述），其次 FuFang，最后 GongNengZZ
            bencao_text = chuchu if chuchu else (fufang if fufang else gongneng)
            herb_bencao.append((herb_name, bencao_text[:300]))
        else:
            herb_bencao.append((herb_name, "（本草原始条文未找到）"))

    conn2.close()

    return formula_rows, herb_counter, herb_bencao


def render(
    disease: str,
    formula_rows: list,
    herb_counter: Counter,
    herb_bencao: list,
    top_n: int = 10,
):
    """输出 Markdown 格式结果"""
    total_formulas = len(formula_rows)
    unique_herbs = len(herb_counter)

    print(f"# 「{disease}」高频核心药分析\n")
    print(f"> **症状关键词：** {disease}")
    print(f"> **含该症状的方剂：** {total_formulas} 张（去重）")
    print(f"> **涉及药物：** {unique_herbs} 味（去重）")
    print()

    # ── 第一段：症状总览 ──────────────────────────────
    print("## 一、含该症状的方剂总览\n")
    print("| # | 方剂名 | 药味数 | 功能主治（节选） |")
    print("|:---:|:---|:---:|:---|")
    for i, row in enumerate(formula_rows[:50], 1):
        indication = esc(row["indication"], 60)
        print(f"| {i} | {esc(row['name'], 20)} | {row['herb_count']} | {indication} |")
    if total_formulas > 50:
        print(f"| … | （共 {total_formulas} 张方剂，略） | | |")
    print()

    # ── 第二段：药物频次统计 ─────────────────────────
    print("## 二、药物频次统计（降序）\n")
    print("| # | 药物 | 出现频次 | 占比 |")
    print("|:---:|:---|:---:|:---:|")
    for i, (herb, count) in enumerate(herb_counter.most_common(top_n), 1):
        pct = count / total_formulas * 100 if total_formulas > 0 else 0
        print(f"| {i} | **{herb}** | {count} | {pct:.1f}% |")
    print()

    # ── 第三段：高频药本草溯源 ─────────────────────
    print("## 三、高频药本草原始条文溯源\n")
    print("> 回归《神农本草经》《名医别录》《药性论》探究药物原始功效\n")
    for i, (herb, bencao_text) in enumerate(herb_bencao, 1):
        print(f"### {i}. **{herb}**")
        if bencao_text and "未找到" not in bencao_text:
            # 提取《书名》引用条文片段
            bencao_clean = esc(bencao_text, 0)
            # 找《》引文
            quotes = re.findall(r"《[^》]+》[^。，；\n]{0,80}", bencao_clean)
            if quotes:
                for q in quotes[:4]:
                    print(f"> {q}")
                print()
            else:
                print(f"> {bencao_clean[:200]}")
                print()
        else:
            print("> （本草条文未收录）\n")

    print("---")
    print(f"*数据来源：中医世家知识库 20120413mssql.sqlite*")
    print(f"*症状关键词：{disease} | 方剂 {total_formulas} 张 | 涉及药物 {unique_herbs} 味*")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="症状/病证 → 高频核心药分析（唐宋古方研读方法论）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/query_disease.py 风疹
  python scripts/query_disease.py 皮肤瘙痒
  python scripts/query_disease.py 中风 --top 5
  python scripts/query_disease.py 咳嗽 --sqlite /path/to/20120413mssql.sqlite
        """,
    )
    parser.add_argument("disease", help="症状/病证关键词（如：风疹、皮肤瘙痒、中风）")
    parser.add_argument("--sqlite", help="SQLite 文件路径（默认自动查找）")
    parser.add_argument(
        "--top", type=int, default=10,
        help="输出前 N 味高频药（默认 10）",
    )
    args = parser.parse_args()

    sqlite_path = find_sqlite_path(args.sqlite)

    print(f"正在分析「{args.disease}」...", file=sys.stderr)
    formula_rows, herb_counter, herb_bencao = query_disease(
        args.disease, sqlite_path, top_n=args.top
    )
    print(
        f"找到 {len(formula_rows)} 张方剂，{len(herb_counter)} 味药\n",
        file=sys.stderr
    )

    render(args.disease, formula_rows, herb_counter, herb_bencao, top_n=args.top)


if __name__ == "__main__":
    main()
