#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桂枝人参汤历代注解查询脚本

用法:
  python scripts/query_guizhi_renshen.py
  python scripts/query_guizhi_renshen.py --herb 麻黄 --max 50
"""

from __future__ import annotations

import argparse
import html
import io
import re
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass


def b(v):
    if v is None:
        return ""
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return str(v)


def esc(t, limit=0):
    t = html.unescape(t or "")
    t = re.sub(r"[|\n\r]", " ", t).strip()
    if limit > 0 and len(t) > limit:
        t = t[:limit] + "…"
    return t


def find_sqlite():
    candidates = [
        Path(__file__).resolve().parent.parent / "references" / "raw" / "20120413mssql.sqlite",
        Path.home() / ".cache" / "zhongyishijia" / "20120413mssql.sqlite",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    raise FileNotFoundError("找不到 SQLite")


# ── 书名 → 朝代（完整映射）────────────────────────────────
# 策略：优先用书名判断朝代，不用正文内容中的引用书名覆盖
BOOK_DYNASTY = {
    # 东汉
    "伤寒论": "东汉", "金匮要略": "东汉", "神农本草经": "东汉", "黄帝内经": "东汉",
    # 魏
    "吴普本草": "魏",
    # 晋
    "肘后备急方": "晋", "脉经": "晋",
    # 梁
    "本草经集注": "梁", "名医别录": "梁",
    # 隋
    "诸病源候论": "隋",
    # 唐
    "备急千金要方": "唐", "千金翼方": "唐", "千金要方": "唐",
    "外台秘要": "唐", "新修本草": "唐",
    # 宋
    "经史证类备急本草": "宋", "本草图经": "宋",
    "太平惠民和剂局方": "宋", "太平圣惠方": "宋",
    "三因极一病证方论": "宋",
    # 金
    "明理论": "金", "脾胃论": "金",
    # 元
    "汤液本草": "元", "本草发挥": "元", "世医得效方": "元",
    "丹溪心法": "元",
    # 明
    "本草纲目": "明", "奇效良方": "明", "普济方": "明",
    "本草经疏": "明", "景岳全书": "明", "医宗必读": "明",
    "伤寒论条辨": "明", "证治准绳": "明", "医学入门": "明",
    "古今医统大全": "明",
    # 清
    "四圣心源": "清", "伤寒悬解": "清", "伤寒来苏集": "清",
    "医宗金鉴": "清", "伤寒论集注": "清", "伤寒论辨证广注": "清",
    "本草备要": "清", "伤寒缵论": "清", "本经逢原": "清",
    "伤寒大白": "清", "伤寒论纲目": "清", "伤寒论本旨": "清",
    "伤寒论类方": "清", "伤寒温疫条辨": "清",
    "伤寒论经解": "清", "伤寒经解": "清",
    "血证论": "清", "温病条辨": "清", "辨证录": "清",
    "伤寒恒论": "清", "伤寒寻源": "清",
    "伤寒附翼": "清", "伤寒原旨": "清",
    "医学金针": "清", "医原": "清",
    "本草思辨录": "清", "时方歌括": "清",
    "类证活人书": "清", "仲景伤寒补亡论": "清",
    "医学实在易": "清", "医学纲目": "清",
    "中医词典": "现代", "高注金匮要略": "清",
    "医门法律": "清", "长沙药解": "清",
    "银海指南": "清", "张氏医通": "清",
    "眉寿堂方案选存": "清", "医述": "清",
    "伤寒百证歌": "清",
    # 民国
    "经方实验录": "民国", "伤寒金匮发微": "民国",
    "医学衷中参西录": "民国",
    # 现代
    "中国药典": "现代", "中华本草": "现代", "中药大辞典": "现代",
    # 日本江户
    "药征": "日本江户", "药征续编": "日本江户",
}


DYNASTY_ORDER = {
    "东汉": 0, "魏": 1, "晋": 2, "梁": 3, "隋": 4,
    "唐": 5, "宋": 6, "金": 7, "元": 8, "日本江户": 9,
    "明": 10, "清": 11, "民国": 12, "现代": 13, "待考": 99,
}


def dynasty_of_book(book_name):
    """从书名推断朝代（优先精确匹配，其次模糊匹配）"""
    if not book_name:
        return "待考"
    # 精确匹配
    if book_name in BOOK_DYNASTY:
        return BOOK_DYNASTY[book_name]
    # 模糊：书名中含某个key
    for key, dyn in BOOK_DYNASTY.items():
        if key in book_name:
            return dyn
    return "待考"


def get_book_by_typeid(conn, typeid):
    """查 zysjcell，找有《》标记的书名"""
    if not typeid:
        return ""
    cur = conn.cursor()
    cur.execute(
        "SELECT Cell_BiaoTi FROM zysjcell WHERE Cell_ID = ? AND Cell_BiaoTi LIKE '《%》%'",
        (typeid,)
    )
    r = cur.fetchone()
    if r and r[0]:
        raw = b(r[0])
        # 去除《》和方剂后缀
        t = raw.replace("《", "").replace("》", "").strip()
        return t
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--herb", default="桂枝人参汤")
    parser.add_argument("--max", type=int, default=20)
    args = parser.parse_args()
    herb = args.herb
    max_per = args.max

    conn = sqlite3.connect(str(find_sqlite()))
    conn.text_factory = bytes
    cur = conn.cursor()
    term = f"%{herb}%"
    results = []

    # 1. zysjyj 方剂本身
    cur.execute("""
        SELECT MingCheng, ChuFang, GongNengZZ, ZhaiLu, LaiYuan, ChuChu
        FROM zysjyj
        WHERE TypeID = 39 AND (MingCheng = ? OR MingCheng LIKE ?)
    """, (herb, term))
    for r in cur.fetchall():
        mc, cf, gn, zl, ly, cc = [b(x) for x in r]
        src = esc(zl) or esc(ly) or esc(cc)
        dyn = dynasty_of_book(src)
        results.append({
            "kind": "方剂",
            "dyn": dyn,
            "title": esc(mc),
            "content": f"处方:{esc(cf, 200)}  主治:{esc(gn, 200)}",
        })

    # 2. zysjllsj 临床理论
    cur.execute("""
        SELECT BiaoTi, NeiRong, TypeID FROM zysjllsj WHERE NeiRong LIKE ?
    """, (term,))
    for r in cur.fetchall():
        bt_raw, nr_raw, tid_raw = r
        bt = b(bt_raw)
        nr = b(nr_raw)
        tid = int(tid_raw) if tid_raw and str(tid_raw).isdigit() else None

        # 优先用 Cell_BiaoTi 书名判断朝代
        book = get_book_by_typeid(conn, tid)
        dyn = dynasty_of_book(book) if book else "待考"

        # 如果书名查不到，用标题推断
        if dyn == "待考" and bt:
            dyn = dynasty_of_book(esc(bt))

        results.append({
            "kind": "理论",
            "dyn": dyn,
            "book": book,
            "title": esc(bt, 60),
            "content": esc(nr, 400),
        })

    conn.close()

    # 按朝代分组
    grouped = {}
    for row in results:
        key = (row["dyn"], DYNASTY_ORDER.get(row["dyn"], 99))
        grouped.setdefault(key, []).append(row)

    # 输出
    print(f"\n{'='*62}")
    print(f"  「{herb}」历代注解（按朝代排序）")
    print(f"{'='*62}")
    print(f"  共 {len(results)} 条")
    print()

    for (dyn, _), rows in sorted(grouped.items(), key=lambda x: x[0][1]):
        print(f"{'─'*62}")
        book0 = rows[0].get("book", "") if rows else ""
        label = f"《{book0}》" if book0 and book0 not in ("待考", "") else ""
        print(f"  【{dyn}】{label}  ({len(rows)} 条)")
        print(f"{'─'*62}")
        for row in rows[:max_per]:
            if row["kind"] == "方剂":
                print(f"  ◆ {row['title']}")
                print(f"    {row['content'][:200]}")
            else:
                t = row["title"].strip()
                c = row["content"].strip()
                if t:
                    print(f"  ▸ {t}")
                if c:
                    idx = c.lower().find(herb.lower())
                    if idx >= 0:
                        s = max(0, idx - 30)
                        e = min(len(c), idx + 100)
                        snippet = ("…" if s > 0 else "") + c[s:e] + ("…" if e < len(c) else "")
                        print(f"    {snippet}")
                    else:
                        print(f"    {c[:120]}{'…' if len(c) > 120 else ''}")
        if len(rows) > max_per:
            print(f"  … 还有 {len(rows) - max_per} 条省略")
        print()

    print(f"{'='*62}")
    print(f"  数据来源：中医世家 SQLite")


if __name__ == "__main__":
    main()
