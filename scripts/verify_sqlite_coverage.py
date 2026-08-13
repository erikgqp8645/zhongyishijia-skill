#!/usr/bin/env python3
"""Coverage probe for zhongyishijia-expert-mentor-lineage's SQLite fallback.

The packaged evidence_cards.jsonl truncates every chunk to ~281 chars
(42% of cards hit the 281-char ceiling exactly; longest is 281; total
content ~59M chars vs SQLite's ~180M chars — 3% retention).

`references/external/zysj.db` is a full copy of zysjmssqlbak.sqlite
(zysj.com.cn's mssql backup, 684 MB, 4 tables, ~1.8 亿字符) that
`scripts/query_formula.py` consults via `zysj_index.fetch_full(chunk_id)`
to repair truncated cards. This script verifies that lookup works
end-to-end and probes how much of a given book's content is in the
SQLite that is NOT in the truncated cards — useful for "complete
list" questions like "list every formula in 辅行诀".

Usage:
    python3 scripts/verify_sqlite_coverage.py                     # smoke test
    python3 scripts/verify_sqlite_coverage.py 辅行诀              # chapter-level probe
    python3 scripts/verify_sqlite_coverage.py 1247 zysjllsj       # raw TypeID probe
    python3 scripts/verify_sqlite_coverage.py --json 辅行诀       # machine-readable
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

SKILL_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = SKILL_ROOT / "references" / "external" / "zysj.db"
JSONL_PATH = SKILL_ROOT / "references" / "text_distillation" / "evidence_cards.jsonl"

TABLES = ["zysjyj", "zysjllsj", "zysjzhsj"]
TEXT_FIELD = {"zysjyj": "ChuFang", "zysjllsj": "NeiRong", "zysjzhsj": "NeiRong"}
TITLE_FIELD = {"zysjyj": "MingCheng", "zysjllsj": "BiaoTi", "zysjzhsj": "BiaoTi"}

# Heuristic TypeID mapping for canonical classical texts that users
# ask "give me all formulas of X" about. Extend as coverage gaps surface.
TEXT_TYPEID_HINTS = {
    "伤寒论": ["58", "98", "103", "337"],
    "金匮要略": ["58", "98", "103"],
    "辅行诀": ["1247"],
    "辅行诀脏腑用药法要": ["1247"],
    "神农本草经": [],
    "千金方": ["121", "122", "168"],
}


def db_available() -> bool:
    return DB_PATH.exists() and DB_PATH.stat().st_size > 100_000_000


def sqlite_stats() -> dict:
    """One-shot row and character counts per table."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    out = {}
    for t in TABLES:
        tf = TEXT_FIELD[t]
        cur.execute(f"SELECT COUNT(*), COALESCE(SUM(LENGTH({tf})),0), "
                    f"COALESCE(MAX(LENGTH({tf})),0), COALESCE(AVG(LENGTH({tf})),0) "
                    f"FROM {t}")
        n, total, mx, avg = cur.fetchone()
        out[t] = {"rows": n, "chars": total, "max_chars": int(mx), "avg_chars": float(avg)}
    con.close()
    return out


def jsonl_stats() -> dict:
    """Card count and summary-length distribution from the packaged jsonl."""
    n = 0
    lens = []
    with JSONL_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += 1
            lens.append(len(c.get("summary", "")))
    return {
        "rows": n,
        "avg_chars": sum(lens) / len(lens) if lens else 0,
        "max_chars": max(lens) if lens else 0,
        "exactly_281": sum(1 for x in lens if x == 281),
    }


def fetch_full(chunk_id: str) -> str | None:
    """Resolve a chunk_id like 'zysjllsj:195484' to full SQLite text."""
    if not chunk_id or ":" not in chunk_id:
        return None
    table, _, id_part = chunk_id.rpartition(":")
    if table not in TEXT_FIELD:
        return None
    try:
        id_ = int(id_part)
    except ValueError:
        return None
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        f"SELECT {TEXT_FIELD[table]} FROM {table} WHERE ID = ? LIMIT 1",
        (id_,),
    ).fetchone()
    con.close()
    return row[0] if row else None


