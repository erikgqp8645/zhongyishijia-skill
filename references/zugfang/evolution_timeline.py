"""
Skill B:演化时间轴(zugfang-evolution-timeline)

输入:方名
输出:跨书跨朝代的演化时间轴(东汉 → 唐 → 宋 → 明 → 清 → 现代)

数据源(5 源拼接):
  1) zysjllsj.TypeID=495 卷十六祖方(ID 98643~98679) — 醫通祖方结构
  2) ysjllsj.TypeID=495 卷六散在引用(身重/湿门/腰痛/痿/脚心痛)
  3) query_formula.py — 全文检索(jsonl 31.76 万卡片)
  4) books_json/0544_证治准绳类方.json — 王肯堂·明
  5) books_json/0760_退思集类方歌注.json — 尤怡/王泰林·清
  6) books_json/0721_秘传证治要诀及类方.json — 戴思恭·明

使用:
    from evolution_timeline import run_evolution
    print(run_evolution("甘姜苓术汤"))
"""
import sqlite3
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

ROOT = Path("/Users/applemima1111/.hermes/skills/zhongyishijia-expert-mentor-lineage")
DB_PATH = ROOT / "references/external/zysj.db"

# 朝代映射(根据 BiaoTi 中的「朝代:XX」字段提取)
DYNASTY_PAT = re.compile(r"作者[^]*?朝代[:：]?\s*([\u4e00-\u9fff·]+?)(?:\s|·|$)")


def query_text_in_book(book_path: Path, formula: str, exact_match: bool = True) -> List[Dict]:
    """在单本 books_json 中查方名出现位置"""
    if not book_path.exists():
        return []
    data = json.loads(book_path.read_text())
    out = []
    for ch in data.get("chapters", []):
        ch_title = ch.get("title", "")
        if not ch_title:
            sec = ch.get("sections", [])
            if sec and sec[0].get("entries"):
                ch_title = sec[0]["entries"][0].get("title", "")
        for sec in ch.get("sections", []):
            for e in sec.get("entries", []):
                content = (e.get("title", "") + e.get("content", "")).strip()
                if not content:
                    continue
                if exact_match and formula not in content:
                    continue
                # 提取片段
                idx = content.find(formula)
                snippet = (
                    content[max(0, idx - 40):idx + len(formula) + 80]
                    if idx >= 0 else content[:120]
                )
                out.append({
                    "chapter": ch_title,
                    "snippet": snippet.replace("\n", " ")[:160],
                })
    return out


def extract_dynasty(biao_ti: str) -> str:
    """从 BiaoTi 提取朝代 + 作者"""
    m = DYNASTY_PAT.search(biao_ti)
    if m:
        return m.group(1).strip()
    return "(待考)"


def get_authors_from_yongj(gz_chapters: List[str]) -> List[str]:
    """从查询结果里提取 朝代|著作|作者 信息"""
    authors = []
    pat = re.compile(r"\|\s*(\S+)\s*\|\s*《([^》]+)》\s*\|\s*([^|]+?)\s*\|")
    for line in gz_chapters:
        m = pat.search(line)
        if m:
            authors.append({
                "dynasty": m.group(1).strip(),
                "book": m.group(2).strip(),
                "author": m.group(3).strip(),
            })
    return authors


def run_query_formula(formula: str) -> List[Dict]:
    """调用 query_formula.py 跑全文检索"""
    script = ROOT / "scripts/query_formula.py"
    try:
        proc = subprocess.run(
            ["python3", str(script), formula],
            capture_output=True, text=True, timeout=180,
        )
        output = proc.stdout
        # 提取表格行
        authors = get_authors_from_yongj(output.splitlines())
        return authors
    except Exception as e:
        return [{"error": str(e)}]


def get_cross_book_hits(formula: str) -> Dict[str, List]:
    """在 3 本類方书中查方名命中"""
    sources = {
        "王肯堂《证治准绳·类方》(明)":
            ROOT / "references/books_json/0544_证治准绳类方.json",
        "《退思集类方歌注》(清·王泰林/尤怡)":
            ROOT / "references/books_json/0760_退思集类方歌注.json",
        "戴思恭《秘传证治要诀及类方》(明)":
            ROOT / "references/books_json/0721_秘传证治要诀及类方.json",
    }
    out = {}
    for title, path in sources.items():
        hits = query_text_in_book(path, formula)
        if hits:
            out[title] = hits
    return out


def get_scattered_yongj_in_zhangshiyitong(formula: str) -> List[Dict]:
    """查《张氏医通》卷六 散在引用(身重/湿/腰痛/痿/脚心痛等)
    - 不在卷十六祖方章,而在其他章里提到此方
    """
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT ID, BiaoTi, substr(NeiRong, 1, 200)
        FROM zysjllsj
        WHERE TypeID=495
          AND NeiRong LIKE ?
          AND ID NOT BETWEEN 98643 AND 98679
        ORDER BY ID
    """, (f"%{formula}%",)).fetchall()
    conn.close()
    return [
        {"id": id_, "chapter": bt, "snippet": nr.replace("\n", " ")[:200]}
        for id_, bt, nr in rows[:20]  # 限制 20 条防爆
    ]


def render_evolution_timeline(formula: str, zudfang_in_zhanglu: List = None) -> str:
    """主入口 — 渲染跨书演化时间轴"""
    out = []
    out.append("╔══════════════════════════════════════════════════════════════════════╗")
    out.append(f"║  演化时间轴:「{formula}」                                                  ║")
    out.append(f"║  数据源(6 源拼接):ysjllsj.TypeID=495 + query_formula + 3 本類方書       ║")
    out.append("╠══════════════════════════════════════════════════════════════════════╣")
    out.append("║")
    out.append(f"║  📍 Step 1:醫通祖方定位 (张璐《张氏医通》卷十六)            ║")

    if zudfang_in_zhanglu:
        z = zudfang_in_zhanglu[0][0]
        b = zudfang_in_zhanglu[0][1]
        out.append(f"║     ✅ 「{formula}」出现在方祖《{z['祖方名']}》中")
        out.append(f"║        变法方 # {z['变法方'].index(b) + 1} / 共 {len(z['变法方'])} 个")
        out.append(f"║        加减法:{b.get('method_zh', '(无)')[:50]}")
        out.append(f"║        治证:{b['zheng_short'][:80]}")
    else:
        out.append(f"║     ⚠️ 「{formula}」不在醫通祖方谱系")

    out.append("║")
    out.append(f"║  📚 Step 2:《张氏医通》卷六 散在引用({formula})")
    scattered = get_scattered_yongj_in_zhangshiyitong(formula)
    if scattered:
        out.append(f"║     总条数:{len(scattered)} 章节")
        for s in scattered[:5]:
            out.append(f"║        [{s['id']}] {s['chapter']:<25} → {s['snippet'][:60]}...")
        if len(scattered) > 5:
            out.append(f"║        ...(还有 {len(scattered) - 5} 条)")
    else:
        out.append(f"║     (无)")

    out.append("║")
    out.append(f"║  📖 Step 3:跨書類方書 命中({formula})")
    cross = get_cross_book_hits(formula)
    if cross:
        for title, hits in cross.items():
            out.append(f"║")
            out.append(f"║  📘 {title}")
            for h in hits[:3]:
                out.append(f"║        · {h['chapter'][:30]:<30} │ {h['snippet'][:70]}...")
            if len(hits) > 3:
                out.append(f"║        ...(该书还命中 {len(hits) - 3} 处)")
    else:
        out.append(f"║     (无)")

    out.append("║")
    out.append(f"║  📜 Step 4:query_formula 历代医家论述")
    qf = run_query_formula(formula)
    qf = [x for x in qf if "error" not in x]
    if qf:
        # 按朝代排序
        out.append(f"║     总条数:{len(qf)} 位医家论述")
        # 朝代顺序
        dynasty_order = ["先秦", "东汉", "三国", "晋", "南北朝",
                          "唐", "宋", "元", "明", "清", "近代", "现代", "待考"]
        qf_sorted = sorted(
            qf,
            key=lambda x: dynasty_order.index(x["dynasty"])
            if x["dynasty"] in dynasty_order else 9999
        )
        out.append(f"║")
        out.append(f"║  按朝代时间轴:")
        for q in qf_sorted[:15]:
            out.append(
                f"║     · {q['dynasty']:5s} 《{q['book']}》 {q['author']:8s}"
            )
        if len(qf_sorted) > 15:
            out.append(f"║     ...(还有 {len(qf_sorted) - 15} 位医家论述)")
    else:
        out.append(f"║     (无 query_formula 数据 — 可能未命中关键词)")

    out.append("║")
    out.append("║  ── 一句话演化心法 ──")
    out.append("║")
    if zudfang_in_zhanglu:
        z = zudfang_in_zhanglu[0][0]
        b = zudfang_in_zhanglu[0][1]
        dynasty_first = qf[0]["dynasty"] if qf else "?"
        dynasty_last = qf[-1]["dynasty"] if qf else "?"
        out.append(
            f"║     「{formula}」从 {dynasty_first} 仲景原方 → {dynasty_last} 现代临床,"
        )
        out.append(
            f"║     在张璐《张氏医通》中被定位为「{z['祖方_short_name']}」家族"
        )
        out.append(
            f"║     变法方,加减法:{b.get('method_zh', '(无)')[:60]}。"
        )

    out.append("╚══════════════════════════════════════════════════════════════════════╝")
    return "\n".join(out)


def run_evolution(formula: str) -> str:
    from zugfang_family_parser import (
        parse_zugfang_chapter, find_zudfang_for_formula
    )
    zudfang = parse_zugfang_chapter()
    hits = find_zudfang_for_formula(zudfang, formula)
    return render_evolution_timeline(formula, hits)


# === CLI 入口 ===
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python evolution_timeline.py <方剂名>")
        print("Example: python evolution_timeline.py 甘姜苓术汤")
        sys.exit(1)
    print(run_evolution(sys.argv[1]))
