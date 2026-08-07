"""
Skill A:方族谱(zugfang-family-tree)

输入:方名(如「理中汤」「甘姜苓术汤」「五苓散」)
输出:ASCII 树形方族谱 + 变法方速查表
  - 草案 3 格式:第一段 60 字摘要 + 详情标志(`--detail X` 展全文)

数据源:ysjllsj.TypeID=495 ID 98643~98679(纯醫通祖方)

使用:
    from family_tree import run_family_tree
    print(run_family_tree("甘姜苓术汤"))
    print(run_family_tree("甘姜苓术汤", detail_idx=10))  # 展全文
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from zugfang_family_parser import (
    parse_zugfang_chapter,
    find_zudfang_for_formula,
    get_var_methods_summary,
)


def render_family_tree(zudfang_list, formula, detail_idx=None) -> str:
    """主入口 — 渲染方族谱"""
    hits = find_zudfang_for_formula(zudfang_list, formula)
    if not hits:
        return render_no_hit(formula)
    return render_single_zudfang(hits, formula, detail_idx)


def render_no_hit(formula: str) -> str:
    out = []
    out.append("╔════════════════════════════════════════════════════════════════╗")
    out.append(f"║  方族谱查询:「{formula}」 — 醫通祖方(张璐《张氏医通》卷十六)         ║")
    out.append("╠════════════════════════════════════════════════════════════════╣")
    out.append(f"║  ❌ 「{formula}」未在《醫通祖方》33 个方祖谱系中                                ║")
    out.append("║                                                                              ║")
    out.append("║  可能的原因:                                                                ║")
    out.append("║    1. 此方不在张璐选定的 32 核心方祖列表里                                  ║")
    out.append("║    2. 此方名用了别名 — 试 Skill B 跨书查找                                  ║")
    out.append("║    3. 此方是张氏医通卷六散在应用 — 看 Skill B 输出散在章节引文         ║")
    out.append("║                                                                              ║")
    out.append("║  → 用 Skill B(zugfang-evolution-timeline)查跨书演化                          ║")
    out.append("╚════════════════════════════════════════════════════════════════╝")
    return "\n".join(out)


def render_single_zudfang(hits, formula, detail_idx) -> str:
    out = []
    out.append("╔════════════════════════════════════════════════════════════════╗")
    out.append(f"║  方族谱:「{formula}」                                                       ║")
    out.append(f"║  数据源:ysjllsj.TypeID=495 (张璐《张氏医通》卷十六·祖方 1695)           ║")
    out.append("╠════════════════════════════════════════════════════════════════╣")

    # 按祖方分组(大多数命中在 1 个祖方,极少数横跨)
    by_zudfang = {}
    for z, b in hits:
        by_zudfang.setdefault(z["祖方ID"], (z, []))[1].append(b)

    for zid, (z, hit_bianfa) in by_zudfang.items():
        out.append("║")
        out.append(f"║  📖 方祖:[{zid}] 《{z['祖方名']}》")
        out.append(f"║     └─ 变法方家族(全部 {len(z['变法方'])} 个):")
        out.append("║")

        hit_names = {b["name"] for b in hit_bianfa}

        for i, b in enumerate(z["变法方"], 1):
            # 标星高亮你查的
            is_target = b["name"] in hit_names
            marker = "★" if is_target else " "

            source_short = b["source"] if b["source"] else "(张璐)"
            # 草案 3:默认 60 字摘要,detail_idx 展全文
            if detail_idx is not None and detail_idx == i:
                zheng_show = b["zheng_full"][:500].replace("\r", " ")
            else:
                zheng_show = b["zheng_short"][:60].replace("\n", " ")

            # 单行格式:[marker] [i] 名称(出处) | 治证摘要 [详情]
            line = f"║  {marker} [{i:2d}] {b['name']}  ({source_short})  │  {zheng_show}"
            if detail_idx is not None and detail_idx != i:
                line += "  ⋯(用 --detail N 展全文)"
            elif is_target and detail_idx is None:
                line += "  ← 你查的"
            out.append(line)

        out.append("║")

        # 加减法速查表
        out.append("║  ── 加减法速查表 ──")
        out.append("║")
        for i, b in enumerate(z["变法方"], 1):
            is_target = b["name"] in hit_names
            tag = " ★" if is_target else "  "
            method = b.get("method_zh", "—")[:50]
            out.append(f"║  {tag}[{i:2d}] {b['name']:<18} │ 法:{method}")

        out.append("║")

        # 一句话心法
        if len(hit_bianfa) == 1:
            b_target = hit_bianfa[0]
            idx_in_list = z["变法方"].index(b_target) + 1
            out.append(
                f"║  💡 一句话心法:"
            )
            out.append(
                f"║     「{b_target['method_zh'][:50] or '(加减法未标)'}」"
            )
            out.append(
                f"║     → 在理中汤家族(共 {len(z['变法方'])} 个变法方)中排名 # {idx_in_list}"
            )
            out.append(
                f"║     → 张璐定位:「{b_target['source'] or '张璐自拟'}」"
            )

    out.append("╚════════════════════════════════════════════════════════════════╝")
    return "\n".join(out)


def render_overview(zudfang_list) -> str:
    """概览:统计 + 全部 33 方祖列表"""
    out = []
    out.append("╔════════════════════════════════════════════════════════════════╗")
    out.append("║  醫通祖方 全谱概览(张璐《张氏医通》卷十六 1695)                       ║")
    out.append("╠════════════════════════════════════════════════════════════════╣")
    stats = get_var_methods_summary(zudfang_list)
    out.append(f"║  方祖数:{stats['方祖数']} | 变法方总数:{stats['变法方总数']} (均 {stats['平均每方祖变法方数']}/祖)      ║")
    out.append(f"║  张璐自拟变法方:{stats['张璐自拟变法方']} | 引用他书变法方:{stats['引用他书变法方']}                ║")
    out.append("║")
    out.append("║  ── 33 方祖列表 ──")
    out.append("║")

    for i, z in enumerate(zudfang_list, 1):
        out.append(f"║  [{i:2d}] [{z['祖方ID']}] 《{z['祖方名']}》  ({len(z['变法方'])} 变法方)")

    out.append("╚════════════════════════════════════════════════════════════════╝")
    return "\n".join(out)


# === CLI 入口 ===
if __name__ == "__main__":
    zudfang = parse_zugfang_chapter()

    if len(sys.argv) < 2:
        print(render_overview(zudfang))
        sys.exit(0)

    formula = sys.argv[1]

    # 解析 --detail N
    detail_idx = None
    if "--detail" in sys.argv:
        i = sys.argv.index("--detail")
        if i + 1 < len(sys.argv):
            try:
                detail_idx = int(sys.argv[i + 1])
            except ValueError:
                pass

    print(render_family_tree(zudfang, formula, detail_idx))
