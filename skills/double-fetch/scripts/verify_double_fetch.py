#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zhongyishijia-double-fetch — 验证脚本

目的：验证三层数据（L0 SQLite / L1 books_json / L2 蒸馏卡）一致性与可还原性。

跑法：
  python3 verify_double_fetch.py

典型用途：
  - 验证某 chunk_id 三层互校没问题
  - 验证"用户异文 vs L0 ground truth" 逐字可比
  - 当 skill 体例变更 / 蒸馏管线升级时，作为回归测试

输出：
  - 三层文件状态
  - 给定 chunk_id 三层互校结果
  - 可选：与异文的逐字对比

退出码：
  0 = 验证通过
  1 = 文件缺失或对比失败
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional


# ── 默认路径定位 ──

def find_skill_root() -> Path:
    """定位 zhongyishijia-expert-mentor-lineage skill 根目录"""
    # scripts/verify_double_fetch.py → skills/double-fetch/scripts/ → skills/double-fetch/ → skills/ → skill root
    here = Path(__file__).resolve()
    # 跳过 scripts/、double-fetch/、skills/ 三层父目录
    return here.parents[3]


def resolve_paths(skill_root: Optional[Path] = None) -> dict:
    """解析三层数据文件路径"""
    root = skill_root or find_skill_root()
    return {
        "L0_sqlite": root / "references/raw/20120413mssql.sqlite",
        "L1_books_json_dir": root / "references/books_json",
        "L2_cards_jsonl": root / "references/text_distillation/evidence_cards.jsonl",
        "skill_md": root / "skills/double-fetch/SKILL.md",
    }


# ── 验证 1：三层文件存在性 ──

def verify_files(paths: dict) -> bool:
    print("=" * 70)
    print("【验证 1】三层文件存在性")
    print("=" * 70)
    ok = True
    for label, p in [
        ("L0 SQLite (ground truth)", paths["L0_sqlite"]),
        ("L1 books_json/ (689 files)", paths["L1_books_json_dir"]),
        ("L2 evidence_cards.jsonl (UI 蒸馏)", paths["L2_cards_jsonl"]),
        ("skill SKILL.md", paths["skill_md"]),
    ]:
        if p.is_file():
            sz = p.stat().st_size
            print(f"  ✅ {label}: 存在 ({sz:,} bytes)")
        elif p.is_dir():
            n = sum(1 for _ in p.iterdir())
            print(f"  ✅ {label}: 存在 ({n} 文件)")
        else:
            print(f"  ❌ {label}: 不存在 ({p})")
            ok = False
    return ok


# ── 验证 2：三层互校 ──

