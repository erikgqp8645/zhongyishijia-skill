#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""composite_query.py — 病机 × 部位 × 症状 复合主题检索

适用提问形态:「X 病机在 Y 部位有没有相关论述」「库里有没有同时讲 A 和 B 的段落」
「中焦痰瘀互结的阻滞 有没有类似论述」。

三段式:
  1) SQL 预筛   —— 每个关键词一个 LIKE,AND 起来 → 粗命中集
  2) 邻近复核   —— 要求所有关键词落在同一字符窗口内(默认 300 字)才算"共现"
  3) 分组输出   —— 按 TypeID 聚合,给出章节/书名/ID + 原文摘录

为什么必须有第 2 步: zysjllsj 的一行 = 一篇长文(常是整章病机论述)。
「痰」「瘀」「中焦」常出现在互不相干的段落,AND 计数会把"同行不同段"也算进去,
直接报 AND 数字会严重高估主题密度。

用法:
    python3 scripts/composite_query.py --llsj 痰瘀 中焦
    python3 scripts/composite_query.py --llsj 痰瘀 中焦 --window 500 --top 10
    python3 scripts/composite_query.py --yj 痰瘀
    python3 scripts/composite_query.py --variants 窸囊
    python3 scripts/composite_query.py --llsj 痰瘀 中焦 --json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sqlite_utils import find_sqlite_path  # noqa: E402

BOOKS_JSON = SKILL_ROOT / "references" / "books_json"

# 库内实作写法 ≠ 通行写法的对照(实测:库内「窠囊」128 条,「窸囊」0 条)
VARIANTS: dict[str, list[str]] = {
    "窠囊": ["窸囊"],
    "痰瘀": ["瘀痰", "痰血瘀"],
    "痰饮": ["痰涎", "淡饮", "留饮"],
    "中焦": ["中州", "中宫", "中脘"],
    "胃脘痛": ["胃痛", "心下痛", "脘痛"],
    "鼓胀": ["臌胀"],
    "痰核": ["痰结", "痰瘤"],
}

LLSJ_TITLE_FIELD = "BiaoTi"
LLSJ_TEXT_FIELD = "NeiRong"


# ── 解码 ──────────────────────────────────────────────────────────
def dec(val) -> str:
    """按表逐值解码。默认 sqlite3 已给 str;bytes 时依次试 utf-8 → gbk。

    不要设 conn.text_factory = gbk —— 那会把 zysjllsj(UTF-8)整表读成乱码,
    详见 references/sqlite_deployment_recipe.md 陷阱 #6。
    """
    if val is None:
        return ""
    if isinstance(val, bytes):
        for enc in ("utf-8", "gbk", "gb18030"):
            try:
                return val.decode(enc)
            except UnicodeDecodeError:
                continue
        return val.decode("utf-8", errors="replace")
    return str(val)


# ── 连接 ──────────────────────────────────────────────────────────
def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.text_factory = None  # 显式:按值手解码,不设全局 factory
    return conn


# ── TypeID → 书名 ────────────────────────────────────────────────
def load_book_map() -> dict[int, str]:
    """books_json/*.json 的 cell_id → title(cell_id 即 zysjllsj 的 TypeID)。

    books_json 只是全库的子集(689 本 / 1105 个 TypeID),不在子集里的 TypeID
    查不到书名 —— 这是覆盖边界,不是数据缺失。
    """
    out: dict[int, str] = {}
    if not BOOKS_JSON.is_dir():
        return out
    for f in sorted(BOOKS_JSON.glob("*.json")):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cid, title = j.get("cell_id"), j.get("title")
        if cid is not None and title:
            out[int(cid)] = str(title)
    return out


def sample_chapters(conn: sqlite3.Connection, typeid: int, limit: int = 4) -> list[str]:
    rows = conn.execute(
        f"SELECT DISTINCT {LLSJ_TITLE_FIELD} FROM zysjllsj WHERE TypeID=? LIMIT 200",
        (typeid,),
    ).fetchall()
    seen, out = set(), []
    for (b,) in rows:
        t = dec(b).strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= limit:
            break
    return out


