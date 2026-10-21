#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""external_formula_query.py — 方剂表外治法(外敷/外贴/熨/洗/涂)检索

适用提问形态:「有没有针对 X 的外敷方」「X 的外用膏剂有哪些」
「外治法里痰瘀同用的方子」「贴脐/箍围/熨法一类的方子」。

与 composite_query.py 的分工(粒度不同,不要混用):
  composite_query.py  → zysjllsj 临床理论层(病机×部位 论述)→ 一行 = 一整章 → 需邻近窗口复核
  本脚本              → zysjyj 方剂层(外治法 配方)→ 一行 = 一张方 = 完整语义单元 → 行级 AND 即可

关键规则(每条都对应一个真实踩坑):
  1) 方剂表行级 AND 合法,不需要邻近窗口 —— 一张方剂的组成+主治+按语
     本就描述同一个处方单元;窗口规则是 zysjllsj 专有的。
  2) 病机关键词(痰/瘀)对外用方几乎不出现在 GongNengZZ(主治)——
     外用方的病机信号在 ChuFang(组成)/ZhiFa(制法)/HuaXueCF(用法)/ZhuYi(按)。
     只扫主治列会漏掉整类外用方(如化痞/消痞/消核一族)。
  3) 筛选用「两组列各自 OR,两组之间 AND」:病机词在病机列任一命中即算,
     部位词在主治列任一命中即算,两组条件同时满足才保留。
  4) 同名方在同表可能有多版本(加减紫金丹 ID=32650 / 14781)→ 按方名分组并陈版本,
     不要静默只取一条。
  5) 方名在方剂表查不到 ≠ 库里没有 —— 古方名可能只存在于 zysjllsj 原文
     (如「新加栝蒌薤白汤」只在俞根《通俗伤寒论》正文里)。

用法:
    python3 scripts/external_formula_query.py --pathology 痰 瘀
    python3 scripts/external_formula_query.py --pathology 痰 瘀 --indication 痞 积聚
    python3 scripts/external_formula_query.py --pathology 痰 瘀 --route 熨
    python3 scripts/external_formula_query.py --pathology 白芥子 --route 贴敷 --top 5
    python3 scripts/external_formula_query.py --pathology 痰 瘀 --json
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

# ── 字段分组 ──────────────────────────────────────────────────────
# 病机信号列:外用方的「痰」「瘀」主要在这里,不在主治列
PATHOLOGY_COLS = ["ChuFang", "ZhiFa", "HuaXueCF", "YongFaYL", "ZhuYi",
                  "LinChuangYY", "BeiZhu"]
# 部位/病名列:痞块/积聚/症瘕/痰核/瘰疬 在这里
INDICATION_COLS = ["GongNengZZ", "XingZhuang", "ChuFang"]
# 用法列:外治给药途径的第一证据位(不含出处列)
USAGE_COLS = ["HuaXueCF", "YongFaYL", "GuiGe"]
# 制法/按语列:给药途径的第二证据位
SECONDARY_ROUTE_COLS = ["ZhiFa", "XingZhuang", "ZhuYi", "FuFang"]

# ── 外治给药途径词表 ──────────────────────────────────────────────
ROUTE_VERBS: dict[str, list[str]] = {
    "贴敷": ["敷贴", "外敷", "外贴", "贴敷", "箍围", "摊贴", "贴于", "贴患处",
             "贴脐", "敷脐", "贴之", "掺", "摊"],
    "熨法": ["熨", "揉熨", "热手摩", "摩之", "摩擦", "磨擦"],
    "洗浴": ["淋洗", "外洗", "浸洗", "洗之", "熏洗", "熏"],
    "涂布": ["外涂", "涂敷", "外搽", "搽之", "涂之", "涂患处"],
    "填塞坐药": ["填塞", "坐药", "纳之"],
}

# 病机词的库内写法变体(字形/异体)
PATHOLOGY_VARIANTS: dict[str, list[str]] = {
    "痰瘀": ["瘀痰", "痰血瘀", "痰瘀相结", "痰瘀互结"],
    "痰": ["水饮", "痰涎"],
    "瘀": ["蓄血", "血瘀", "恶血"],
    "痞": ["痞块", "癥瘕", "症瘕", "积聚", "结块"],
    "痰核": ["痰结", "核块", "瘰疬"],
}


