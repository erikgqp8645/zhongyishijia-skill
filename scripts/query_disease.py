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


# Windows 终端修复
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass


def find_sqlite_path(sqlite_arg: str | None = None) -> Path:
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
        "找不到 20120413mssql.sqlite。请使用 --sqlite 参数指定路径。"
    )


def s(val) -> str:
    """安全转字符串，并去除首尾空白"""
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace").strip()
    return str(val).strip()


def extract_herbs(chufang: str) -> list[str]:
    """从 ChuFang 字段提取药名列表

    策略：先用（）分割去除炮制指令段，再按分隔符提取药名。
    例: "天雄（炮.去皮.脐）麻黄（去节）" → ["天雄", "麻黄"]
    """
    if not chufang:
        return []
    herbs: list[str] = []

    # ── 第 1 步：去除炮制指令段 ─────────────────────────────
    # 匹配全角/半角括号及其内容，如 "（去皮脐)" "(炮.去皮.脐)"
    cleaned = re.sub(r"[（(][^)）]*[)）]", "", chufang)

    # ── 第 2 步：按分隔符分割 ────────────────────────────────
    parts = re.split(r"[,，。、\s]+", cleaned)

    # ── 第 3 步：NOISE 过滤 + 药名提取 ──────────────────────
    NOISE = {
        # 通用非药名
        "一方", "各等分", "各等份", "等分", "一方各", "兼给", "各半",
        "各", "每服", "右为", "右七味", "右六味", "右八味",
        "右九味", "右十味", "一两", "二两", "三两", "二枚", "三枚",
        # 炮制关键词（避免误提取）
        "去皮", "去节", "去核", "去心", "去芦", "去骨",
        "去脐", "去刺", "去翅", "去鳞", "去蒂", "去膂",
        "炙", "炒", "煨", "烘", "酒浸", "醋浸", "水洗",
        "米泔浸", "泔浸", "泔洗",
        "炮", "煅", "煮", "蒸", "焙", "炙甘草",
        # 剂型/服用关键词
        "丸", "汤", "散", "膏", "煎", "渍", "酿", "末",
        "服", "钱匕", "钱", "匕", "盏", "升", "合",
    }
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^([一-龥]{2,10})", part)
        if m:
            name = m.group(1).strip()
            if name not in NOISE:
                herbs.append(name)
    return herbs


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


def esc(text: str, limit: int = 0) -> str:
    """转义 | 和换行符，并在指定长度截断"""
    text = re.sub(r"[|\n\r]", " ", text)
    text = text.strip()
    if limit > 0 and len(text) > limit:
        text = text[:limit] + "…"
    return text


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