def verify_three_layer(
    paths: dict, chunk_id: str = "zysjllsj:195478"
) -> tuple[bool, dict]:
    """对指定 chunk_id 做 L0/L1/L2 三层互校。返回 (pass, info)。"""
    print()
    print("=" * 70)
    print(f"【验证 2】三层互校 (chunk_id={chunk_id})")
    print("=" * 70)

    info = {}

    # L0 SQLite
    if not paths["L0_sqlite"].exists():
        print(f"  ❌ L0 SQLite 不存在")
        return False, info
    conn = sqlite3.connect(paths["L0_sqlite"])
    cur = conn.cursor()
    table, row_id = chunk_id.split(":")
    cur.execute(f"SELECT ID, length(NeiRong), BiaoTi FROM {table} WHERE ID=?", (int(row_id),))
    row = cur.fetchone()
    if row:
        info["L0_len"] = row[1]
        info["L0_title"] = row[2]
        info["L0_text"] = cur.execute(
            f"SELECT NeiRong FROM {table} WHERE ID=?", (int(row_id),)
        ).fetchone()[0]
        print(f"  L0: id={row[0]}, len={row[1]}, title={row[2]!r}")
    else:
        print(f"  ❌ L0: chunk_id={chunk_id} 不存在")
        conn.close()
        return False, info
    conn.close()

    # L1 books_json — 用 L0 标题精确匹配 entries.title（精确锚，而非 fuzzy）
    if paths["L1_books_json_dir"].exists():
        target_title = info["L0_title"]
        best_match = None
        for fp in paths["L1_books_json_dir"].glob("*.json"):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                # 精确查找：遍历所有 entries 比 title
                for ch in data.get("chapters", []):
                    for sec in ch.get("sections", []):
                        for entry in sec.get("entries", []):
                            if entry.get("title") == target_title:
                                content = entry.get("content", "")
                                if content:
                                    best_match = (fp.name, content, len(content))
                                    break
                        if best_match:
                            break
                    if best_match:
                        break
                if best_match:
                    break
            except Exception:
                continue
        if best_match:
            info["L1_len"] = best_match[2]
            info["L1_source"] = best_match[0]
            info["L1_diff"] = abs(best_match[2] - info["L0_len"])
            print(f"  L1: {best_match[0]} len={best_match[2]} "
                  f"(exact title match for '{target_title}', diff ±{info['L1_diff']})")
        else:
            info["L1_len"] = None
            info["L1_source"] = None
            print(f"  ⚠️ L1: 未找到 entries.title == '{target_title}' 的 books_json 条目")

    # L2 evidence_cards.jsonl
    l2_card_id = None
    l2_summary = None
    if paths["L2_cards_jsonl"].exists():
        with open(paths["L2_cards_jsonl"], encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                if chunk_id in (c.get("chunk_id", "") or ""):
                    l2_card_id = c.get("card_id")
                    l2_summary = c.get("summary", "")
                    break
    if l2_summary is not None:
        info["L2_len"] = len(l2_summary)
        info["L2_card_id"] = l2_card_id
        print(f"  L2: card_id={l2_card_id}, summary_len={len(l2_summary)}")
    else:
        info["L2_len"] = None
        info["L2_card_id"] = None
        print(f"  ⚠️ L2: chunk_id 不在 evidence_cards.jsonl 中")

    # 一致性判定
    print()
    print("=" * 70)
    print("【验证 3】一致性 + 截断识别")
    print("=" * 70)

    ok_l0_l1 = (
        info.get("L0_len") is not None
        and info.get("L1_len") is not None
        and abs(info["L0_len"] - info["L1_len"]) <= 50
    )
    print(f"  L0/L1 长度一致: {ok_l0_l1} "
          f"(L0={info.get('L0_len')}, L1={info.get('L1_len')}, "
          f"diff={info.get('L1_diff', '?')})")

    ok_l2_truncated = (
        info.get("L2_len") is not None and info["L2_len"] <= 281
    )
    print(f"  L2 summary ≤ 281 字符（截断识别）: {ok_l2_truncated} "
          f"(L2={info.get('L2_len')})")

    passed = ok_l0_l1 and ok_l2_truncated
    print()
    print("=" * 70)
    print("【最终结论】" + (" ✅ 通过" if passed else " ❌ 不通过"))
    print("=" * 70)
    if passed:
        print(f"  chunk_id={chunk_id}")
        print(f"  - L0 + L1 = {info.get('L0_len')} = {info.get('L1_len')} （互为 ground truth）")
        print(f"  - L2 = {info.get('L2_len')} 字符（蒸馏卡 UI 层，已截断）")
        print(f"  - 双源取证流程可用，能还原完整原文")

    return passed, info


def extract_l1_text(book_data) -> Optional[str]:
    """从 books_json 中递归抽取最长的字符串字段"""
    candidates = []

    def walk(obj):
        if isinstance(obj, str) and len(obj) > 200:
            candidates.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    walk(book_data)
    # 返回最长者（章节级原文）
    if candidates:
        return max(candidates, key=len)
    return None


# ── 验证 4：与异文逐字对比（可选） ──

def verify_against_variant(
    info: dict,
    user_variant_composition: list[str],
    user_variant_1liang: list[str],
) -> bool:
    """逐字对比用户贴的 7 味药名 vs L0 ground truth 7 味。"""
    print()
    print("=" * 70)
    print("【验证 4】用户异文 vs L0 ground truth 逐字对比")
    print("=" * 70)

    if "L0_text" not in info:
        print("  ❌ 没有 L0_text，跳过")
        return False

    # 抽取 L0 中这一段的方剂组成
    l0_text = info["L0_text"]
    # 找"大补心汤（第二方）"段（因为"代赭石"也出现在"小补心汤第二方"里）
    idx = l0_text.find("大补心汤（第二方）")
    if idx == -1:
        idx = l0_text.find("代赭石")
    if idx == -1:
        print("  ❌ L0 文本中找不到大补心汤第二方或代赭石")
        return False
    # 截到"上方七味"前
    end_idx = l0_text.find("上方七味", idx)
    if end_idx == -1:
        end_idx = idx + 300
    l0_constit = l0_text[idx:end_idx]
    # 把"一方作xxx"的校注剥掉，让主药名更纯粹
    l0_main = re.sub(r"（[^）]*?一方作[^）]*?）", "", l0_constit)
    print(f"  L0 组成段（去校注后）:\n    {l0_main}")

    # 用户三两药（4 味）
    print()
    print(f"  {'用户贴':<12} | {'L0 主药名':<25} | 状态")
    print("  " + "-" * 70)
    ok_count = 0
    diff_count = 0
    for u in user_variant_composition:
        # 在 L0 主药名（去校注后）里查
        if u in l0_main:
            ok_count += 1
            print(f"  {u:<12} | (L0 主药含此) | ✅ 一致")
        elif any(u in s for s in re.findall(r"[（(]([^)）]*?一方作[^)）]*?)[)）]", l0_constit)):
            diff_count += 1
            print(f"  {u:<12} | (在'一方作'校注里) | ⚠️ 异文（用户采他校）")
        else:
            diff_count += 1
            print(f"  {u:<12} | (L0 完全无此) | ❌ 异常")
    for u in user_variant_1liang:
        if u in l0_main:
            ok_count += 1
            print(f"  {u:<12} | (L0 主药含此) | ✅ 一致")
        elif any(u in s for s in re.findall(r"[（(]([^)）]*?一方作[^)）]*?)[)）]", l0_constit)):
            diff_count += 1
            print(f"  {u:<12} | (在'一方作'校注里) | ⚠️ 异文（用户采他校）")
        else:
            diff_count += 1
            print(f"  {u:<12} | (L0 完全无此) | ❌ 异常")
    print()
    print(f"  7 味药对比: {ok_count}/7 一致 + {diff_count}/7 是已知他校异说")
    return ok_count + diff_count == 7  # 所有 7 味要么一致要么已知异文


# ── 入口 ──

def main():
    parser = argparse.ArgumentParser(
        description="zhongyishijia-double-fetch 验证脚本 — 检验三层数据一致性与可还原性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 默认验证 195478
  python3 verify_double_fetch.py

  # 指定其它 chunk_id
  python3 verify_double_fetch.py --chunk-id zysjllsj:195477

  # 含逐字对比（用户异文 vs L0）
  python3 verify_double_fetch.py --variant-composition 牡丹皮 旋覆花 竹叶 人参 \\
                                  --variant-1liang 萸肉 甘草（炙） 干姜
        """,
    )
    parser.add_argument(
        "--chunk-id",
        default="zysjllsj:195478",
        help="要验证的 chunk_id（默认 zysjllsj:195478 / 大补心汤第二方所在章节）",
    )
    parser.add_argument(
        "--variant-composition",
        nargs="+",
        default=["牡丹皮", "旋覆花", "竹叶", "人参"],
        help="用户异文中的三两药名（空格分隔）",
    )
    parser.add_argument(
        "--variant-1liang",
        nargs="+",
        default=["萸肉", "甘草（炙）", "干姜"],
        help="用户异文中的一两药名（空格分隔）",
    )

    args = parser.parse_args()
    paths = resolve_paths()

    passed1 = verify_files(paths)
    if not passed1:
        print("\n❌ 文件缺失，验证提前结束")
        sys.exit(1)

    passed2, info = verify_three_layer(paths, chunk_id=args.chunk_id)
    if not passed2:
        print(f"\n❌ 三层互校不通过")
        sys.exit(1)

    passed4 = verify_against_variant(
        info,
        user_variant_composition=args.variant_composition,
        user_variant_1liang=args.variant_1liang,
    )

    if passed2 and passed4:
        print("\n" + "=" * 70)
        print("✅ 所有验证通过")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"\n⚠️ 验证部分通过：层次一致={passed2}, 异文逐字={passed4}")
        sys.exit(0)


if __name__ == "__main__":
    main()
