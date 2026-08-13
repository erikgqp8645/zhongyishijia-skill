"""
Skill C.1 原型:跨祖方家族对比(cross_family_compare)

输入: 2-3 个方剂名
输出:
  - 各方所属祖方 + 在祖方家族中的位置
  - 加减法对比(若都在某祖方家族)
  - 朝代时间轴重叠度
  - 一句话对比心法

不依赖 Skill A/B 的 ASCII 输出,直接结构化 Markdown 表格。
"""
import re
import sys
from pathlib import Path

THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR))

from zugfang_family_parser import (
    parse_zugfang_chapter,
    find_zudfang_for_formula,
)
from evolution_timeline import (
    run_query_formula,
    get_cross_book_hits,
    get_scattered_yongj_in_zhangshiyitong,
)


def find_zudfang_of_formula(zudfang_list, formula):
    """返回 (方祖, 变法方, 角色) 列表

    优先级:
    1. 完全等值祖方名(如「桂枝汤」就是祖方「桂枝汤(玉函)」)
    2. 变法方含查询词(如「肾着汤」是理中汤家族变法方)
    """
    # 优先级 1: 等值祖方名(去掉「(玉函)」「(金匮)」等后缀)
    short = re.sub(r"[（(][^)）]*[)）]", "", formula).strip()
    for z in zudfang_list:
        z_short = re.sub(r"[（(][^)）]*[)）]", "", z["祖方名"]).strip()
        if z_short == short or z["祖方_short_name"] == short:
            # 命中祖方本身
            # 创建一个伪"变法方"标识其就是祖方
            return [(z, {"name": z["祖方_short_name"], "source": "(祖方)",
                          "zheng_short": "本祖方",
                          "method_zh": "(本祖方,无加减法)", "is_zhanglu": True}, "祖方")]

    # 优先级 2: 变法方包含查询词
    hits = find_zudfang_for_formula(zudfang_list, formula)
    return [(z, b, "变法方") for z, b in hits]


def get_dynasty_set_for_formula(formula):
    """返回某方剂出现在 query_formula 里的朝代集合"""
    qf = run_query_formula(formula)
    qf = [x for x in qf if "error" not in x]
    dynasties = set()
    for q in qf:
        if q.get("dynasty") and q["dynasty"] != "(待考)":
            dynasties.add(q["dynasty"])
    return dynasties


def get_scattered_chapters_count(formula):
    """返回散在引用章节数"""
    scattered = get_scattered_yongj_in_zhangshiyitong(formula)
    return len(scattered)


def get_cross_book_count(formula):
    """返回跨书命中数"""
    cross = get_cross_book_hits(formula)
    return {title: len(hits) for title, hits in cross.items()}


def render_cross_family_compare(zudfang_list, formulas):
    """主渲染函数"""
    out = []
    out.append("╔════════════════════════════════════════════════════════════════╗")
    out.append(f"║  跨祖方家族对比:{len(formulas)} 个方剂")
    out.append(f"║  数据源:ysjllsj.TypeID=495 (张璐《张氏医通》卷十六·祖方 1695)")
    out.append("╠════════════════════════════════════════════════════════════════╣")

    # 1. 各方所属祖方 + 完整详情
    out.append("║")
    out.append("║  ── 1. 各方所属祖方(完整详情) ──")
    out.append("║")
    formula_info = []
    for f in formulas:
        hits = find_zudfang_of_formula(zudfang_list, f)
        scattered_n = get_scattered_chapters_count(f)
        dynasty_set = get_dynasty_set_for_formula(f)
        cross_books = get_cross_book_count(f)
        if hits:
            z, b, role = hits[0]
            # 在家族中的位置
            if role == "祖方":
                idx_in_z = "本祖方"
                total_in_z = len(z["变法方"])
            else:
                idx_in_z = z["变法方"].index(b) + 1
                total_in_z = len(z["变法方"])
            role_marker = "★ 本祖方" if role == "祖方" else f"变法方 #{idx_in_z}"
            out.append(f"║  📍「{f}」({role})")
            out.append(f"║     → 祖方:{z['祖方名']} [{z['祖方ID']}]")
            out.append(f"║     → 角色:{role_marker} / 共 {total_in_z} 个")
            out.append(f"║     → 加减法:{b.get('method_zh', '(无)')}")
            out.append(f"║     → 主治证:{b.get('zheng_short', '(无)')[:80]}")
            # 病因:从 zheng_full 末尾取按语(张璐/王肯堂的引申,通常是「X者。Y也。」)
            zf = b.get("zheng_full", "")
            # 取 zheng_full 第一个「。」之后的内容作为按语/病因
            parts = zf.split("。", 2)
            if len(parts) >= 3 and parts[2].strip():
                bingyin = parts[2].strip()[:80]
                out.append(f"║     → 病因/按语:{bingyin}")
            # ★ 本祖方额外信息:原方组成 + 煎服法
            if role == "祖方":
                out.append(f"║")
                out.append(f"║     ★【本祖方原方】")
                out.append(f"║     → 治证:{z.get('原方_主治', '')}")
                out.append(f"║     → 组成:{z.get('原方_组成', '')}")
                out.append(f"║     → 煎服:{z.get('原方_煎服法', '')}")
            # 散在/跨书/朝代
            out.append(f"║     → 散在引用:{scattered_n} 章节 (张氏医通卷六)")
            out.append(f"║     → 跨书命中:{cross_books}")
            out.append(f"║     → 朝代覆盖:{sorted(dynasty_set)}")
            formula_info.append({
                "formula": f,
                "role": role,
                "zudfang": z,
                "bianfa": b,
                "idx": idx_in_z,
                "total": total_in_z,
                "scattered": scattered_n,
                "cross": cross_books,
                "dynasties": dynasty_set,
            })
        else:
            out.append(f"║  📍「{f}」")
            out.append(f"║     → ❌ 不在《醫通祖方》33 个方祖谱系")
            out.append(f"║     → 散在引用:{scattered_n} 章节")
            out.append(f"║     → 朝代覆盖:{sorted(dynasty_set)}")
            formula_info.append({
                "formula": f,
                "role": None,
                "zudfang": None,
                "scattered": scattered_n,
                "cross": cross_books,
                "dynasties": dynasty_set,
            })
    # 2. 祖方交集
    out.append("║")
    out.append("║  ── 2. 祖方关系图 ──")
    out.append("║")
    in_zud = [fi for fi in formula_info if fi.get("zudfang")]
    zudfang_ids = set(fi["zudfang"]["祖方ID"] for fi in in_zud)
    if len(zudfang_ids) == 1:
        z = in_zud[0]["zudfang"]
        out.append(f"║  ✅ 所有 {len(formulas)} 个方都在同一个祖方:{z['祖方名']}")
    elif len(zudfang_ids) == len(in_zud):
        out.append(f"║  ⚠️  {len(in_zud)} 个方分布在 {len(zudfang_ids)} 个不同的祖方")
        out.append(f"║     (无共同祖方)")
    elif len(zudfang_ids) == 0:
        out.append(f"║  ❌ 没有方在《醫通祖方》谱系")
    else:
        out.append(f"║  ✅ {len(in_zud)} 个方分布:")
        for zid in zudfang_ids:
            fs = [fi["formula"] for fi in in_zud if fi["zudfang"]["祖方ID"] == zid]
            zname = next(fi["zudfang"]["祖方名"] for fi in in_zud if fi["zudfang"]["祖方ID"] == zid)
            out.append(f"║     祖方 {zid} ({zname}):共 {len(fs)} 方 - {' / '.join(fs)}")

    # 3. 同族变法方全表 + 加减法对比
    out.append("║")
    out.append("║  ── 3. 同族变法方全表(各祖方家族所有变法方) ──")
    out.append("║")
    # 收集有 zudfang 的方 + 它们所在的祖方家族
    families_to_show = {}
    for fi in formula_info:
        if fi.get("zudfang"):
            z = fi["zudfang"]
            zid = z["祖方ID"]
            if zid not in families_to_show:
                families_to_show[zid] = {"zudfang": z, "queries": []}
            families_to_show[zid]["queries"].append(fi["formula"])

    if not families_to_show:
        out.append(f"║  (没有方在《醫通祖方》谱系,无家族可列)")
    else:
        for zid, info in families_to_show.items():
            z = info["zudfang"]
            queries = info["queries"]
            out.append(f"║")
            out.append(f"║  📖 祖方《{z['祖方名']}》[{zid}](共 {len(z['变法方'])} 个变法方)")
            out.append(f"║     你查的方在这:{', '.join(queries)}")
            out.append(f"║")
            out.append(f"║     ┌────┬──────────────────────────┬──────────────────┬──────────┐")
            out.append(f"║     │ #  │ 变法方名                    │ 加减法             │ 主治证   │")
            out.append(f"║     ├────┼──────────────────────────┼──────────────────┼──────────┤")
            for i, b in enumerate(z["变法方"], 1):
                # 高亮你查的方
                is_query = b["name"] in queries
                marker = " ★ " if is_query else "   "
                name_short = b["name"][:22]
                method = b.get("method_zh", "")[:16]
                zheng = b.get("zheng_short", "")[:8]
                out.append(f"║     │{marker}{i:2d} │ {name_short:<24} │ {method:<16} │ {zheng:<8} │")
            out.append(f"║     └────┴──────────────────────────┴──────────────────┴──────────┘")

    # 3.5 加减法模式汇总
    out.append("║")
    out.append("║  ── 4. 加减法模式汇总 ──")
    out.append("║")
    in_zud_with_method = [
        fi for fi in formula_info
        if fi.get("role") == "变法方"
        and fi.get("bianfa")
        and fi["bianfa"].get("method_zh")
        and "本祖方" not in fi["bianfa"]["method_zh"]
    ]
    if not in_zud_with_method:
        out.append(f"║  (你查的方都不是某个祖方家族的变法方,无显式加减法可对比)")
        out.append(f"║  → 它们都是本祖方或不在《醫通祖方》谱系,加减法对比需查跨书注解)")
    else:
        # 4a. 关键词频率统计
        keyword_count = {}
        for fi in in_zud_with_method:
            m = fi["bianfa"]["method_zh"]
            for kw in ["加", "减", "去", "入", "合", "化", "变", "易", "换"]:
                if kw in m:
                    keyword_count[kw] = keyword_count.get(kw, 0) + 1
        out.append(f"║  4a. 加减法关键词频率(在你查的变法方里):")
        for kw, cnt in sorted(keyword_count.items(), key=lambda x: -x[1]):
            out.append(f"║      「{kw}」:{cnt} 次")
        out.append(f"║")
        # 4b. 你查的变法方逐方展开
        out.append(f"║  4b. 你查的变法方逐方详表:")
        out.append(f"║")
        out.append(f"║     ┌──────────────────┬────────────────────────────────────┬──────────┐")
        out.append(f"║     │ 方剂              │ 加减法(原书原文)                │ 主治证    │")
        out.append(f"║     ├──────────────────┼────────────────────────────────────┼──────────┤")
        for fi in in_zud_with_method:
            m = fi["bianfa"].get("method_zh", "")[:34]
            z = fi["bianfa"].get("zheng_short", "")[:8]
            out.append(f"║     │ {fi['formula']:<16} │ {m:<34} │ {z:<8} │")
        out.append(f"║     └──────────────────┴────────────────────────────────────┴──────────┘")

    # 5. 朝代覆盖对比
    out.append("║")
    out.append("║  ── 5. 朝代覆盖对比 ──")
    out.append("║")
    dynasty_order = ["先秦", "东汉", "三国", "晋", "南北朝",
                      "唐", "宋", "元", "明", "清", "近代", "现代", "待考"]
    out.append(f"║  ┌{'─' * 14}┬{'─' * 18}┬{'─' * 12}┐")
    out.append(f"║  │{'方剂':<14}│{'出现在哪些朝代':<18}│{'朝代数':<12}│")
    out.append(f"║  ├{'─' * 14}┼{'─' * 18}┼{'─' * 12}┤")
    for fi in formula_info:
        ds = fi["dynasties"]
        ds_ordered = [d for d in dynasty_order if d in ds]
        out.append(f"║  │{fi['formula']:<14}│{','.join(ds_ordered):<18}│{len(ds):<12}│")
    out.append(f"║  └{'─' * 14}┴{'─' * 18}┴{'─' * 12}┘")

    # 共同朝代
    common_dynasties = set.intersection(*[fi["dynasties"] for fi in formula_info]) if all(fi["dynasties"] for fi in formula_info) else set()
    if common_dynasties:
        out.append(f"║  所有方都出现的朝代:{sorted(common_dynasties)}")

    # 6. 一句话心法
    out.append("║")
    out.append("║  ── 6. 一句话对比心法 ──")
    out.append("║")
    if len(in_zud) == len(formula_info):
        # 全部在《醫通祖方》谱系
        # 找最大家族 / 最大家族位置
        if in_zud:
            biggest = max(in_zud, key=lambda fi: fi["total"])
            smallest = min(in_zud, key=lambda fi: fi["total"])
            out.append(f"║  「{len(formulas)} 方均出自《醫通祖方》家族」")
            out.append(f"║   最大家族:{biggest['zudfang']['祖方名']}({biggest['total']} 变法方)")
            out.append(f"║   最小家族:{smallest['zudfang']['祖方名']}({smallest['total']} 变法方)")
            out.append(f"║   共同朝代:{sorted(common_dynasties) if common_dynasties else '(无交集)'}")
    else:
        not_in = [fi["formula"] for fi in formula_info if not fi.get("zudfang")]
        out.append(f"║  {len(formulas) - len(not_in)}/{len(formulas)} 方在《醫通祖方》谱系")
        out.append(f"║  不在谱系的方:{', '.join(not_in)}")
        out.append(f"║  → 这些方需要用 Skill B 查跨书演化")

    out.append("╚════════════════════════════════════════════════════════════════╝")
    return "\n".join(out)


# === CLI 入口 ===
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 cross_family_compare.py <方剂1> <方剂2> [<方剂3> ...]")
        print("示例: python3 cross_family_compare.py 肾着汤 五苓散 桂枝汤")
        sys.exit(1)
    zudfang = parse_zugfang_chapter()
    print(render_cross_family_compare(zudfang, sys.argv[1:]))
