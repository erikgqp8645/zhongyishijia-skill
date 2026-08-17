#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_prescription.py — 验证"读唐宋古方方法论"

支持自然语言查询 + 关键词模式:
  python scripts/verify_prescription.py "治疗皮肤瘙痒的核心药有哪些"
  python scripts/verify_prescription.py "为什么续命汤用麻黄"
  python scripts/verify_prescription.py "麻黄的本草功效"
  python scripts/verify_prescription.py "破癥坚积聚的方剂"
  python scripts/verify_prescription.py "中风的高频药" --top 6
  python scripts/verify_prescription.py 皮肤瘙痒  --keywords 痒 瘾疹  (传统模式)

方法论 4 步:
  1. 同病证 → 多方归纳
  2. 提取高频核心药
  3. 检索本经/别录原文 (zysjllsj:72xxx 本草原始文献汇编)
  4. 输出"病证-核心药-本草原文"对照表
"""

from __future__ import annotations

import argparse
import io
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# 共享 SQLite 路径查找 (三级查找 + 环境变量 + --sqlite 参数)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sqlite_utils import find_sqlite_path  # noqa: E402

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

# ── 配置 ──────────────────────────────────────────
# SQLite 路径由 _connect(sqlite_arg) 动态解析 (三级查找 + --sqlite 参数 + ZHONGYISHIJIA_SQLITE 环境变量)
# 保留 _SKILL_ROOT 以备其他用途 (如定位 references/ 子目录)
_SKILL_ROOT = Path(__file__).resolve().parent.parent

# CLI 指定的 SQLite 路径 (main() 中赋值, _connect() 读取)
_SQLITE_ARG: str | None = None

# 中药字典 (长药名优先, 避免短串误匹配)
HERBS = sorted(
    [
        "麻黄", "桂心", "桂枝", "肉桂", "附子", "羌活", "独活", "防风", "细辛",
        "人参", "黄芩", "芍药", "川芎", "当归", "白术", "茯苓", "甘草", "杏仁",
        "生地黄", "熟地黄", "干地黄", "竹沥", "生姜", "大枣", "石膏", "羚羊角",
        "天麻", "枳壳", "枳实", "蔓荆实", "蒺藜子", "荆芥穗", "苦参", "益母草",
        "乌蛇", "白花蛇", "威灵仙", "防己", "黄芪", "白芷", "菊花", "漏芦",
        "大黄", "柴胡", "半夏", "陈皮", "丹皮", "牡丹皮", "桃仁", "红花",
        "黄连", "黄柏", "栀子", "泽泻", "车前子", "滑石", "木通", "通草", "麦冬",
        "五味子", "旋覆花", "代赭石", "地黄", "薄荷", "蝉蜕", "钩藤", "蒺藜",
        "秦艽", "桑寄生", "牛膝", "杜仲", "续断", "狗脊", "萆薜", "枸杞子",
        "菟丝子", "决明子", "青葙子", "密蒙花", "石决明", "山药", "山茱萸",
        "石菖蒲", "远志", "蛇床子",
    ],
    key=lambda x: -len(x),
)

# 病证关键词 → 扩展搜索词
DISEASE_KEYWORD_MAP: dict[str, list[str]] = {
    # 皮肤瘙痒
    "皮肤瘙痒": ["痒", "瘾疹", "风瘙痒", "瘙痒"],
    "痒": ["痒", "瘾疹", "风瘙痒", "瘙痒"],
    "瘾疹": ["痒", "瘾疹", "风瘙痒", "瘙痒"],
    # 中风
    "中风": ["中风", "续命", "偏枯"],
    "续命": ["续命", "中风"],
    "偏枯": ["偏枯", "中风"],
    # 目系
    "目系": ["青盲", "目盲", "目翳", "明目", "目暗", "雀目", "目疾"],
    "目盲": ["目盲", "青盲", "明目"],
    "青盲": ["青盲", "目盲"],
    "目翳": ["目翳", "明目", "翳膜"],
    "明目": ["明目", "目疾"],
    # 其他常见病证 (按需扩展)
    "伤寒": ["伤寒", "太阳", "阳明", "少阳", "太阴", "少阴", "厥阴"],
    "疟疾": ["疟"],
    "水肿": ["水肿", "风水", "皮水"],
    "消渴": ["消渴"],
    "心悸": ["心悸", "怔忡", "惊悸"],
    "痹证": ["痹", "历节", "痛痹", "着痹", "行痹"],
    "历节": ["历节", "痹"],
    "咳嗽": ["咳", "喘", "咳嗽"],
    "虚劳": ["虚劳", "五劳", "七伤"],
    "黄疸": ["黄疸", "黄胆", "黄"],
    "痢疾": ["痢", "下利", "滞下"],
    "带下": ["带下"],
    "不孕": ["不孕", "绝子", "无子"],
    "遗精": ["遗精", "失精", "精"],
    "头痛": ["头痛", "头风", "首风"],
    "眩晕": ["眩晕", "眩", "冒"],
    # 经典方剂 (查方剂高频药)
    "桂枝汤": ["桂枝汤", "桂枝"],
    "小青龙汤": ["小青龙汤", "青龙"],
    "续命汤": ["续命汤", "续命"],
    "四逆汤": ["四逆汤", "四逆"],
}

# 病证别名归一
_DISEASE_ALIAS: dict[str, str] = {
    "皮肤瘙痒": "皮肤瘙痒",
    "瘙痒": "皮肤瘙痒",
    "中风": "中风",
    "续命": "中风",
    "偏枯": "中风",
    "目系": "目系",
    "目盲": "目系",
    "青盲": "目系",
    "目翳": "目系",
    "明目": "目系",
    "伤寒": "伤寒",
    "疟": "疟疾",
    "疟疾": "疟疾",
    "水肿": "水肿",
    "消渴": "消渴",
    "心悸": "心悸",
    "怔忡": "心悸",
    "痹": "痹证",
    "痹证": "痹证",
    "历节": "痹证",
    "咳": "咳嗽",
    "喘": "咳嗽",
    "咳嗽": "咳嗽",
    "虚劳": "虚劳",
    "黄疸": "黄疸",
    "黄胆": "黄疸",
    "黄": "黄疸",
    "痢": "痢疾",
    "下利": "痢疾",
    "带下": "带下",
    "不孕": "不孕",
    "绝子": "不孕",
    "遗精": "遗精",
    "失精": "遗精",
    "头痛": "头痛",
    "头风": "头痛",
    "眩": "眩晕",
    "眩晕": "眩晕",
    "冒": "眩晕",
}

# 自然语言意图识别
_INTENT_RE = {
    # "为什么X用Y" → 查 Y 的本草原文 (查药)
    "why": re.compile(r"为什么\s*(?:[\u4e00-\u9fa5]+?)\s*(?:用|选|要)\s*([\u4e00-\u9fa5]+)"),
    # "X的本草功效" / "X的本草" / "X的功效" → 查药
    "herb_bencao": re.compile(r"([\u4e00-\u9fa5]+?)\s*的\s*(?:本草|药性|本草功效|原始功效|本草记载)"),
    # "X的功效" → 查药
    "herb_xiang": re.compile(r"([\u4e00-\u9fa5]+?)\s*的\s*功效"),
    # "高频药" / "核心药" → 病证模式
    "core_herbs": re.compile(r"(?:高频|核心|主要|常用)\s*(?:药|药物)"),
    # "治疗X的方剂" / "X的方" → 病证模式
    "disease_formula": re.compile(r"(?:治疗|主治|治)\s*(.+?)\s*(?:的|有哪些|有什么)?\s*(?:方|方剂)"),
    # "破X积聚" / "X积聚" 的方剂 → 主治反查
    "indications": re.compile(r"([\u4e00-\u9fa5]+(?:积聚|癥瘕|症瘕))"),
    # "含X的方剂" / "有X的方" / "用X的方" → 方剂反查 (查 Chufang 含某药)
    "formula_reverse": re.compile(r"(?:含|有|用)\s*([\u4e00-\u9fa5]+?)\s*(?:的)?\s*(?:方|方剂|药方|处方)"),
}

# 本草原文引用格式
# 主治条文必须是 "《X》云∶主Y..." 格式 (主 + 病证/功效)
# 排除: 异名 (名X), 采收 (二月采), 性味 (味X), 注释 (云X, 无主字)
# 贪婪匹配: 一直取到下一个《X》引用标记 (本草/药性论/衍义/液 等), 完整保留 2-3 句
_BENCAO_PATTERNS = [
    re.compile(r"《本草》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL),
    re.compile(r"《本草经》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL),
    re.compile(r"《本经》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL),
    re.compile(r"《别录》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL),
    re.compile(r"《唐本》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL),
    re.compile(r"《蜀本》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL),
    re.compile(r"《药性论》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL),
]
_HEADLESS_MAIN = re.compile(
    r"(?:^|\n)\s*(?:味[^\n]{1,30})?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)",
    re.DOTALL,
)
_SOURCE_PRIORITY = ["本经", "本草", "别录", "唐本", "蜀本", "药性论"]


# ── 自然语言解析 ──────────────────────────────────
def parse_query(text: str) -> dict:
    """解析自然语言 → (intent, disease, herb, top_n, raw_keywords)

    intent ∈ {disease_verify, herb_bencao, indications, fallback}
    """
    text_clean = text.strip()
    result = {
        "intent": "disease_verify",
        "disease": None,
        "herb": None,
        "raw_query": text_clean,
    }

    # 1) "为什么X用Y" → herb_bencao
    m = _INTENT_RE["why"].search(text_clean)
    if m:
        result["intent"] = "herb_bencao"
        result["herb"] = m.group(1)
        return result

    # 2) "X的本草/功效" → herb_bencao
    m = _INTENT_RE["herb_bencao"].search(text_clean)
    if m:
        herb = m.group(1)
        # 排除"为什么"等假阳性
        if herb not in ("为什么", "什么", "如何", "怎么"):
            result["intent"] = "herb_bencao"
            result["herb"] = herb
            return result

    # 3) "含X的药方/方剂" → formula_reverse
    m = _INTENT_RE["formula_reverse"].search(text_clean)
    if m:
        herb = m.group(1)
        # 排除明显是病证/方剂的匹配
        if herb not in ("什么", "哪些", "什么方"):
            result["intent"] = "formula_reverse"
            result["herb"] = herb
            return result

    # 4) "破X积聚" 的方剂 → indications
    m = _INTENT_RE["indications"].search(text_clean)
    if m and ("方" in text_clean or "积聚" in text_clean):
        result["intent"] = "indications"
        result["herb"] = m.group(1)  # 复用 herb 字段存"破X积聚"短语
        return result

    # 4) 默认: 病证验证模式
    # 去掉尾部的"的核心药/高频药/方剂/有哪些药"等后缀
    text_stripped = re.sub(
        r"(?:的核心药|的高频药|的常用药|的方剂|有哪些药|有哪味药|的中药|的药物"
        r"|的核心|的高频|的常用|的方|有哪些|有哪|有什|方剂|\?|？)+$",
        "",
        text_clean,
    ).strip()
    m = re.search(r"(?:治疗|治|主|用于|关于|论)\s*(.+)", text_stripped)
    if m:
        disease = m.group(1).strip()
    else:
        disease = text_stripped

    # 别名归一
    disease = _DISEASE_ALIAS.get(disease, disease)
    result["disease"] = disease
    result["intent"] = "disease_verify"
    return result


# ── 工具函数 ──────────────────────────────────────
def _connect(sqlite_arg: str | None = None) -> sqlite3.Connection:
    """按优先级查找 SQLite 路径: --sqlite 参数 → ZHONGYISHIJIA_SQLITE → 三级查找"""
    db_path = find_sqlite_path(sqlite_arg or _SQLITE_ARG)
    # GBK 编码 (MSSQL 还原特征)
    conn = sqlite3.connect(str(db_path))
    conn.text_factory = lambda b: b.decode("gbk", errors="replace")
    return conn


def _extract_herbs(text: str) -> list[str]:
    found, seen = [], set()
    for h in HERBS:
        if h in text and h not in seen:
            found.append(h)
            seen.add(h)
    return found


def _fetch_prescriptions(keywords: list[str], limit: int = 300) -> list[tuple[str, str]]:
    where = " OR ".join(["ChuFang LIKE ? OR MingCheng LIKE ?"] * len(keywords))
    params: list = []
    for kw in keywords:
        params.extend([f"%{kw}%", f"%{kw}%"])
    params.append(limit)
    con = _connect()
    cur = con.execute(
        f"SELECT MingCheng, ChuFang FROM zysjyj WHERE {where} LIMIT ?",
        params,
    )
    seen, result = set(), []
    for n, c in cur:
        if n and c and n not in seen:
            result.append((n, c))
            seen.add(n)
    con.close()
    return result


def _fetch_bencao(herb: str) -> list[dict]:
    con = _connect()
    cur = con.execute(
        """
        SELECT ID, BiaoTi, NeiRong FROM zysjllsj
        WHERE BiaoTi = ?
          AND (NeiRong LIKE '%本草%' OR NeiRong LIKE '%别录%' OR NeiRong LIKE '%本经%')
        ORDER BY ID
        LIMIT 20
        """,
        (herb,),
    )
    candidates = []
    for id_, title, content in cur:
        if not content:
            continue
        quotes: list[dict] = []
        for pat in _BENCAO_PATTERNS:
            m = pat.search(content)
            if m:
                src = pat.pattern.split("》")[0].lstrip("《")
                text = m.group(1).strip()
                # 截到下一个《X》引用标记 (本经常多句连用: "...。止X。破Y。")
                next_ref = re.search(r"《[一-鿿]{1,5}》", text)
                if next_ref:
                    text = text[: next_ref.start()].rstrip("。；,， ")
                # 同时也截到第二个句号 (本经主治通常 2-3 句, 完整保留)
                periods = list(re.finditer(r"[。；]", text))
                if len(periods) >= 2:
                    text = text[: periods[1].start()]
                # 兜底: 单句截断
                if "。" in text and not text.endswith("。"):
                    first = re.search(r"[。；]", text)
                    if first and first.start() < 50:  # 第一个句号太早说明还有
                        pass
                quotes.append({"src": src, "text": text})
        if not quotes:
            m2 = _HEADLESS_MAIN.search(content)
            if m2:
                text = m2.group(1).strip()
                if 70000 <= id_ < 80000:
                    src = "本草经集注"
                elif 1 <= id_ < 10000:
                    src = "本草(现代)"
                else:
                    src = "本草(原文)"
                # headless 模式截到第二个句号
                periods = list(re.finditer(r"[。；]", text))
                if len(periods) >= 2:
                    text = text[: periods[1].start()]
                quotes.append({"src": src, "text": text})
        if quotes:
            candidates.append({"id": id_, "title": title, "quotes": quotes})
    con.close()
    return candidates


# ── 意图执行器 ──────────────────────────────────
def run_disease_verify(
    disease: str,
    keywords: list[str] | None,
    top: int,
    show_bencao: bool,
    max_pres_list: int,
) -> dict:
    print(f"\n{'='*78}")
    print(f"# 病证: {disease}")
    print(f"# 搜索关键词: {keywords or [disease]}")
    print(f"{'='*78}\n")

    if not keywords:
        # 查别名表
        keywords = DISEASE_KEYWORD_MAP.get(disease, [disease])

    records = _fetch_prescriptions(keywords)
    n = len(records)
    print(f"【步骤 1 · 多方归纳】共 {n} 首方剂")
    if records:
        for name, _ in records[:max_pres_list]:
            print(f"  · {name}")
        if n > max_pres_list:
            print(f"  · ... (还有 {n - max_pres_list} 首)")

    herb_counter: Counter = Counter()
    for _, chufang in records:
        for h in set(_extract_herbs(chufang)):
            herb_counter[h] += 1

    print(f"\n【步骤 2 · 高频核心药】 Top {top}:")
    if not herb_counter:
        print("  (无命中)")
    else:
        for h, cnt in herb_counter.most_common(top):
            pct = cnt / n * 100 if n else 0
            bar = "█" * int(pct / 5)
            print(f"  {h:6s}  {cnt:>3}/{n}  ({pct:>3.0f}%)  {bar}")

    if show_bencao:
        print(f"\n【步骤 3 · 本草原文】 (来源: zysjllsj:72xxx 本草原始文献汇编)")
        if not herb_counter:
            print("  (无核心药可查)")
        else:
            for h, _ in herb_counter.most_common(top):
                bc_list = _fetch_bencao(h)
                if not bc_list:
                    print(f"\n  【{h}】  数据库未收录本草原始章节")
                    continue
                seen: set = set()
                merged: list[dict] = []
                for c in bc_list:
                    for q in c["quotes"]:
                        key = (q["src"], q["text"][:50])
                        if key not in seen:
                            seen.add(key)
                            merged.append(q)
                merged.sort(key=lambda q: _SOURCE_PRIORITY.index(q["src"]) if q["src"] in _SOURCE_PRIORITY else 99)
                first = bc_list[0]
                print(
                    f"\n  【{h}】 zysjllsj:{first['id']} 《{first['title']}》"
                    + (f" (+{len(bc_list)-1} 个章节)" if len(bc_list) > 1 else "")
                )
                for q in merged[:3]:
                    txt = q["text"][:200]
                    print(f"    《{q['src']}》: {txt}{'…' if len(q['text']) > 200 else ''}")

    print(f"\n{'─'*78}")
    print(f"# 总结")
    print(f"{'─'*78}")
    print(f"病证「{disease}」在 zysj.com.cn 知识库命中 {n} 首方剂, "
          f"归纳出 {len(herb_counter)} 味核心药。")
    if herb_counter:
        top1 = herb_counter.most_common(1)[0]
        print(f"最高频核心药: {top1[0]} (覆盖 {top1[1]}/{n} = {top1[1]/n*100:.0f}%)")
    print()
    return {
        "disease": disease,
        "keywords": keywords,
        "n_prescriptions": n,
        "core_herbs": dict(herb_counter.most_common(top)),
    }


def run_herb_bencao(herb: str, top: int = 3) -> dict:
    print(f"\n{'='*78}")
    print(f"# 药名: {herb}  (本草原文检索)")
    print(f"{'='*78}\n")

    bc_list = _fetch_bencao(herb)
    if not bc_list:
        print(f"数据库未收录「{herb}」的本草原始章节。")
        print(f"可能原因: 该药不入本草主流体系 (如地区性草药), 或本数据库未涵盖。\n")
        return {"herb": herb, "n_chapters": 0}

    print(f"【本草原文】共 {len(bc_list)} 个章节 (zysjllsj:72xxx 系列):\n")
    for i, c in enumerate(bc_list[:top], 1):
        print(f"  章节 {i}: zysjllsj:{c['id']} 《{c['title']}》")
        for q in c["quotes"][:3]:
            txt = q["text"][:300]
            print(f"    《{q['src']}》: {txt}{'…' if len(q['text']) > 300 else ''}")
        print()

    # 总结
    all_quotes = []
    for c in bc_list:
        for q in c["quotes"]:
            all_quotes.append(q)
    unique_srcs = set(q["src"] for q in all_quotes)
    print(f"{'─'*78}")
    print(f"# 总结")
    print(f"{'─'*78}")
    print(f"「{herb}」本草原始文献共 {len(bc_list)} 个章节, "
          f"含 {len(all_quotes)} 条引文, 来自来源: {', '.join(sorted(unique_srcs))}\n")
    return {"herb": herb, "n_chapters": len(bc_list), "n_quotes": len(all_quotes)}


def run_indications(query: str, top: int = 10) -> dict:
    """主治反查: 找本草主治含该短语的药物"""
    print(f"\n{'='*78}")
    print(f"# 主治反查: {query}")
    print(f"{'='*78}\n")

    # 第一步: 查方剂 Chufang 字段
    con = _connect()
    cur = con.execute(
        "SELECT MingCheng, ChuFang FROM zysjyj WHERE ChuFang LIKE ? LIMIT ?",
        (f"%{query}%", top * 3),
    )
    matches = []
    for name, chufang in cur:
        if name and chufang:
            matches.append((name, chufang))

    if matches:
        print(f"【方剂含「{query}」】共 {len(matches)} 首 (展示前 {top}):\n")
        for name, chufang in matches[:top]:
            snippet = chufang.replace("\r", "").replace("\n", " ")
            idx = snippet.find(query)
            if idx >= 0:
                start = max(0, idx - 40)
                end = min(len(snippet), idx + 60)
                snippet = ("…" if start > 0 else "") + snippet[start:end] + ("…" if end < len(snippet) else "")
            else:
                snippet = snippet[:120] + "…"
            print(f"  · {name}")
            print(f"    {snippet}")
            print()
    else:
        print(f"【方剂 Chufang 字段无「{query}」原文】")
        print(f"  (本草主治原文不在方剂字段, 改查本草章节)\n")

    # 第二步: 查本草章节 (这条才是"破癥坚积聚"原文所在)
    cur2 = con.execute(
        """
        SELECT ID, BiaoTi, NeiRong FROM zysjllsj
        WHERE NeiRong LIKE ? OR NeiRong LIKE ?
        LIMIT 30
        """,
        (f"%{query}%", f"%{query.replace('癥', '症')}%"),
    )
    bencao_matches = []
    for id_, title, content in cur2:
        if not content: continue
        # 只保留 BiaoTi 是药名 (≤4 字) 的章节
        if title and len(title) <= 4:
            # 找含 query 的句子
            idx = content.find(query)
            if idx < 0: idx = content.find(query.replace('癥', '症'))
            if idx >= 0:
                start = max(0, idx - 30)
                end = min(len(content), idx + 80)
                snippet = content[start:end].replace('\r','').replace('\n',' ')
                bencao_matches.append((id_, title, snippet))

    if bencao_matches:
        print(f"【本草主治含「{query}」的药物】共 {len(bencao_matches)} 条 (展示前 {top}):\n")
        seen_h = set()
        shown = 0
        for id_, title, snippet in bencao_matches:
            if title in seen_h: continue
            seen_h.add(title)
            print(f"  · {title} (zysjllsj:{id_})")
            print(f"    …{snippet}…")
            print()
            shown += 1
            if shown >= top: break

    con.close()
    return {"query": query, "n_formula": len(matches), "n_bencao": len(bencao_matches)}


def run_formula_reverse(herb: str, top: int = 15) -> dict:
    """方剂反查: 找方名或处方含某药的所有方剂 (方名命中优先, 排除纯药名/同名重复条目)"""
    print(f"\n{'='*78}")
    print(f"# 方剂反查: 含「{herb}」")
    print(f"{'='*78}\n")

    con = _connect()
    # 第一步: 方名含某药 (排除纯药名章节, 按 MingCheng 去重, 经典方优先)
    # 注: 不用 SQL 的 ORDER BY, 而是 Python 端取全部后按 name_priority 排序
    cur = con.execute(
        "SELECT DISTINCT MingCheng, ChuFang FROM zysjyj "
        "WHERE MingCheng LIKE ? AND MingCheng != ?",
        (f"%{herb}%", herb),
    )
    name_matches = []
    seen = set()
    for name, chufang in cur:
        if name and chufang and name not in seen:
            name_matches.append((name, chufang))
            seen.add(name)

    # 排序: 简短名优先 (汤/散/丸/饮/丹/膏 等单字后缀) — 经典方剂命名规律
    def name_priority(name: str) -> int:
        suffixes = ('汤', '散', '丸', '饮', '丹', '膏')
        # 经典名方分高 (短 + 常见后缀)
        if len(name) <= 4 and name.endswith(suffixes):
            return 0  # 最高
        if len(name) <= 6 and name.endswith(suffixes):
            return 1
        if name.startswith(('加味', '加减', '加')):
            return 2
        return 3
    name_matches.sort(key=lambda x: (name_priority(x[0]), x[0]))

    print(f"【方名含「{herb}」的方剂】共 {len(name_matches)}+ 首 (展示前 {min(top, len(name_matches))}):\n")
    for name, chufang in name_matches[:top]:
        snippet = chufang.replace("\r", "").replace("\n", " ")
        idx = snippet.find(herb)
        if idx >= 0:
            start = max(0, idx - 30)
            end = min(len(snippet), idx + 80)
            snippet = ("…" if start > 0 else "") + snippet[start:end] + ("…" if end < len(snippet) else "")
        else:
            snippet = snippet[:120] + "…"
        print(f"  · {name}")
        print(f"    {snippet}")
        print()

    # 第二步: 处方字段含某药 (补充, 按 MingCheng 排序)
    if len(name_matches) < top:
        remaining = top - len(name_matches)
        cur2 = con.execute(
            "SELECT DISTINCT MingCheng, ChuFang FROM zysjyj "
            "WHERE ChuFang LIKE ? AND MingCheng NOT LIKE ?",
            (f"%{herb}%", f"%{herb}%"),
        )
        extra_matches = []
        for name, chufang in cur2:
            if name and chufang and name not in seen:
                extra_matches.append((name, chufang))
                seen.add(name)
        if extra_matches:
            extra_matches.sort(key=lambda x: (name_priority(x[0]), x[0]))
            print(f"【处方含「{herb}」的其他方剂】共 {len(extra_matches)}+ 首 (补充前 {min(remaining, len(extra_matches))}):\n")
            for name, chufang in extra_matches[:remaining]:
                snippet = chufang.replace("\r", "").replace("\n", " ")
                idx = snippet.find(herb)
                if idx >= 0:
                    start = max(0, idx - 30)
                    end = min(len(snippet), idx + 80)
                    snippet = ("…" if start > 0 else "") + snippet[start:end] + ("…" if end < len(snippet) else "")
                print(f"  · {name}")
                print(f"    {snippet}")
                print()

    # 总结
    print(f"{'─'*78}")
    print(f"# 总结")
    print(f"{'─'*78}")
    print(f"「{herb}」在 zysj.com.cn 数据库 (zysjyj 表) 至少出现于 {len(name_matches)}+ 首方剂。")
    print(f"提示: 用 '细辛的本草' 可查本草原始主治；用 '痹证的核心药' 可查含细辛的病证应用。\n")
    con.close()
    return {"herb": herb, "n_formula": len(name_matches)}


# ── 主入口 ────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="验证读唐宋古方方法论 — 支持自然语言查询 (同病证多方归纳 + 高频核心药 + 本草原文)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
自然语言查询示例:
  %(prog)s "治疗皮肤瘙痒的核心药"
  %(prog)s "中风的高频药"
  %(prog)s "为什么续命汤用麻黄"
  %(prog)s "麻黄的本草功效"
  %(prog)s "含细辛的方剂"        # 方剂反查 (按方名优先)
  %(prog)s "含麻黄的方剂"        # 同上
  %(prog)s "破癥坚积聚的方剂"    # 主治反查 (本草章节)

关键词模式 (传统):
  %(prog)s 皮肤瘙痒 --keywords 痒 瘾疹
  %(prog)s 中风 --top 6
  %(prog)s 续命 --no-bencao
        """,
    )
    parser.add_argument("query", nargs="?", help="自然语言查询或病证名")
    parser.add_argument("--keywords", nargs="+", default=None, help="显式搜索关键词 (覆盖自动推断)")
    parser.add_argument("--top", type=int, default=12, help="显示核心药/方剂数量 (默认 12)")
    parser.add_argument("--no-bencao", action="store_true", help="跳过本草原文检索")
    parser.add_argument("--max-pres-list", type=int, default=5, help="步骤 1 展示方剂名数量 (默认 5)")
    parser.add_argument("--debug", action="store_true", help="显示意图解析细节")
    parser.add_argument(
        "--sqlite",
        default=None,
        help="显式指定 SQLite 数据库路径 (默认走三级查找: ~/.cache/zhongyishijia/ → ~/.local/share/ → <repo>/references/raw/)",
    )
    args = parser.parse_args()

    # 同步到模块级全局, _connect() 通过 _SQLITE_ARG 读取
    global _SQLITE_ARG
    _SQLITE_ARG = args.sqlite

    if not args.query:
        parser.print_help()
        sys.exit(1)

    parsed = parse_query(args.query)
    if args.debug:
        print(f"[debug] 解析结果: {parsed}", file=sys.stderr)

    if args.keywords:
        # 显式 --keywords 覆盖, 强制走病证模式
        disease = parsed.get("disease") or args.query
        run_disease_verify(
            disease=disease,
            keywords=args.keywords,
            top=args.top,
            show_bencao=not args.no_bencao,
            max_pres_list=args.max_pres_list,
        )
    elif parsed["intent"] == "herb_bencao":
        run_herb_bencao(parsed["herb"], top=args.top)
    elif parsed["intent"] == "formula_reverse":
        run_formula_reverse(parsed["herb"], top=args.top)
    elif parsed["intent"] == "indications":
        run_indications(parsed["herb"], top=args.top)
    else:
        # 病证模式
        run_disease_verify(
            disease=parsed["disease"],
            keywords=None,
            top=args.top,
            show_bencao=not args.no_bencao,
            max_pres_list=args.max_pres_list,
        )


if __name__ == "__main__":
    main()
