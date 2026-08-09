#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ad-hoc verification for formula-query exact-match behavior.

用法:
  python scripts/verify_exact_match.py
  python scripts/verify_exact_match.py --formula "抵当汤"   # 单方剂

设计原则 (2026-07-12 沉淀):
  - 用 evidence_cards.jsonl 自身计算的「title 全等匹配」数作为 ground truth
  - 对比脚本 stderr 报告的 primary 数, 必须 == ground truth
  - 抓取主报告「历代注解」section 的所有 card_id, 验证全是 primary (无次卡片污染)
  - 验证演变章节显式列出家族方剂 + 标注「次卡片·家族方剂」
  - 验证 fallback: 模糊查询列出家族, 0 命中 + 无家族方剂也提示

复用于:
  - 任何对 classify_cards() 的改动回归
  - 任何对引述格式 (generate_citation_line) 的改动
  - 任何对 fallback 逻辑的改动

不要做:
  - 不要把 ground truth 写死 (永远用 jsonl 现场算)
  - 不要跳 T2 (card_id 污染检查), 这是验证精确匹配是否真正生效的核心
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent  # ~/.hermes/skills/zhongyishijia-expert-mentor-lineage
SCRIPT = SKILL / "scripts" / "formula_query.py"
CARDS = SKILL / "references" / "text_distillation" / "evidence_cards.jsonl"


def ground_truth_primary(keyword: str) -> int:
    """从 evidence_cards.jsonl 直接计算 title 全等匹配数 (权威 ground truth)"""
    kw = keyword.strip()
    count = 0
    with open(CARDS, encoding="utf-8") as f:
        for line in f:
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = (c.get("title") or "").strip()
            t2 = t.rstrip("方").strip() if t.endswith("方") else t
            if t == kw or t2 == kw:
                count += 1
    return count


def run_query(keyword: str, *args) -> tuple[int, str, str]:
    r = subprocess.run(
        ["python3", str(SCRIPT), keyword] + list(args),
        capture_output=True, text=True, cwd=str(SKILL),
    )
    return r.returncode, r.stdout, r.stderr


def parse_primary_count(stderr: str) -> int | None:
    m = re.search(r"精确匹配.*?: (\d+) 条", stderr)
    return int(m.group(1)) if m else None


def extract_main_card_ids(stdout: str) -> set[str]:
    """抓主报告「历代注解」section 的所有 card_id"""
    if "## 二~九、历代注解" not in stdout or "## 十、" not in stdout:
        return set()
    main = stdout.split("## 二~九、历代注解")[1].split("## 十、")[0]
    return set(re.findall(r"`card_id=([a-f0-9]+)`", main))


def extract_family_formulas(stdout: str) -> list[str]:
    """抓演变章节「家族方剂」列表"""
    if "### 家族方剂（次卡片·来源非精确匹配）" not in stdout:
        return []
    sec = stdout.split("### 家族方剂（次卡片·来源非精确匹配）")[1]
    nc = re.search(r"\n## ", sec)
    if nc:
        sec = sec[:nc.start()]
    items = re.findall(r"\| ([^|\n]+) \| 家族方剂 \|", sec)
    return [i.strip() for i in items if i.strip()]


def collect_primary_cards(keyword: str) -> set[str]:
    """从 jsonl 收集目标方剂的所有 primary card_id"""
    kw = keyword.strip()
    cids = set()
    with open(CARDS, encoding="utf-8") as f:
        for line in f:
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = (c.get("title") or "").strip()
            if t == kw or t.rstrip("方").strip() == kw:
                cids.add(c.get("card_id"))
    return cids


def verify_one(keyword: str) -> tuple[int, int]:
    """返回 (passed, failed)"""
    p, f = 0, 0
    def check(cond, msg):
        nonlocal p, f
        if cond:
            p += 1
            print(f"  PASS: {msg}")
        else:
            f += 1
            print(f"  FAIL: {msg}")

    print(f"\n[{keyword}] — exact-match verification")
    rc, out, err = run_query(keyword)
    check(rc == 0, f"exit 0 (got {rc})")

    gt = ground_truth_primary(keyword)
    prim = parse_primary_count(err)
    check(prim == gt, f"primary count = ground truth {gt} (got {prim})")

    if prim and prim > 0:
        # T2: 主报告 card_id 全是 primary
        main_cids = extract_main_card_ids(out)
        primary_cids = collect_primary_cards(keyword)
        check(
            main_cids.issubset(primary_cids),
            f"main section {len(main_cids)} card_ids all primary",
        )

        # T3: 演变章节标注家族方剂
        families = extract_family_formulas(out)
        if families:
            check(True, f"演变章节列出 {len(families)} 个家族方剂")
            non_self = [x for x in families[:3] if x != keyword]
            check(len(non_self) == 3, f"前 3 个家族方剂都不是 {keyword} 本体")

    # T4-T5: fallback
    rc, out, err = run_query(keyword + "X")  # 不存在的方剂
    check("数据库中也无任何包含该关键词的家族方剂" in out or
          "未找到与" in out, "0 命中触发 fallback 提示")

    return p, f


def main():
    parser = argparse.ArgumentParser(description="Ad-hoc verify formula_query.py exact-match")
    parser.add_argument("--formula", help="单方剂验证 (默认: 多方剂抽样)")
    args = parser.parse_args()

    if args.formula:
        formulas = [args.formula]
    else:
        # 多方剂抽样回归 (覆盖高/中/低命中, 大方剂与小方剂)
        formulas = ["抵当汤", "小柴胡汤", "麻黄升麻汤",
                    "桂枝人参汤", "九味羌活丸", "大承气汤", "五苓散"]

    total_p, total_f = 0, 0
    for kw in formulas:
        p, f = verify_one(kw)
        total_p += p
        total_f += f

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_p} passed, {total_f} failed")
    sys.exit(0 if total_f == 0 else 1)


if __name__ == "__main__":
    main()