def probe_text(keyword: str, *, typeids: Iterable[str] | None = None,
               table: str = "zysjllsj") -> dict:
    """Count records in a table where the text contains keyword.

    If typeids is given, restrict to those TypeIDs; otherwise scan all.
    Returns counts only — does NOT dump content (call fetch_full for that).
    """
    con = sqlite3.connect(DB_PATH)
    tf = TEXT_FIELD[table]
    if typeids:
        placeholders = ",".join("?" * len(list(typeids)))
        cur = con.execute(
            f"SELECT TypeID, COUNT(*), SUM(LENGTH({tf})) "
            f"FROM {table} WHERE TypeID IN ({placeholders}) AND {tf} LIKE ? "
            f"GROUP BY TypeID",
            (*typeids, f"%{keyword}%"),
        )
    else:
        cur = con.execute(
            f"SELECT TypeID, COUNT(*), SUM(LENGTH({tf})) "
            f"FROM {table} WHERE {tf} LIKE ? "
            f"GROUP BY TypeID ORDER BY SUM(LENGTH({tf})) DESC",
            (f"%{keyword}%",),
        )
    rows = cur.fetchall()
    con.close()
    return {
        "keyword": keyword,
        "table": table,
        "hits_by_typeid": [
            {"TypeID": r[0], "rows": r[1], "total_chars": r[2]} for r in rows
        ],
        "total_rows": sum(r[1] for r in rows),
        "total_chars": sum(r[2] for r in rows),
    }


def cmd_smoke() -> int:
    """Quick health check: db reachable, fetch_full works, stats sane."""
    if not db_available():
        print(f"FAIL: zysj.db missing or too small at {DB_PATH}")
        return 1
    db = sqlite_stats()
    jl = jsonl_stats()
    print("=== zysj.db (full source) ===")
    for t, s in db.items():
        print(f"  {t}: {s['rows']:>7,} rows, {s['chars']:>10,} chars, "
              f"max={s['max_chars']:>7,}, avg={s['avg_chars']:>6.0f}")
    print("=== evidence_cards.jsonl (truncated index) ===")
    print(f"  {jl['rows']:>7,} cards, avg={jl['avg_chars']:.0f} chars, "
          f"max={jl['max_chars']}, exactly-281={jl['exactly_281']:,}")
    retention = sum(s["chars"] for s in db.values()) / max(jl["rows"] * jl["avg_chars"], 1)
    print(f"  SQLite/jsonl char ratio: {retention:.1f}x (jsonl keeps ~{100/retention:.2f}%)")

    sample = fetch_full("zysjllsj:195484")
    if not sample or "二旦" not in sample:
        print("FAIL: fetch_full('zysjllsj:195484') did not return expected content")
        return 1
    print(f"  fetch_full smoke test OK ({len(sample)} chars for 辅行诀 ch.8)")
    print("PASS")
    return 0


def cmd_text_probe(keyword: str, *, as_json: bool = False) -> int:
    typeids = TEXT_TYPEID_HINTS.get(keyword)
    if typeids is None and keyword.isdigit():
        typeids = [keyword]
    result = probe_text(keyword, typeids=typeids)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"keyword={result['keyword']!r} table={result['table']}")
        if not result["hits_by_typeid"]:
            print("  no hits")
        for h in result["hits_by_typeid"]:
            print(f"  TypeID={h['TypeID']:>5}  rows={h['rows']:>4}  "
                  f"chars={h['total_chars']:>8,}")
        print(f"  TOTAL: {result['total_rows']} rows, "
              f"{result['total_chars']:,} chars")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args or args[0] in ("--smoke", "-s"):
        return cmd_smoke()
    if args[0] == "--json":
        return cmd_text_probe(args[1], as_json=True) if len(args) > 1 else cmd_smoke()
    return cmd_text_probe(args[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv))