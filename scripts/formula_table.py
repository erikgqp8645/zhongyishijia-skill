#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
formula_table.py — 含某药方剂的元数据表格

启发式提取方剂元数据 (出处/作者/朝代/主治), 输出 Markdown 表格.

策略:
  1. 找 zysjllsj 表中含某药 + 标题像方剂 的章节
  2. 从章节 BiaoTi (方名) 启发式推断出处 (如 含"汤"且在伤寒章节 → 伤寒论)
  3. 从 NeiRong 提取 "治X" 句作主治

用法:
  python scripts/formula_table.py 细辛
  python scripts/formula_table.py 麻黄 --top 20
  python scripts/formula_table.py 附子 --top 15
"""

from __future__ import annotations

import argparse
import io
import re
import sqlite3
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

_SKILL_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _SKILL_ROOT / "references" / "external" / "zysj.db"

# 方名关键词 → (朝代, 出处, 作者) 启发式映射
TITLE_HEURISTIC: list[tuple[str, tuple[str, str, str]]] = [
    # 伤寒论 (张仲景)
    ("金匮", ("东汉", "《金匮要略》", "张仲景")),
    ("伤寒", ("东汉", "《伤寒论》", "张仲景")),
    # 圣济总录/局方 (宋)
    ("圣济", ("宋", "《圣济总录》", "")),
    ("局方", ("宋", "《太平惠民和剂局方》", "")),
    ("圣惠", ("宋", "《太平圣惠方》", "")),
    # 千金要方 (唐)
    ("千金", ("唐", "《千金要方》", "孙思邈")),
    # 外台秘要 (唐)
    ("外台", ("唐", "《外台秘要》", "王焘")),
    # 古今录验/延年/广济/必效 (唐·方书)
    ("古今录验", ("唐", "《古今录验》", "甄立言")),
    ("延年", ("唐", "《延年秘录》", "")),
    ("广济", ("唐", "《广济方》", "")),
    ("必效", ("唐", "《必效方》", "")),
    # 丹溪/景岳/医宗金鉴/伤寒悬解/四圣心源
    ("丹溪", ("元", "《丹溪心法》", "朱震亨")),
    ("景岳", ("明", "《景岳全书》", "张介宾")),
    ("医宗", ("清", "《医宗金鉴》", "吴谦")),
    ("悬解", ("清", "《伤寒悬解》", "黄元御")),
    ("四圣", ("清", "《四圣心源》", "黄元御")),
    ("温疫", ("清", "《伤寒温疫条辨》", "杨栗山")),
    ("医案", ("清", "《临证医案》", "")),
    # 经方实验录/伤寒金匮发微 (民国)
    ("发微", ("民国", "《伤寒金匮发微》", "曹颖甫")),
    ("实验录", ("民国", "《经方实验录》", "曹颖甫")),
    # 其它常见
    ("得效", ("元", "《世医得效方》", "危亦林")),
    ("本事", ("宋", "《本事方》", "许叔微")),
    ("三因", ("宋", "《三因方》", "陈言")),
    ("济生", ("宋", "《济生方》", "严用和")),
]

# 纯名方 → (朝代, 出处, 作者) 映射 (修复 bug: 纯名方没有《XX》标记时靠这里识别)
PURE_NAME_MAP: dict[str, tuple[str, str, str]] = {
    # 伤寒论 / 金匮要略 (张仲景)
    "麻黄汤": ("东汉", "《伤寒论》", "张仲景"),
    "桂枝汤": ("东汉", "《伤寒论》", "张仲景"),
    "小青龙汤": ("东汉", "《伤寒论》", "张仲景"),
    "大青龙汤": ("东汉", "《伤寒论》", "张仲景"),
    "理中汤": ("东汉", "《伤寒论》", "张仲景"),
    "真武汤": ("东汉", "《伤寒论》", "张仲景"),
    "四逆汤": ("东汉", "《伤寒论》", "张仲景"),
    "小建中汤": ("东汉", "《伤寒论》", "张仲景"),
    "大建中汤": ("东汉", "《金匮要略》", "张仲景"),
    "苓桂术甘汤": ("东汉", "《伤寒论》", "张仲景"),
    "五苓散": ("东汉", "《伤寒论》", "张仲景"),
    "当归芍药散": ("东汉", "《金匮要略》", "张仲景"),
    "麻黄附子细辛汤": ("东汉", "《伤寒论》", "张仲景"),
    "当归四逆汤": ("东汉", "《伤寒论》", "张仲景"),
    "小柴胡汤": ("东汉", "《伤寒论》", "张仲景"),
    "大柴胡汤": ("东汉", "《伤寒论》", "张仲景"),
    "半夏泻心汤": ("东汉", "《伤寒论》", "张仲景"),
    "生姜泻心汤": ("东汉", "《伤寒论》", "张仲景"),
    "甘草泻心汤": ("东汉", "《伤寒论》", "张仲景"),
    "葛根汤": ("东汉", "《伤寒论》", "张仲景"),
    "葛根黄芩黄连汤": ("东汉", "《伤寒论》", "张仲景"),
    "白虎汤": ("东汉", "《伤寒论》", "张仲景"),
    "白虎加人参汤": ("东汉", "《伤寒论》", "张仲景"),
    "白虎加桂枝汤": ("东汉", "《金匮要略》", "张仲景"),
    "竹叶石膏汤": ("东汉", "《伤寒论》", "张仲景"),
    "调胃承气汤": ("东汉", "《伤寒论》", "张仲景"),
    "小承气汤": ("东汉", "《伤寒论》", "张仲景"),
    "大承气汤": ("东汉", "《伤寒论》", "张仲景"),
    "桃核承气汤": ("东汉", "《伤寒论》", "张仲景"),
    "抵当汤": ("东汉", "《伤寒论》", "张仲景"),
    "黄连阿胶汤": ("东汉", "《伤寒论》", "张仲景"),
    "炙甘草汤": ("东汉", "《伤寒论》", "张仲景"),
    "猪苓汤": ("东汉", "《伤寒论》", "张仲景"),
    "附子汤": ("东汉", "《伤寒论》", "张仲景"),
    "甘草汤": ("东汉", "《伤寒论》", "张仲景"),
    "桔梗汤": ("东汉", "《伤寒论》", "张仲景"),
    "瓜蒂散": ("东汉", "《伤寒论》", "张仲景"),
    "白通汤": ("东汉", "《伤寒论》", "张仲景"),
    "通脉四逆汤": ("东汉", "《伤寒论》", "张仲景"),
    "吴茱萸汤": ("东汉", "《伤寒论》", "张仲景"),
    "黄连汤": ("东汉", "《伤寒论》", "张仲景"),
    "干姜黄芩黄连人参汤": ("东汉", "《伤寒论》", "张仲景"),
    "旋覆代赭汤": ("东汉", "《伤寒论》", "张仲景"),
    "厚朴生姜半夏甘草人参汤": ("东汉", "《伤寒论》", "张仲景"),
    "芍药甘草汤": ("东汉", "《伤寒论》", "张仲景"),
    "茯苓四逆汤": ("东汉", "《伤寒论》", "张仲景"),
    "黄芩汤": ("东汉", "《伤寒论》", "张仲景"),
    # 太平惠民和剂局方 (宋)
    "四君子汤": ("宋", "《太平惠民和剂局方》", ""),
    "四物汤": ("宋", "《太平惠民和剂局方》", ""),
    "参苓白术散": ("宋", "《太平惠民和剂局方》", ""),
    "藿香正气散": ("宋", "《太平惠民和剂局方》", ""),
    "逍遥散": ("宋", "《太平惠民和剂局方》", ""),
    "八正散": ("宋", "《太平惠民和剂局方》", ""),
    "凉膈散": ("宋", "《太平惠民和剂局方》", ""),
    "川芎茶调散": ("宋", "《太平惠民和剂局方》", ""),
    "人参养荣汤": ("宋", "《太平惠民和剂局方》", ""),
    "十全大补汤": ("宋", "《太平惠民和剂局方》", ""),
    "人参败毒散": ("宋", "《太平惠民和剂局方》", ""),
    "五积散": ("宋", "《太平惠民和剂局方》", ""),
    "苏合香丸": ("宋", "《太平惠民和剂局方》", ""),
    "至宝丹": ("宋", "《太平惠民和剂局方》", ""),
    "苏子降气汤": ("宋", "《太平惠民和剂局方》", ""),
    "黑锡丹": ("宋", "《太平惠民和剂局方》", ""),
    # 金匮要略 (张仲景) 补充
    "肾气丸": ("东汉", "《金匮要略》", "张仲景"),
    "薯蓣丸": ("东汉", "《金匮要略》", "张仲景"),
    "酸枣仁汤": ("东汉", "《金匮要略》", "张仲景"),
    "百合地黄汤": ("东汉", "《金匮要略》", "张仲景"),
    "甘麦大枣汤": ("东汉", "《金匮要略》", "张仲景"),
    "泻心汤": ("东汉", "《金匮要略》", "张仲景"),
    "黄土汤": ("东汉", "《金匮要略》", "张仲景"),
    "温经汤": ("东汉", "《金匮要略》", "张仲景"),
    "桂枝茯苓丸": ("东汉", "《金匮要略》", "张仲景"),
    "薏苡附子败酱散": ("东汉", "《金匮要略》", "张仲景"),
    "乌梅丸": ("东汉", "《伤寒论》", "张仲景"),
    "柏叶汤": ("东汉", "《金匮要略》", "张仲景"),
    # 千金方 (唐·孙思邈)
    "温胆汤": ("唐", "《千金要方》", "孙思邈"),
    "独活寄生汤": ("唐", "《千金要方》", "孙思邈"),
    "苇茎汤": ("唐", "《千金要方》", "孙思邈"),
    "紫雪丹": ("唐", "《千金要方》", "孙思邈"),
    # 景岳全书 (明·张介宾)
    "金水六君煎": ("明", "《景岳全书》", "张介宾"),
    "左归丸": ("明", "《景岳全书》", "张介宾"),
    "右归丸": ("明", "《景岳全书》", "张介宾"),
    "理阴煎": ("明", "《景岳全书》", "张介宾"),
    "暖肝煎": ("明", "《景岳全书》", "张介宾"),
    "济川煎": ("明", "《景岳全书》", "张介宾"),
    "玉女煎": ("明", "《景岳全书》", "张介宾"),
    # 医宗金鉴 (清·吴谦)
    "五味消毒饮": ("清", "《医宗金鉴》", "吴谦"),
    # 丹溪心法 (元·朱震亨)
    "虎潜丸": ("元", "《丹溪心法》", "朱震亨"),
    # 三因方 (宋·陈言)
    "三仁汤": ("清", "《温病条辨》", "吴瑭"),
    # 伤寒论变方
    "半夏厚朴汤": ("东汉", "《金匮要略》", "张仲景"),
    "苏子降气汤": ("宋", "《太平惠民和剂局方》", ""),
}

FORMULA_SUFFIXES = ('汤', '散', '丸', '饮', '丹', '膏', '饮子', '煎', '方')
NON_FORMULA_TITLES = {
    '细辛', '麻黄', '附子', '桂枝', '黄芪', '人参', '当归', '川芎',
    '中风', '伤寒', '金匮', '温病', '本草', '伤风', '伤湿',
}


def _connect() -> sqlite3.Connection:
    if not _DB_PATH.exists():
        raise FileNotFoundError(f"zysj.db 不存在: {_DB_PATH}")
    return sqlite3.connect(_DB_PATH)


def _is_formula_title(title: str) -> bool:
    """标题是否像方剂 (排除纯药物章节/学科章节)"""
    if title in NON_FORMULA_TITLES:
        return False
    # 排除"X. 短中文"型 (如 "1.石膏", "2.卫生防疫宝丹")
    # 规则: 以"数字."开头 + 后接 1-6 字符 + 不能是方剂 (即不含任何汤/散/丸名)
    if re.match(r'^\d+[\.．、·]\s*\S{1,6}$', title):
        # 如果整段是单味药名 (石膏/细辛/麻黄/附子/桂枝/黄芪等) - 排除
        cleaned = re.sub(r'^\d+[\.．、·]\s*', '', title)
        single_herbs = {'石膏', '细辛', '麻黄', '附子', '桂枝', '黄芪', '人参',
                        '当归', '川芎', '芍药', '甘草', '柴胡', '半夏', '黄连',
                        '大黄', '白术', '茯苓', '栀子', '生姜', '大枣'}
        if cleaned in single_herbs:
            return False
        # 短标题 (≤2 字) 通常不是方剂名 (如 "1.知", "2.地")
        if len(cleaned) <= 2:
            return False
        # 短标题无方剂后缀 → 也排除 (如 "1.知母", "2.防风")
        if not any(cleaned.endswith(s) for s in FORMULA_SUFFIXES):
            return False
    # 排除"X.Y 数字.数字"型 (章节编号, 如 "1.9 肛管", "3.5 脂类")
    if re.search(r'\d+[\.．]\s*\d', title):
        return False
    # 排除含学科/解剖词的章节
    science_words = ('肛管', '胆囊', '胰腺', '脂类', '生理', '病理',
                     '解剖', '营养', '维生素', '矿物质', '蛋白', '脂肪',
                     '碳水', '神经', '组织', '细胞', '胚胎', '婴儿',
                     '儿童', '老年', '妇人', '男子', '心理', '情绪',
                     '卫生防疫')
    if any(w in title for w in science_words):
        return False
    if len(title) < 2 or len(title) > 35:
        return False
    # 标题含"汤/散/丸/饮/丹/膏/煎/方" 等方剂后缀
    return any(title.endswith(s) for s in FORMULA_SUFFIXES)


def _clean_title(title: str) -> str:
    """清理标题: 去除前缀编号/章节标记, 提取方名"""
    cleaned = re.sub(r'^[一二三四五六七八九十百\d]+[\.．、]\s*', '', title)
    cleaned = re.sub(r'^[\[【〔]\s*附\s*[\]】〕]\s*', '', cleaned)
    return cleaned

def _extract_source_from_title(title: str) -> tuple[str, str, str]:
    """从方名启发式推断出处/作者/朝代.

    优先查 PURE_NAME_MAP (修复: 纯名方"理中汤"等)
    否则查 TITLE_HEURISTIC 关键词
    """
    if title in PURE_NAME_MAP:
        return PURE_NAME_MAP[title]
    for keyword, info in TITLE_HEURISTIC:
        if keyword in title:
            return info
    return ("待考", "未识别", "")


def _extract_indication(content: str) -> str:
    """从 NeiRong 提取 '治X' / '主治X' / '此方主之X' 句"""
    if not content:
        return "(无内容)"
    patterns = [
        # "此方主之X" (千金/外台常见, X 内可有顿号/逗号, 但终于是句号/分号)
        re.compile(r"此方主之\s*([^。；]{2,80}?)(?:[。，；,]|$)", re.DOTALL),
        # "治X方" / "治X病" / "治X者" (X 内可有顿号/逗号)
        re.compile(r"治([^。；]{2,80}?)(?:方|病|者)?(?:[。，；,]|$)", re.DOTALL),
        # "主治X"
        re.compile(r"主治([^。；]{2,80}?)(?:[。，；,]|$)", re.DOTALL),
        # "《X》云∶Y" 引用类
        re.compile(r"《[^》]+》\s*云[∶:]?\s*([^。；]{2,80}?)(?:[。，；,]|$)", re.DOTALL),
    ]
    for pat in patterns:
        m = pat.search(content)
        if m:
            text = m.group(1).strip()
            if len(text) >= 2 and not text.startswith(('之', '也', '者', '当', '宜')):
                return text[:80]
    return "(未提取)"


def fetch_formulas_with_herb(herb: str, top: int = 20) -> list[dict]:
    """从 zysjllsj 找含某药且标题像方剂的章节, 启发式提取元数据.

    排序策略 (修复 bug: 让经典方不被"1./2./3."数字开头方剂挤掉):
      1. 含《XX》书名标记的方剂  (如 《伤寒论》理中汤, 《千金》补肾丸)
      2. 纯名方 (不含数字编号/书名标记) (如 理中汤, 麻黄汤)
      3. 其他 (如 1.益肺消积汤, 〔附〕九味羌活汤)
    """
    con = _connect()
    cur = con.execute(
        """
        SELECT ID, BiaoTi, NeiRong FROM zysjllsj
        WHERE NeiRong LIKE ?
          AND (BiaoTi LIKE '%汤%' OR BiaoTi LIKE '%散%' OR BiaoTi LIKE '%丸%'
               OR BiaoTi LIKE '%饮%' OR BiaoTi LIKE '%丹%' OR BiaoTi LIKE '%膏%'
               OR BiaoTi LIKE '%方%')
        LIMIT 5000
        """,
        (f"%{herb}%",),
    )
    results = []
    seen = set()
    for id_, title, content in cur:
        if not (title and content):
            continue
        if not _is_formula_title(title):
            continue
        if title in seen:
            continue
        if herb not in content:
            continue
        dynasty, book, author = _extract_source_from_title(title)
        indication = _extract_indication(content)
        # 优先级 (修复: 经典方在含《XX》次要方前):
        #   -1 = 经典方 (PURE_NAME_MAP 命中) - 理中汤/真武汤/苓桂术甘汤等
        #    0 = 含重要书名 (《伤寒论》/《金匮》/《千金》/《外台》/《局方》/《医宗金鉴》/《医略》/《删繁方》)
        #    1 = 含次要书名 (《集验》/《经效》/《必效》/《广济》/《延年》/《肘后》/《良方》)
        #    2 = 数字编号/带标记方 (1.XXX, 一、XXX, 〔附〕XXX)
        #    3 = 其它纯名方 (数据库里大量无名方, 如 丁字号方)
        # 数字/中文编号前缀检测: "1." "1、" "18、" "18." "一、" "二、" "十、" "一七·" "一○○·" 等
        # 注: "○" 是 U+25CB (零的圈形)
        has_numeric_prefix = bool(
            re.match(r'^\d+[\.．、·]', title)            # 数字 + 句点/顿号/中点
            or re.match(r'^[一二三四五六七八九十百○]+[\.．、·]', title)  # 中文数字 + ○ + 句点/顿号/中点
        )
        has_bracket_prefix = bool(re.match(r'^[\[【〔]', title))
        has_exclude_word = '卫生防疫' in title
        # 经典方优先 (priority -1)
        if title in PURE_NAME_MAP:
            priority = -1
        elif has_numeric_prefix or has_bracket_prefix or has_exclude_word:
            # 数字编号方/带标记方
            priority = 2
        elif re.search(r'《(?P<book>[^》]+)》', title):
            book = re.search(r'《(?P<book>[^》]+)》', title).group('book')
            # 重要古方书
            important_books = {'伤寒论', '金匮', '金匮要略', '千金', '千金要方', '外台',
                               '外台秘要', '局方', '太平惠民和剂局方', '圣济总录', '圣惠',
                               '太平圣惠方', '医宗', '医宗金鉴', '删繁方', '医略'}
            if book in important_books:
                priority = 0
            else:
                # 次要方书
                priority = 1
        else:
            # 其它纯名方
            priority = 3
        results.append({
            "title": title,
            "dynasty": dynasty,
            "book": book,
            "author": author or "—",
            "indication": indication,
            "id": id_,
            "_priority": priority,
        })
        seen.add(title)
    # 按优先级 + MingCheng 排序 (优先级 0 排前, 同优先级按 MingCheng)
    results.sort(key=lambda r: (r["_priority"], r["title"]))
    # 删除内部字段
    for r in results:
        r.pop("_priority", None)
    con.close()
    return results[:top]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="含某药方剂的元数据表格 (出处/作者/朝代/主治)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 细辛 --top 15
  %(prog)s 麻黄 --top 20
  %(prog)s 附子
        """,
    )
    parser.add_argument("herb", help="药名 (如 细辛/麻黄/附子/桂枝)")
    parser.add_argument("--top", type=int, default=20, help="显示方剂数量 (默认 20)")
    args = parser.parse_args()

    print(f"\n正在搜索含「{args.herb}」的方剂元数据...")
    results = fetch_formulas_with_herb(args.herb, top=args.top)
    print(f"找到 {len(results)} 条方剂元数据\n")

    if not results:
        print(f"未找到含「{args.herb}」的方剂。")
        return

    # Markdown 表格
    print("| # | 方名 | 朝代 | 出处 | 作者 | 主治 |")
    print("|---|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        print(f"| {i} | {r['title']} | {r['dynasty']} | {r['book']} | {r['author']} | {r['indication']} |")

    print()
    print("注:")
    print("- 出处/作者/朝代 按方剂名启发式推断 (基于常见中医典籍命名规律)")
    print("- 主治字段从 zysjllsj 章节正文提取 '治X' 句 (章节片段存储, 可能不完整)")


if __name__ == "__main__":
    main()