def dec(val) -> str:
    """按值手解码:默认 sqlite3 已给 str;bytes 时依次试 utf-8 → gbk。

    不要设 conn.text_factory = gbk —— 会把 zysjllsj(UTF-8)整表读成乱码,
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


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.text_factory = None
    return conn


def expand(kws: list[str]) -> list[str]:
    """把关键词扩成 词 + 库内变体,去重保序。"""
    out: list[str] = []
    for k in kws:
        for cand in [k] + PATHOLOGY_VARIANTS.get(k, []):
            if cand and cand not in out:
                out.append(cand)
    return out


def first_hit(fields: dict[str, str], cols: list[str],
              variants: list[str]) -> tuple[str, str] | None:
    """在给定列集合里找任一变体命中,返回 (列名, 命中词)。"""
    for col in cols:
        text = fields.get(col, "")
        if not text:
            continue
        for v in variants:
            if v in text:
                return col, v
    return None


def detect_route(fields: dict[str, str]) -> tuple[str | None, str | None]:
    """返回 (途径名, 证据所在字段)。先用用法列,无则退到制法/主治/按语列。"""
    for scope in (USAGE_COLS, SECONDARY_ROUTE_COLS):
        for col in scope:
            text = fields.get(col, "")
            if not text:
                continue
            for route, verbs in ROUTE_VERBS.items():
                if any(v in text for v in verbs):
                    return route, col
    return None, None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="方剂表外治法检索(外敷/外贴/熨/洗/涂)")
    ap.add_argument("--pathology", nargs="+", metavar="KW",
                    help="病机关键词(扫组成/制法/用法/按语列)")
    ap.add_argument("--indication", nargs="+", metavar="KW",
                    help="部位/病名关键词(扫主治/组成列)")
    ap.add_argument("--route", metavar="R",
                    help=f"限定给药途径,取值: {'/'.join(ROUTE_VERBS)}")
    ap.add_argument("--top", type=int, default=40, help="最多输出方名组数")
    ap.add_argument("--sqlite", help="显式指定 zysj.db 路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv[1:])

    if not (args.pathology or args.indication):
        ap.print_help()
        return 1

    try:
        db_path = find_sqlite_path(args.sqlite)
    except FileNotFoundError as exc:
        print(f"FAIL: 找不到 SQLite。{exc}")
        return 1

    conn = connect(db_path)
    scan_cols = list(dict.fromkeys(
        ["ID", "MingCheng", "ZhaiLu", "LaiYuan"]
        + PATHOLOGY_COLS + INDICATION_COLS + USAGE_COLS + SECONDARY_ROUTE_COLS))

    sql = f"SELECT {', '.join(scan_cols)} FROM zysjyj WHERE TypeID=39"
    rows = conn.execute(sql).fetchall()

    path_variants = expand(args.pathology) if args.pathology else []
    ind_variants = expand(args.indication) if args.indication else []

    groups: dict[str, list[dict]] = {}
    scanned = 0
    for raw in rows:
        fields = {c: dec(v) for c, v in zip(scan_cols, raw)}
        scanned += 1

        # 病机列筛:组内 OR(任一变体命中任一病机列即算命中)
        path_hit = None
        if path_variants:
            path_hit = first_hit(fields, PATHOLOGY_COLS, path_variants)
            if not path_hit:
                continue

        # 主治列筛:组内 OR;与病机组之间是 AND(两组条件都要满足)
        ind_hit = None
        if ind_variants:
            ind_hit = first_hit(fields, INDICATION_COLS, ind_variants)
            if not ind_hit:
                continue

        route, route_col = detect_route(fields)
        if route is None:
            continue
        if args.route and route != args.route:
            continue

        name = fields.get("MingCheng", "").strip()
        if not name:
            continue
        groups.setdefault(name, []).append({
            "ID": fields.get("ID"),
            "source": fields.get("ZhaiLu") or fields.get("LaiYuan") or "",
            "indication": fields.get("GongNengZZ") or fields.get("XingZhuang") or "",
            "composition": fields.get("ChuFang", ""),
            "preparation": fields.get("ZhiFa", ""),
            "usage": fields.get("HuaXueCF") or fields.get("YongFaYL") or "",
            "route": route,
            "route_evidence": route_col,
            "pathology_evidence": f"{path_hit[0]}:{path_hit[1]}" if path_hit else "",
            "indication_evidence": f"{ind_hit[0]}:{ind_hit[1]}" if ind_hit else "",
        })

    # 同名多版本:按 ID 升序,版本数一并给出
    out_groups = []
    for name, versions in groups.items():
        versions.sort(key=lambda v: str(v["ID"]))
        out_groups.append({"name": name, "version_count": len(versions),
                           "versions": versions})
    out_groups.sort(key=lambda g: (-g["version_count"], g["name"]))
    out_groups = out_groups[: args.top]

    payload = {
        "db": str(db_path),
        "scanned_formulas": scanned,
        "matched_groups": len(groups),
        "pathology_variants": path_variants,
        "indication_variants": ind_variants,
        "groups": out_groups,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        conn.close()
        return 0

    print(f"扫描方剂表(TypeID=39) {scanned} 首")
    print(f"病机词: {' / '.join(path_variants) or '(无)'}")
    print(f"部位词: {' / '.join(ind_variants) or '(无)'}")
    print(f"命中方名组: {len(groups)}  (已截断至 top {len(out_groups)})")
    print()
    for g in out_groups:
        v0 = g["versions"][0]
        tag = f"  [{g['version_count']} 个版本]" if g["version_count"] > 1 else ""
        print(f"— {g['name']}{tag}   途径:{v0['route']}   {v0['source']}")
        for v in g["versions"]:
            print(f"   · ID={v['ID']}  主治: {v['indication'][:150]}")
            if len(g["versions"]) > 1:
                print(f"     组成: {v['composition'][:160]}")
                print(f"     出处: {v['source']}")
        print()

    conn.close()
    return 0


if __name__ == "__main__":
    # 传完整 argv(不切片):argparse 会把 argv[0] 当程序名,切片会把
    # 第一个选项名吃掉当成 prog,导致 "unrecognized arguments"。与 composite_query.py 同约定。
    sys.exit(main(sys.argv))
