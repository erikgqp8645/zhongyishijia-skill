"""
Skill C.2:病证 → 多祖方交叉反查

输入:病证关键词(如「寒湿腰痛」「咳嗽」「痞证」「心悸」「不寐」)
输出:所有祖方/变法方里主治含此证者 + 横向对比

数据源(3 源拼接):
  1) zysjllsj.TypeID=495 ID 98643~98679 变法方 zheng_full(医通祖方结构)
  2) zysjllsj.TypeID=495 卷六散在引用(所有「病证」章节 ID 98216 腰痛 / 98226 咳嗽 ...)
  3) query_formula 历代医家论述(jsonl 全文检索)

实现策略:
  Step 1:ysjllsj SQL LIKE 匹配 zheng_full 含病证关键词
  Step 2:对每个命中祖方/变法方,生成详细卡片
  Step 3:输出 markdown 表格横向对比
"""
import sqlite3
import re
import sys
from pathlib import Path

THIS_DIR = Path(__file__).parent
sys.path.insert(0, str(THIS_DIR))

from zugfang_family_parser import parse_zugfang_chapter


# 病证词典(常用证型关键词 → 可搜索的同义词集)
ZHENG_DICT = {
    "寒湿腰痛": ["寒湿", "湿寒", "湿冷", "腰冷"],
    "湿热腰痛": ["湿热", "热湿"],
    "咳嗽": ["咳嗽", "咳逆", "咳喘", "嗽"],
    "痞证": ["痞", "心下痞", "胸痞", "脘痞"],
    "心悸": ["心悸", "怔忡", "心动悸"],
    "不寐": ["不寐", "不得卧", "不得眠", "失眠"],
    "痰湿": ["痰", "痰饮", "痰湿"],
    "痞满": ["痞满", "痞胀", "满闷"],
    "虚寒": ["虚寒", "虚冷", "寒虚"],
    "实热": ["实热", "热盛", "里热"],
    "阳虚": ["阳虚", "亡阳"],
    "阴虚": ["阴虚", "亡阴", "虚热"],
    "湿滞经络": ["湿滞经络", "湿痹", "湿着"],
    "水饮": ["水饮", "饮停", "停饮", "蓄水"],
    "泻泄": ["泻泄", "泄泻", "下利", "五更泻"],
    "带下": ["带下", "白带", "赤带"],
    "崩漏": ["崩漏", "崩中", "漏下"],
    "痰饮": ["痰饮", "支饮", "悬饮", "溢饮"],
    "水肿": ["水肿", "肿胀", "浮肿"],
    "自汗": ["自汗", "汗出", "汗多"],
    "发热": ["发热", "热", "烦热"],
    "恶寒": ["恶寒", "畏寒", "寒热"],
}


def expand_zheng_to_keywords(zheng):
    """输入「寒湿腰痛」→ 展开为 [「寒湿」,「湿寒」,「湿冷」,「腰冷」]"""
    if zheng in ZHENG_DICT:
        return ZHENG_DICT[zheng]
    # 简单按字拆 + 全文匹配
    return [zheng]


def search_zugfang_for_zheng(zudfang_list, zheng):
    """返回祖方/变法方 里含此证的所有记录"""
    keywords = expand_zheng_to_keywords(zheng)
    hits = []
    for z in zudfang_list:
        # 祖方本身主治
        zhengren_text = z.get("原方_主治", "") or ""
        if any(kw in zhengren_text for kw in keywords):
            hits.append({
                "type": "祖方",
                "祖方名": z["祖方_short_name"],
                "祖方ID": z["祖方ID"],
                "变法方名": "-",
                "主治": zhengren_text,
                "加减法": "-",
            })
        # 变法方主治
        for b in z["变法方"]:
            zf = b.get("zheng_full", "") or ""
            if any(kw in zf for kw in keywords):
                hits.append({
                    "type": "变法方",
                    "祖方名": z["祖方_short_name"],
                    "祖方ID": z["祖方ID"],
                    "变法方名": b["name"],
                    "主治": b.get("zheng_short", "")[:60],
                    "加减法": b.get("method_zh", "")[:40],
                })
    return hits, keywords


def dedupe_hits(hits):
    """按 (TypeID, ID) 去重"""
    seen = set()
    out = []
    for h in hits:
        key = (h.get("TypeID"), h.get("ID"))
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def search_zysjllsj_for_zheng(zz_db_path, zheng, typeid_filter=None):
    """直接在 zysjllsj 里搜索病证"""
    keywords = expand_zheng_to_keywords(zheng)
    conn = sqlite3.connect(zz_db_path)
    c = conn.cursor()
    hits = []
    for kw in keywords:
        if typeid_filter:
            c.execute(
                "SELECT TypeID, ID, BiaoTi, substr(NeiRong, 1, 200) FROM zysjllsj "
                "WHERE TypeID=? AND NeiRong LIKE ? LIMIT 20",
                (typeid_filter, f"%{kw}%"),
            )
        else:
            c.execute(
                "SELECT TypeID, ID, BiaoTi, substr(NeiRong, 1, 200) FROM zysjllsj "
                "WHERE NeiRong LIKE ? LIMIT 30",
                (f"%{kw}%",),
            )
        for row in c.fetchall():
            hits.append({
                "type": "散在引用",
                "TypeID": row[0],
                "ID": row[1],
                "BiaoTi": row[2],
                "NeiRong_preview": row[3],
            })
    conn.close()
    return dedupe_hits(hits)


def render_zheng_lookup(zz_db_path, zudfang_list, zheng):
    """主渲染函数"""
    out = []
    out.append("╔════════════════════════════════════════════════════════════════╗")
    out.append(f"║  病证反查:「{zheng}」")
    out.append(f"║  数据源:ysjllsj.TypeID=495 (医通祖方) + zysjllsj 全文检索")
    out.append("╠════════════════════════════════════════════════════════════════╣")

    keywords = expand_zheng_to_keywords(zheng)
    out.append(f"║")
    out.append(f"║  展开的同义词: {keywords}")
    out.append(f"║")

    # ─── Step 1: 医通祖方(变法方)命中的祖方/变法方 ───
    out.append(f"║  ── 1. 医通祖方结构中命中的祖方/变法方 ──")
    out.append(f"║")
    zugfang_hits, _ = search_zugfang_for_zheng(zudfang_list, zheng)
    if not zugfang_hits:
        out.append(f"║  (医通祖方结构中未命中 — 此病证可能散在其他章节)")
    else:
        # 按祖方归类
        by_zudfang = {}
        for h in zugfang_hits:
            by_zudfang.setdefault(h["祖方名"], []).append(h)
        out.append(f"║  命中 {len(zugfang_hits)} 条,分布于 {len(by_zudfang)} 个祖方")
        out.append(f"║")
        out.append(f"║     ┌──────────────────┬──────────────────┬────────────────────────┐")
        out.append(f"║     │ 祖方              │ 变法方            │ 主治证                  │")
        out.append(f"║     ├──────────────────┼──────────────────┼────────────────────────┤")
        for zname, hs in sorted(by_zudfang.items(), key=lambda x: -len(x[1])):
            for i, h in enumerate(hs):
                zname_show = zname if i == 0 else ""
                out.append(
                    f"║     │ {zname_show:<16} │ {h['变法方名'][:16]:<16} │ {h['主治'][:22]:<22} │"
                )
        out.append(f"║     └──────────────────┴──────────────────┴────────────────────────┘")

    # ─── Step 2: zysjllsj 全文检索 ───
    out.append(f"║")
    out.append(f"║  ── 2. zysjllsj 全文检索散在引用(不限 TypeID) ──")
    out.append(f"║")
    zysj_hits = search_zysjllsj_for_zheng(zz_db_path, zheng, typeid_filter=495)
    if not zysj_hits:
        out.append(f"║  (zysjllsj 中未命中 TypeID=495 散在引用)")
    else:
        out.append(f"║  命中 {len(zysj_hits)} 条 TypeID=495 散在章节:")
        out.append(f"║")
        out.append(f"║     ┌──────────┬────────────────────────┬────────────────────────┐")
        out.append(f"║     │ ID       │ BiaoTi                  │ 原文摘要                │")
        out.append(f"║     ├──────────┼────────────────────────┼────────────────────────┤")
        for h in zysj_hits[:15]:
            out.append(
                f"║     │ {h['ID']:<8} │ {h['BiaoTi'][:22]:<22} │ {h['NeiRong_preview'][:22]:<22} │"
            )
        out.append(f"║     └──────────┴────────────────────────┴────────────────────────┘")

    # ─── Step 3: 一句话洞察 ───
    out.append(f"║")
    out.append(f"║  ── 3. 临床洞察 ──")
    out.append(f"║")
    # 提前计算归类(后续 step 4 也要用)
    by_zudfang = {}
    for h in zugfang_hits:
        by_zudfang.setdefault(h["祖方名"], []).append(h)

    if zugfang_hits:
        n_zudfang_count = len(by_zudfang)
        top_zudfang = max(by_zudfang.items(), key=lambda x: len(x[1]))
        out.append(f"║  病证「{zheng}」在《醫通祖方》结构中分布于 {n_zudfang_count} 个祖方,")
        out.append(f"║  其中「{top_zudfang[0]}」家族覆盖最广({len(top_zudfang[1])} 条变法方)。")
        out.append(f"║  → 临床选方路径:先看「{top_zudfang[0]}」家族变法方是否对症,再扩展到其他家族。")
    else:
        out.append(f"║  「{zheng}」未直接命中《醫通祖方》结构,")
        out.append(f"║  → 建议查 TypeID=495 卷六散在章节,或 query_formula 全文检索。")
    out.append(f"╚════════════════════════════════════════════════════════════════╝")
    return "\n".join(out)


# === CLI 入口 ===
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 zheng_lookup.py <病证关键词>")
        print("示例: python3 zheng_lookup.py 寒湿腰痛")
        sys.exit(1)
    zudfang = parse_zugfang_chapter()
    zz_db = str(THIS_DIR.parent / "external" / "zysj.db")
    print(render_zheng_lookup(zz_db, zudfang, sys.argv[1]))