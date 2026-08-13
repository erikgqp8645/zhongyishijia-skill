#!/usr/bin/env python3
"""Thin wrapper over the packaged zysj SQLite database.

The lineage-skill evidence_cards.jsonl truncates every source chunk to a
~281-character summary. This module exposes the full original text from
zysj.db (a copy of zysj.com.cn's mssqlbak) so callers can fetch the
unabridged record after a card hit.

Tables and primary text columns:
  - zysjyj    : ChuFang     (herb / formula)
  - zysjllsj  : NeiRong     (clinical theory)
  - zysjzhsj  : NeiRong     (synthesis / 医话)
  - zysjcell  : Cell_NeiRong (cell entries)

Records are keyed by (TypeID, ID). The lineage chunk_id encodes these as
"zysjllsj:195484" — split on the colon to recover (table, id).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import local
from typing import Optional

_DB_PATH = Path(__file__).resolve().parent / "zysj.db"

_TABLE_TEXT_FIELD = {
    "zysjyj":   "ChuFang",
    "zysjllsj": "NeiRong",
    "zysjzhsj": "NeiRong",
    "zysjcell": "Cell_NeiRong",
}

_TABLE_TITLE_FIELD = {
    "zysjyj":   "MingCheng",
    "zysjllsj": "BiaoTi",
    "zysjzhsj": "BiaoTi",
    "zysjcell": "Cell_BiaoTi",
}

# Per-thread connection so concurrent searches don't share cursors.
_tls = local()


def _conn() -> sqlite3.Connection:
    con = getattr(_tls, "con", None)
    if con is None:
        if not _DB_PATH.exists():
            raise FileNotFoundError(f"zysj.db not found at {_DB_PATH}")
        con = sqlite3.connect(_DB_PATH)
        con.row_factory = sqlite3.Row
        _tls.con = con
    return con


def _resolve_chunk(chunk_id: str) -> Optional[tuple[str, int]]:
    """Split a chunk_id like 'zysjllsj:195484' -> ('zysjllsj', 195484)."""
    if not chunk_id or ":" not in chunk_id:
        return None
    table, _, id_part = chunk_id.rpartition(":")
    table = table.strip()
    if table not in _TABLE_TEXT_FIELD:
        return None
    try:
        return table, int(id_part.strip())
    except ValueError:
        return None


def fetch_full(chunk_id: str) -> Optional[str]:
    """Return the unabridged text for a lineage chunk_id, or None if absent."""
    resolved = _resolve_chunk(chunk_id)
    if not resolved:
        return None
    table, id_ = resolved
    tf = _TABLE_TEXT_FIELD[table]
    row = _conn().execute(
        f"SELECT {tf} FROM {table} WHERE ID = ? LIMIT 1", (id_,)
    ).fetchone()
    if not row:
        return None
    return row[tf]


def fetch_record(chunk_id: str) -> Optional[dict]:
    """Return full record dict (text + title + source_ref + chunk_id)."""
    resolved = _resolve_chunk(chunk_id)
    if not resolved:
        return None
    table, id_ = resolved
    tf = _TABLE_TEXT_FIELD[table]
    title_field = _TABLE_TITLE_FIELD[table]
    row = _conn().execute(
        f"SELECT {title_field} AS title, {tf} AS text FROM {table} WHERE ID = ? LIMIT 1",
        (id_,),
    ).fetchone()
    if not row:
        return None
    return {
        "title":     row["title"] or "",
        "text":      row["text"] or "",
        "source_ref": f"{table} TypeID={_lookup_type_id(table, id_) or '?'}",
        "chunk_id":  f"{table}:{id_}",
    }


def _lookup_type_id(table: str, id_: int) -> Optional[int]:
    row = _conn().execute(f"SELECT TypeID FROM {table} WHERE ID = ? LIMIT 1", (id_,)).fetchone()
    return row["TypeID"] if row else None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: zysj_index.py <chunk_id>")
        sys.exit(1)
    print(fetch_full(sys.argv[1]) or "")