def looks_like_book_title(title: str) -> bool:
    """粗筛:像书名而不是章节名(章节名多为 '第一节·xxx' / '第三章 xxx')。"""
    if not title or len(title) < 4:
        return False
    if "·" in title or "第" in title[:3]:
        return False
    if title.endswith("序"):
        return False
    return True


def resolve_book(conn: sqlite3.Connection, typeid: int,
                 book_map: dict[int, str]) -> tuple[str | None, str]:
    """返回 (书名, 来源标记)。来源标记:books_json / candidate / unresolved。"""
    if typeid in book_map:
        return book_map[typeid], "books_json"
    for cand in sample_chapters(conn, typeid, limit=20):
        if looks_like_book_title(cand):
            return cand, "candidate"
    return None, "unresolved"


# ── 邻近窗口 ──────────────────────────────────────────────────────
def positions(text: str, kw: str) -> list[int]:
    out, i = [], text.find(kw)
    while i != -1:
        out.append(i)
        i = text.find(kw, i + 1)
    return out


def proximity_ok(text: str, kws: list[str], window: int) -> bool:
    """所有关键词是否都出现在彼此 ±window 字符范围内(星形邻接)。"""
    pos = {k: positions(text, k) for k in kws}
    if any(not v for v in pos.values()):
        return False
    anchor = kws[0]
    for p in pos[anchor]:
        if all(any(abs(q - p) <= window for q in pos[k]) for k in kws[1:]):
            return True
    return False


def best_anchor(text: str, kws: list[str], window: int) -> int:
    """选邻近关键词最密集的位置,用于切摘录。"""
    pos = {k: positions(text, k) for k in kws}
    anchor = kws[0]
    best, best_score = (pos[anchor][0] if pos[anchor] else 0), -1
    for p in pos[anchor]:
        score = sum(1 for k in kws for q in pos[k] if abs(q - p) <= window)
        if score > best_score:
            best, best_score = p, score
    return best


