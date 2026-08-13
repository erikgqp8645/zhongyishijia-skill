"""
祖方演化分析·统一入口

输入:方名 + skill 选择
  - skill A(默认):方族谱查询
  - skill B:跨书演化时间轴
  - skill C:跨祖方家族对比
  - skill both:Skill A + B
  - skill all:Skill A + B + C

用法:
    python3 run_zugfang.py "甘姜苓术汤"            # 默认 Skill A
    python3 run_zugfang.py "甘姜苓术汤" --a      # 显式 Skill A
    python3 run_zugfang.py "甘姜苓术汤" --b      # 显式 Skill B
    python3 run_zugfang.py "甘姜苓术汤" --c 桂枝汤 五苓散  # Skill C 多方对比
    python3 run_zugfang.py "甘姜苓术汤" --both   # Skill A+B
    python3 run_zugfang.py "甘姜苓术汤" --all     # A+B+C
    python3 run_zugfang.py "甘姜苓术汤" --a --detail 10  # Skill A 详情模式
"""
import sys
import argparse
from pathlib import Path

THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR))

from zugfang_family_parser import parse_zugfang_chapter
from family_tree import render_family_tree, render_overview
from evolution_timeline import run_evolution
from cross_family_compare import render_cross_family_compare
from zheng_lookup import render_zheng_lookup


def main():
    parser = argparse.ArgumentParser(
        description="祖方演化分析 — 医通祖方族谱 + 跨书演化时间轴 + 跨祖方家族对比",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    %(prog)s "理中汤"          # Skill A:方族谱(默认)
    %(prog)s "肾着汤" --a     # Skill A(显式)
    %(prog)s "肾着汤" --b     # Skill B:演化时间轴
    %(prog)s "肾着汤" --c "桂枝汤" "五苓散"  # Skill C:跨祖方家族对比
    %(prog)s "理中汤" --a --detail 10  # 展第 10 个变法方全文
        """,
    )
    parser.add_argument(
        "formula",
        nargs="?",
        help="方剂名称,如「理中汤」「甘姜苓术汤」「五苓散」(不指定则跑 36 方祖概览)",
    )
    # Skill C 额外参数:支持多对方剂
    parser.add_argument(
        "formulas",
        nargs="*",
        help="(仅 Skill C 使用)其他方剂名,作横向对比",
    )
    skill_group = parser.add_mutually_exclusive_group()
    skill_group.add_argument("--a", action="store_true", help="Skill A:方族谱查询")
    skill_group.add_argument("--b", action="store_true", help="Skill B:跨书演化时间轴")
    skill_group.add_argument("--c", action="store_true", help="Skill C:跨祖方家族对比(需 2-3 个方)")
    skill_group.add_argument("--z", action="store_true", help="Skill C.2:病证反查(输入病证关键词,如「寒湿腰痛」「痞证」「咳嗽」)")
    skill_group.add_argument("--both", action="store_true", help="Skill A + Skill B")
    skill_group.add_argument("--all", action="store_true", help="Skill A + Skill B + Skill C")
    parser.add_argument(
        "--detail",
        type=int,
        default=None,
        help="Skill A 详情标志:展开第 N 个变法方的全文(默认只显示 60 字摘要)",
    )

    args = parser.parse_args()
    all_formulas = [args.formula] + args.formulas if args.formula else args.formulas

    if args.c:
        if len(all_formulas) < 2:
            print("⚠️  Skill C 需要 2-3 个方剂作对比,例如:")
            print('  python3 run_zugfang.py --c "肾着汤" "五苓散" "桂枝汤"')
            sys.exit(1)
        run_skill_c(all_formulas)
    elif args.z:
        if not args.formula:
            print("⚠️  Skill C.2 病证反查需要病证关键词,如:")
            print('  python3 run_zugfang.py --z "寒湿腰痛"')
            sys.exit(1)
        run_skill_z(args.formula)
    elif args.b:
        run_skill_b(args.formula)
    elif args.both:
        run_skill_a(args.formula, args.detail)
        print("\n\n")
        print("=" * 80)
        print("=" * 80)
        print("\n")
        run_skill_b(args.formula)
    elif args.all:
        run_skill_a(args.formula, args.detail)
        print("\n\n")
        print("=" * 80)
        print("=" * 80)
        print("\n")
        run_skill_b(args.formula)
        print("\n\n")
        print("=" * 80)
        print("=" * 80)
        print("\n")
        if len(all_formulas) >= 2:
            run_skill_c(all_formulas)
        else:
            print("⚠️  Skill C 需要 2-3 个方剂,跳过 Skill C")
    elif args.formula is None:
        run_skill_overview()
    else:
        run_skill_a(args.formula, args.detail)


def run_skill_a(formula, detail_idx=None):
    zudfang = parse_zugfang_chapter()
    print(render_family_tree(zudfang, formula, detail_idx))


def run_skill_b(formula):
    print(run_evolution(formula))


def run_skill_c(formulas):
    zudfang = parse_zugfang_chapter()
    print(render_cross_family_compare(zudfang, formulas))


def run_skill_z(zheng):
    zudfang = parse_zugfang_chapter()
    zz_db = str(THIS_DIR.parent / "external" / "zysj.db")
    print(render_zheng_lookup(zz_db, zudfang, zheng))


def run_skill_overview():
    zudfang = parse_zugfang_chapter()
    print(render_overview(zudfang))


if __name__ == "__main__":
    main()