# ── llsj 检索 ─────────────────────────────────────────────────────
def query_llsj(conn: sqlite3.Connection, kws: list[str], window: int,
               top: int) -> dict:
    where = " AND ".join(
        f"{LLSJ_TEXT_FIELD} LIKE ?" for _ in kws
    )
    params = [f"%{k}%" for k in kws]
    raw = conn.execute(
        f"SELECT TypeID, ID, {LLSJ_TITLE_FIELD}, {LLSJ_TEXT_FIELD} "
        f"FROM zysjllsj WHERE {where}",
        params,
    ).fetchall()

    entries = []
    for typeid, rid, biaoti, content in raw:
        text = dec(content)
        if not proximity_ok(text, kws, window):
            continue
        a = best_anchor(text, kws, window)
        span = max(160, window)
        s = max(0, a - span // 2)
        excerpt = text[s:s + span].replace("\r\n", "\n").replace("\n", " ")
        entries.append({
            "TypeID": typeid,
            "ID": rid,
            "chapter": dec(biaoti),
            "excerpt": excerpt,
        })

    entries.sort(key=lambda e: (-e["ID"], e["TypeID"]))
    return {"raw_hits": len(raw), "proximity_hits": len(entries), "entries": entries}


# ── yj 方剂检索 ───────────────────────────────────────────────────
def query_yj(conn: sqlite3.Connection, kws: list[str], top: int) -> dict:
    cols = ["MingCheng", "ChuChu", "LaiYuan", "GongNengZZ", "ChuFang"]
    where = " AND ".join(
        f"({c} LIKE ? OR {c} LIKE ?)" for c in ["MingCheng", "GongNengZZ"]
    )
    params: list[str] = []
    for _ in ["MingCheng", "GongNengZZ"]:
        params.extend(f"%{k}%" for k in kws)
    rows = conn.execute(
        f"SELECT {', '.join(cols)} FROM zysjyj WHERE {where} LIMIT ?",
        (*params, top * 5),
    ).fetchall()
    out = []
    for name, chuchu, laiyuan, gongneng, chufang in rows:
        out.append({
            "name": dec(name),
            "source": dec(laiyuan),
            "indication": dec(gongneng)[:220],
            "composition": dec(chufang)[:160],
        })
        if len(out) >= top:
            break
    return {"hits": out}


# ── 变体探测 ─────────────────────────────────────────────────────
def probe_variants(conn: sqlite3.Connection, term: str) -> list[dict]:
    cands = [term] + VARIANTS.get(term, [])
    out = []
    for c in cands:
        n_llsj = conn.execute(
            f"SELECT COUNT(*) FROM zysjllsj WHERE {LLSJ_TEXT_FIELD} LIKE ?",
            (f"%{c}%",),
        ).fetchone()[0]
        n_yj = conn.execute(
            "SELECT COUNT(*) FROM zysjyj WHERE MingCheng LIKE ? OR GongNengZZ LIKE ?",
            (f"%{c}%", f"%{c}%"),
        ).fetchone()[0]
        out.append({"term": c, "zysjllsj": n_llsj, "zysjyj": n_yj})
    return out


# ── 输出 ──────────────────────────────────────────────────────────
def print_llsj(result: dict, kws: list[str], window: int,
                book_map: dict[int, str], conn: sqlite3.Connection) -> None:
    print(f"关键词: {' / '.join(kws)}   邻近窗口: ±{window} 字")
    print(f"粗命中(同行全文 AND): {result['raw_hits']}   "
          f"邻近共现(收敛后): {result['proximity_hits']}")
    if not result["entries"]:
        print("→ 邻近窗口内无共现。若认为是"库里有",先跑 --variants 查写法差异。")
        return
    print()
    for e in result["entries"]:
        book, src = resolve_book(conn, e["TypeID"], book_map)
        label = f"《{book}》" if book and src == "books_json" else (
            f"候选:{book}" if book else "书名未映射")
        print(f"— TypeID={e['TypeID']} ID={e['ID']}  {label}  章节:{e['chapter']}")
        print(f"  {e['excerpt']}")
        print()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="病机×部位×症状 复合主题检索")
    ap.add_argument("--llsj", nargs="+", metavar="KW", help="临床理论库关键词(AND 预筛 + 邻近复核)")
    ap.add_argument("--yj", nargs="+", metavar="KW", help="方剂库关键词")
    ap.add_argument("--window", type=int, default=300, help="邻近窗口字符数(默认 300)")
    ap.add_argument("--top", type=int, default=15, help="最多输出条数")
    ap.add_argument("--variants", metavar="TERM", help="探测某词的库内写法变体命中数")
    ap.add_argument("--sqlite", help="显式指定 zysj.db 路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv[1:])

    if not (args.llsj or args.yj or args.variants):
        ap.print_help()
        return 1

    try:
        db_path = find_sqlite_path(args.sqlite)
    except FileNotFoundError as exc:
        print(f"FAIL: 找不到 SQLite。{exc}")
        return 1

    conn = connect(db_path)
    book_map = load_book_map()
    payload: dict = {"db": str(db_path)}

    if args.variants:
        payload["variants"] = probe_variants(conn, args.variants)
        if not args.json:
            print(f"变体探测: {args.variants}")
            for v in payload["variants"]:
                print(f"  {v['term']:<8} zysjllsj={v['zysjllsj']:<7} zysjyj={v['zysjyj']}")

    if args.llsj:
        res = query_llsj(conn, args.llsj, args.window, args.top)
        payload["llsj"] = {"keywords": args.llsj, "window": args.window, **res}
        if not args.json:
            print_llsj(res, args.llsj, args.window, book_map, conn)

    if args.yj:
        res = query_yj(conn, args.yj, args.top)
        payload["yj"] = res
        if not args.json:
            print(f"\n方剂库命中: {len(res['hits'])}")
            for h in res["hits"]:
                print(f"— {h['name']}  {h['source']}")
                print(f"  主治: {h['indication']}")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
