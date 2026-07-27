#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
桂枝人参汤 — 标准化方剂/条文查询脚本

用法:
  python scripts/formula_query.py <关键词>
  python scripts/formula_query.py 桂枝人参汤
  python scripts/formula_query.py 小柴胡汤

  # 完整报告模式（生成结构化 Markdown 文档）
  python scripts/formula_query.py 甘草泻心汤 --full-report

输出格式:
  - 默认: 按朝代从古至今排序的 Markdown 表格（仅主卡片 = title 包含方剂名）
  - --full-report: 完整结构化 Markdown 文档
    （含出处溯源、历代注解、病机归纳、方剂演变、临床应用、剂量换算、证据索引）

数据驱动: 13 个章节全部从 evidence_cards.jsonl 自动提取，模板见
`templates/formula_report_template.md`
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

from _sqlite_utils import setup_windows_stdout
from _source_map import (
    DYNASTY_ORDER,
    SOURCE_MAP,
    TYPEID_MAP,
    identify_source,
    sort_key,
)

setup_windows_stdout()

# ── 模板路径 ──
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SCRIPT_DIR.parent / "templates" / "formula_report_template.md"

# ── 剂量换算表（东汉1两≈3g，1升≈200ml）──
HAN_TO_MODERN = {
    "两": 3.0,
    "铢": 0.125,    # 1两=24铢
    "升": 200.0,
    "合": 20.0,
    "方寸匕": 2.0,
    "枚": 1.0,
    "个": 1.0,
    "斤": 240.0,
    "分": 0.3,       # 宋以后常用
    "钱": 3.0,
    "克": 1.0,       # 现代单位
}


# ── 工具函数 ──

def clean_summary(text: str, max_len: int = 300) -> str:
    """清理摘要: 去 HTML 标签, 解 HTML 实体, 截取合理长度"""
    text = html.unescape(text)
    text = text.replace("[br]", " ").replace("[b]", "").replace("[/b]", "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def search_cards(keyword: str, cards_path: Path) -> list[dict]:
    """搜索 evidence_cards.jsonl"""
    matches = []
    for line in cards_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = " ".join(
            str(item.get(k) or "") for k in ["card_type", "title", "summary", "source_ref"]
        )
        if keyword in text:
            matches.append(item)
    return matches


def classify_cards(matches: list[dict], keyword: str) -> tuple[list[dict], list[dict]]:
    """将匹配卡片分为主卡片（title 包含关键词）和次卡片（仅正文提及）"""
    primary, secondary = [], []
    for card in matches:
        if keyword in card.get("title", ""):
            primary.append(card)
        else:
            secondary.append(card)
    return primary, secondary


def get_time_span(matches: list[dict]) -> str:
    """推断时间跨度"""
    dynasties = set()
    for card in matches:
        dyn, _, _ = identify_source(card)
        if dyn != "待考":
            dynasties.add(dyn)
    if not dynasties:
        return "待考"
    sorted_dyns = sorted(dynasties, key=lambda d: DYNASTY_ORDER.get(d, 99))
    if len(sorted_dyns) <= 2:
        return "、".join(sorted_dyns)
    return f"{sorted_dyns[0]}—{sorted_dyns[-1]}"


def group_by_dynasty(matches: list[dict]) -> dict[str, list[dict]]:
    """按朝代分组"""
    groups = defaultdict(list)
    for card in matches:
        dyn, book, author = identify_source(card)
        groups[dyn].append(card)
    return dict(groups)


def load_template() -> str:
    """加载报告模板"""
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    return ""


# ── 处方/用法解析 ──

def parse_formula_components(summary: str) -> dict[str, str]:
    """从 summary 中解析 处方/主治/用法/出处/性味/归经/功能主治 字段"""
    parts = {}
    # 多种分隔符: 分号/全角分号
    segments = re.split(r'[；;]', summary)
    for seg in segments:
        m = re.match(r'\s*([\u4e00-\u9fff]+)\s*[::]\s*(.*)', seg)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            parts[key] = value
    return parts


def parse_drug_composition(prescription: str) -> list[tuple[str, str, str]]:
    """解析处方组成: 药物名/剂量/炮制"""
    if not prescription:
        return []
    # 格式: "柴胡（去苗）半斤..." 或 "桂枝12克（去皮）..."
    drugs = re.findall(
        r'([\u4e00-\u9fff]+)(?:（([^）]*)）)?\s*([\d.]+(?:两|铢|升|合|枚|个|斤|分|钱|克|方寸匕|寸匕)?)?',
        prescription
    )
    result = []
    for name, prep, amount in drugs:
        if not name or len(name) > 6:
            continue
        result.append((name, prep or "", amount or ""))
    return result[:15]


# ── 朝代章节生成（远端基础结构） ──

def generate_dynasty_sections(groups: dict[str, list[dict]], max_per_dynasty: int = 15) -> str:
    """生成朝代章节内容"""
    sections = []
    dynasty_names = {
        "东汉": "二、东汉时期",
        "晋": "三、晋代",
        "南北朝": "四、南北朝时期",
        "隋": "四、隋代",
        "唐": "五、唐代",
        "宋": "六、宋代",
        "金": "六、金代",
        "元": "七、元代",
        "明": "八、明代",
        "清": "九、清代",
        "民国": "十、民国时期",
        "现代": "十一、现代",
        "日本江户": "六、日本江户时期",
        "待考": "十二、其他/待考",
    }

    dynasty_order_sorted = sorted(groups.keys(), key=lambda d: DYNASTY_ORDER.get(d, 99))

    for idx, dyn in enumerate(dynasty_order_sorted):
        cards = groups[dyn][:max_per_dynasty]
        if not cards:
            continue

        section_title = dynasty_names.get(dyn, f"（{dyn}）")
        lines = [f"### {section_title}", ""]

        # 按书籍分组
        by_book = defaultdict(list)
        for card in cards:
            _, book, author = identify_source(card)
            by_book[(book, author)].append(card)

        for (book, author), book_cards in by_book.items():
            author_str = f" {author}" if author else ""
            lines.append(f"#### {book}{author_str}")
            lines.append("")

            for card in book_cards[:5]:  # 每本书最多5条
                summary = clean_summary(card.get("summary", ""), max_len=500)
                title = card.get("title", "")
                header = f"**{title}**  " if title else ""
                lines.append(f"> {header}{summary}")
                lines.append("")

        sections.append("\n".join(lines))

    return "\n\n---\n\n".join(sections)


def generate_index_table(groups: dict[str, list[dict]]) -> str:
    """生成证据索引表"""
    rows = []
    dynasty_order_sorted = sorted(groups.keys(), key=lambda d: DYNASTY_ORDER.get(d, 99))

    for dyn in dynasty_order_sorted:
        for card in groups[dyn]:
            _, book, author = identify_source(card)
            card_id = card.get("card_id", "")
            rows.append(f"| {dyn} | {book} | {author} | {card_id} |")

    return "\n".join(rows) if rows else "| | | | |"


# ── 1. 出处溯源 ──

def generate_classic_origins(primary_cards: list[dict]) -> str:
    """生成「经典原文」章节（仅 title 匹配的主卡片，过滤朝代标注错误的）"""
    if not primary_cards:
        return "> 暂无经典原文数据。\n"

    sorted_cards = sorted(primary_cards, key=sort_key)
    lines = []
    seen = set()
    for card in sorted_cards[:8]:  # 取最早的 8 条
        dyn, book, author = identify_source(card)
        source_ref = card.get("source_ref", "")
        chunk_id = card.get("chunk_id", "")
        title = card.get("title", "")
        wrong_keywords = ["重订", "补订", "新编", "校注", "白话", "通俗"]

        # 过滤朝代错误标注的卡片
        if dyn == "东汉":
            check_texts = [source_ref, book]
            if any(ws in " ".join(check_texts) for ws in wrong_keywords):
                continue

        summary = card.get("summary", "")
        parts = parse_formula_components(summary)
        source = parts.get("出处", "") or source_ref or book

        # 去重
        key = f"{source}|{parts.get('主治','')[:50]}"
        if key in seen:
            continue
        seen.add(key)

        if parts.get("主治") or parts.get("功能主治"):
            zhuzhi = parts.get("主治") or parts.get("功能主治", "")
            lines.append(f"**《{source.strip('《》')}》**（{dyn}）\n")
            lines.append(f"> {zhuzhi}\n")

    if not lines:
        return "> 暂无经典原文数据。\n"
    return "\n".join(lines)


def generate_composition_table(primary_cards: list[dict]) -> str:
    """生成「组成」表格（仅主卡片）"""
    for card in primary_cards:
        summary = card.get("summary", "")
        parts = parse_formula_components(summary)
        if parts.get("处方") and len(parts["处方"]) > 5:
            fang = parts["处方"]
            drugs = parse_drug_composition(fang)
            if drugs:
                rows = []
                for name, prep, amount in drugs:
                    rows.append(f"| {name} | {amount or '—'} | {prep or '—'} |")
                return (
                    "| 组成 | 剂量 | 炮制 |\n|:----:|:----:|:----:|\n"
                    + "\n".join(rows)
                )
    return "| （暂未提取到） | | |"


def generate_usage_table(primary_cards: list[dict]) -> str:
    """生成「煎服法」章节"""
    for card in primary_cards:
        summary = card.get("summary", "")
        parts = parse_formula_components(summary)
        if parts.get("用法"):
            return f"> **煎服法**：{parts['用法']}"
    return "> （暂未提取到煎服法数据）"


# ── 2. 病机归纳（深度版） ──

def extract_core_pathogenesis(primary_cards: list[dict], keyword: str) -> str:
    """提取核心病机（一句话）"""
    # 优先从东汉《伤寒论》《金匮》的 clinical_theory 卡片提取
    for card in primary_cards:
        if card.get("card_type") != "clinical_theory":
            continue
        dyn, _, _ = identify_source(card)
        if dyn not in ("东汉", "晋"):
            continue
        summary = card.get("summary", "")
        # 找包含病机关键词的最短句子
        sentences = re.split(r'[。！？]', summary)
        for s in sentences:
            s = s.strip()
            if not s or len(s) > 80 or len(s) < 10:
                continue
            if any(kw in s for kw in ["病机", "主之", "主因", "病因为", "故也", "是也"]):
                return s + "。"
    return f"（参见历代医家注解）"


def generate_pathogenesis_table(primary_cards: list[dict]) -> str:
    """生成「病因病机表」（病因→病机 映射），只返回数据行（不含表头）"""
    rows = []
    seen_cause = set()
    for card in primary_cards:
        if card.get("card_type") not in ("clinical_theory", "synthesis"):
            continue
        summary = card.get("summary", "")
        sentences = re.split(r'[。！？]', summary)
        for s in sentences:
            s = s.strip()
            if not s or len(s) > 100 or len(s) < 8:
                continue
            if "病机" in s and "病机" not in seen_cause:
                seen_cause.add("病机")
                rows.append(f"| 参见原文 | {clean_summary(s, max_len=80)} |")
                if len(rows) >= 5:
                    return "\n".join(rows)

    if not rows:
        return "| （数据未充分提取） | |"
    return "\n".join(rows)


def generate_symptoms_table(primary_cards: list[dict]) -> str:
    """生成「证候要点表」（症状→病机），只返回数据行（不含表头）"""
    rows = []
    for card in primary_cards:
        if card.get("card_type") != "clinical_theory":
            continue
        summary = card.get("summary", "")
        sentences = re.split(r'[。！？]', summary)
        for s in sentences:
            s = s.strip()
            if not s or len(s) > 100:
                continue
            m = re.match(r'([^，。]{3,30})[，,](\s*(?:病[在机]|[因缘][于为])[^，。]{3,30})', s)
            if m:
                symptom = clean_summary(m.group(1), max_len=30)
                mechanism = clean_summary(m.group(2), max_len=40)
                rows.append(f"| {symptom} | {mechanism} |")
                if len(rows) >= 8:
                    return "\n".join(rows)
    if not rows:
        return "| （参见经典原文） | |"
    return "\n".join(rows)


def generate_prescription_analysis(primary_cards: list[dict]) -> str:
    """生成「治法方解」"""
    lines = []
    for card in primary_cards:
        if card.get("card_type") != "clinical_theory":
            continue
        summary = card.get("summary", "")
        if any(kw in summary for kw in ["方解", "组方", "君臣", "配伍", "诸药合用", "合用"]):
            sentences = re.split(r'[。！？]', summary)
            for s in sentences:
                s = s.strip()
                if not s or len(s) < 15 or len(s) > 200:
                    continue
                if any(kw in s for kw in ["君", "臣", "佐", "使", "方解", "配伍", "合用"]):
                    lines.append(f"> {s}。")
                    if len(lines) >= 5:
                        break
        if len(lines) >= 5:
            break
    if not lines:
        return "> （治法方解详见历代医家注解章节）"
    return "\n".join(lines)


# ── 3. 方剂演变 ──

def find_related_formulas(primary_cards: list[dict], keyword: str) -> list[str]:
    """从主卡片中提取相关方剂名（排除关键词自身）"""
    related = set()
    # 分解关键词
    keyword_parts = {keyword}
    for suffix in ["汤", "丸", "散", "膏", "丹"]:
        keyword_parts.add(keyword.replace(suffix, ""))

    for card in primary_cards:
        summary = card.get("summary", "")
        for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:汤|丸|散|膏|丹))', summary):
            name = m.group(1)
            if name in related or len(name) < 2:
                continue
            # 排除包含关键词本身的方剂
            skip = False
            for kp in keyword_parts:
                if kp and len(kp) >= 2 and kp in name:
                    skip = True
                    break
            if skip:
                continue
            related.add(name)
    return sorted(related, key=lambda x: -len(x))[:8]


def generate_formula_family_tree(primary_cards: list[dict], keyword: str) -> str:
    """生成方剂家族演变树（基础ASCII图）"""
    related = find_related_formulas(primary_cards, keyword)
    if not related:
        return f"（暂未提取到家族方剂）"

    # 过滤掉非方剂的干扰（如症状组合）
    real_formulas = [r for r in related[:8] if any(s in r for s in ['汤', '丸', '散', '膏', '丹']) and 2 <= len(r) <= 6]

    if not real_formulas:
        return f"（暂未提取到家族方剂）"

    # 简化版：列出本方 + 相关方剂
    lines = [f"{keyword}（本方）"]
    for r in real_formulas[:6]:
        lines.append(f"    ├── 相关方剂：{r}")
    return "\n".join(lines)


def generate_related_formulas_table(primary_cards: list[dict], keyword: str) -> str:
    """生成「相关方剂辨析」表，只返回数据行（不含表头）"""
    related = find_related_formulas(primary_cards, keyword)
    if not related:
        return "| （未提取到） | | |"

    rows = []
    for name in related[:8]:
        rows.append(f"| {name} | 同类方剂 | 详见历代注解章节 |")
    return "\n".join(rows)


# ── 4. 临床应用 ──

def generate_classic_indications_table(primary_cards: list[dict]) -> str:
    """生成「经典适应症」表，只返回数据行（不含表头）"""
    rows = []
    seen = set()
    for card in primary_cards:
        dyn, _, _ = identify_source(card)
        if dyn != "东汉":
            continue
        if card.get("card_type") != "clinical_theory":
            continue
        summary = card.get("summary", "")
        for s in re.split(r'[。；]', summary):
            s = s.strip()
            if not s:
                continue
            if "主之" in s and len(s) < 200:
                key = s[:30]
                if key not in seen:
                    seen.add(key)
                    rows.append(f"| 伤寒/杂病 | {clean_summary(s, max_len=80)} | 主之 |")
                    if len(rows) >= 8:
                        return "\n".join(rows)
        if len(rows) >= 8:
            break
    if not rows:
        return "| （参见出处溯源） | | |"
    return "\n".join(rows)


def generate_modern_diseases_table(primary_cards: list[dict]) -> str:
    """生成「现代对应」表（中医病证 → 现代疾病），只返回数据行（不含表头）"""
    disease_map = {
        "感冒": "上呼吸道感染",
        "发热": "感染性发热",
        "咳嗽": "急慢性支气管炎",
        "哮喘": "支气管哮喘",
        "腹泻": "急性肠炎",
        "便秘": "习惯性便秘",
        "胃痛": "慢性胃炎",
        "胃炎": "慢性胃炎",
        "溃疡": "消化性溃疡",
        "肝炎": "病毒性肝炎",
        "肺炎": "细菌性肺炎",
        "痢疾": "细菌性痢疾",
        "湿疹": "湿疹",
        "痤疮": "寻常痤疮",
        "失眠": "神经衰弱",
        "眩晕": "高血压/梅尼埃病",
        "心悸": "心律失常",
        "水肿": "心/肾性水肿",
        "关节炎": "类风湿性关节炎",
        "糖尿病": "2型糖尿病",
        "高血压": "原发性高血压",
        "冠心病": "冠状动脉粥样硬化性心脏病",
        "心绞痛": "心绞痛",
        "中风": "脑血管意外",
    }

    rows = []
    seen = set()
    for card in primary_cards:
        dyn, _, _ = identify_source(card)
        if dyn not in ("现代", "民国"):
            continue
        summary = card.get("summary", "")
        for cn, modern in disease_map.items():
            if cn in summary and modern not in seen:
                seen.add(modern)
                rows.append(f"| {cn} | {modern} | {dyn} |")
                if len(rows) >= 6:
                    break
        if len(rows) >= 6:
            break
    if not rows:
        return "| （暂未提取到现代对应数据） | | |"
    return "\n".join(rows)


def generate_modern_applications_table(primary_cards: list[dict]) -> str:
    """生成「现代应用」表（民国+现代的临床报道），只返回数据行（不含表头）"""
    rows = []
    seen = set()
    for card in primary_cards:
        dyn, _, _ = identify_source(card)
        if dyn not in ("现代", "民国"):
            continue
        if card.get("card_type") not in ("synthesis", "clinical_theory"):
            continue
        summary = card.get("summary", "")
        for m in re.finditer(r'([^。]{5,80}(?:治疗|应用|用治|用于|适应)[^。]{5,80}。)', summary):
            s = clean_summary(m.group(1), max_len=100)
            key = s[:40]
            if key not in seen and len(s) > 10:
                seen.add(key)
                rows.append(f"| 临床报道 | {s} |")
                if len(rows) >= 5:
                    break
        if len(rows) >= 5:
            break
    if not rows:
        return "| （暂未提取到现代应用数据） | |"
    return "\n".join(rows)


# ── 5. 历代剂量换算 ──

def generate_original_dosage_table(primary_cards: list[dict], keyword: str = "") -> str:
    """生成「原方剂量」表 — 优先选 title 严格匹配 keyword 的卡片"""
    candidates = []
    for card in primary_cards:
        if card.get("card_type") != "herb":
            continue
        title = card.get("title", "")
        summary = card.get("summary", "")
        # 排除加减方、加味方
        if "加减" in title or "加味" in title or "变方" in title:
            continue
        if "加减" in summary[:20] or "加味" in summary[:20]:
            continue
        candidates.append(card)

    # 优先 title 严格等于 keyword 的卡片（如"小柴胡汤"而不是"谷芽枳实小柴胡汤"）
    if keyword:
        exact = [c for c in candidates if c.get("title", "").strip() == keyword.strip()]
        if exact:
            candidates = exact

    sorted_candidates = sorted(candidates, key=sort_key)

    for card in sorted_candidates:
        summary = card.get("summary", "")
        parts = parse_formula_components(summary)
        fang = parts.get("处方", "")
        if fang and "克" not in fang:  # 优先汉制剂量
            drugs = parse_drug_composition(fang)
            if drugs:
                rows = []
                for name, prep, amount in drugs:
                    if not amount:
                        continue
                    display = f"{amount}" + (f"（{prep}）" if prep else "")
                    rows.append(f"| {name} | {display} |")
                if rows:
                    dyn, book, author = identify_source(card)
                    return (
                        f"**原始剂量来源**：《{book.strip('《》')}》{author}\n\n"
                        f"| 药物 | 原书剂量 |\n|:----:|:--------|\n"
                        + "\n".join(rows)
                    )
    return "> （数据库中未保留汉制原方剂量，请参见下方「现代参考剂量」表——其原始数据多来自古籍原方）"


def generate_modern_dosage_table(primary_cards: list[dict], keyword: str = "") -> str:
    """生成「现代参考剂量」表 — 优先选原方而非加减方"""
    candidates = []
    for card in primary_cards:
        if card.get("card_type") != "herb":
            continue
        title = card.get("title", "")
        summary = card.get("summary", "")
        if "加减" in title or "加味" in title or "变方" in title:
            continue
        if "加减" in summary[:20] or "加味" in summary[:20]:
            continue
        candidates.append(card)

    # 优先 title 严格等于 keyword 的卡片
    if keyword:
        exact = [c for c in candidates if c.get("title", "").strip() == keyword.strip()]
        if exact:
            candidates = exact

    sorted_candidates = sorted(candidates, key=sort_key)

    for card in sorted_candidates:
        summary = card.get("summary", "")
        parts = parse_formula_components(summary)
        fang = parts.get("处方", "")
        if not fang:
            continue
        drugs = re.findall(
            r'([\u4e00-\u9fff]+)(?:（[^）]*）)?\s*([\d.]+)(克|两|铢|升|合|枚|个|斤|分|钱|寸匕|方寸匕)?',
            fang
        )
        if not drugs:
            continue

        rows = []
        for name, num, unit in drugs[:12]:
            unit = unit or "两"
            try:
                num_float = float(num)
            except ValueError:
                continue
            modern = num_float * HAN_TO_MODERN.get(unit, 3.0)
            if unit == "枚" or unit == "个":
                modern_str = f"{int(num_float)}{unit}"
            elif unit == "克":
                modern_str = f"{num_float}g（现代）"
            elif modern >= 100:
                modern_str = f"{modern:.0f}ml（约{modern/200:.1f}升）" if "升" in unit else f"{modern:.0f}g"
            elif modern >= 10:
                modern_str = f"{modern:.0f}g"
            else:
                modern_str = f"{modern:.1f}g"
            rows.append(f"| {name} | {num}{unit} | {modern_str} |")

        if rows:
            dyn, book, author = identify_source(card)
            return (
                f"**原始剂量来源**：《{book.strip('《》')}》{author}\n\n"
                f"| 药物 | 原书剂量 | 现代参考剂量 |\n|:----:|:--------:|:-----------:|\n"
                + "\n".join(rows)
            )
    return "> （未提取到现代剂量数据）"


# ── 6. 简表模式（远端默认输出） ──

def generate_legacy_table(keyword: str, primary_cards: list[dict], max_cards: int = 10) -> str:
    """生成简表模式（远端默认输出）"""
    primary_cards.sort(key=sort_key)
    lines = [f"# 「{keyword}」历代医家论述汇总\n"]
    lines.append(f"> 共检索到 **{len(primary_cards)} 条** 直接相关的证据卡片（title 包含「{keyword}」），以下按朝代从古至今排列\n")
    lines.append("")
    lines.append("| 朝代 | 著作 | 作者 | 原文论述摘要 | 卡片类型 |")
    lines.append("|:----:|:----:|:----:|:-----------|:--------:|")

    prev_dynasty = ""
    count_in_dynasty = 0
    for card in primary_cards:
        dyn, book, author = identify_source(card)
        if dyn != prev_dynasty:
            prev_dynasty = dyn
            count_in_dynasty = 0
        count_in_dynasty += 1
        if count_in_dynasty > max_cards:
            continue

        summary = card.get("summary", "")
        card_type = card.get("card_type", "")
        summary_clean = clean_summary(summary)
        summary_clean = summary_clean.replace("|", "｜")
        lines.append(f"| {dyn} | {book} | {author} | {summary_clean} | {card_type} |")

    lines.append("")
    lines.append("---")
    lines.append(f"*数据来源：中医世家知识库 evidence_cards.jsonl（317,580 张卡片）*")
    lines.append(f"*查询关键词：{keyword}*")

    return "\n".join(lines)


# ── 完整报告生成（终极版） ──

def generate_full_report(keyword: str, primary_cards: list[dict], all_matches: int) -> str:
    """生成完整 Markdown 报告（13 章节终极版）"""
    template = load_template()
    if not template:
        print("错误: 找不到报告模板文件", file=sys.stderr)
        return ""

    primary_cards.sort(key=sort_key)
    groups = group_by_dynasty(primary_cards)

    # 替换占位符
    report = template
    report = report.replace("{formula_name}", keyword)
    report = report.replace("{card_count}", str(len(primary_cards)))
    report = report.replace("{total_matches}", str(all_matches))
    report = report.replace("{time_span}", get_time_span(primary_cards))
    report = report.replace("{dynasty_sections}", generate_dynasty_sections(groups))
    report = report.replace("{evidence_index}", generate_index_table(groups))
    report = report.replace("{query_date}", date.today().isoformat())

    # 1. 出处溯源
    report = report.replace("{classic_origins}", generate_classic_origins(primary_cards))
    report = report.replace("{composition_table}", generate_composition_table(primary_cards))
    report = report.replace("{usage_table}", generate_usage_table(primary_cards))

    # 10. 病机归纳
    report = report.replace("{core_pathogenesis}", extract_core_pathogenesis(primary_cards, keyword))
    report = report.replace("{pathogenesis_table}", generate_pathogenesis_table(primary_cards))
    report = report.replace("{symptoms_table}", generate_symptoms_table(primary_cards))
    report = report.replace("{prescription_analysis}", generate_prescription_analysis(primary_cards))

    # 11. 方剂演变
    report = report.replace("{formula_family_tree}", generate_formula_family_tree(primary_cards, keyword))
    report = report.replace("{related_formulas_table}", generate_related_formulas_table(primary_cards, keyword))

    # 12. 临床应用
    report = report.replace("{classic_indications_table}", generate_classic_indications_table(primary_cards))
    report = report.replace("{modern_diseases_table}", generate_modern_diseases_table(primary_cards))
    report = report.replace("{modern_applications_table}", generate_modern_applications_table(primary_cards))

    # 13. 剂量换算
    report = report.replace("{original_dosage_table}", generate_original_dosage_table(primary_cards, keyword))
    report = report.replace("{modern_dosage_table}", generate_modern_dosage_table(primary_cards, keyword))

    return report


# ── 主流程 ──

def main() -> None:
    parser = argparse.ArgumentParser(
        description="中医方剂/条文标准化查询 — 按朝代排序输出医家论述",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python scripts/formula_query.py 桂枝人参汤              # 简表模式（默认）
  python scripts/formula_query.py 小柴胡汤 --full-report  # 完整结构化报告
  python scripts/formula_query.py 甘草泻心汤 --full-report -o 报告.md
        """,
    )
    parser.add_argument("keyword", help="要查询的方剂名/条文名/关键词")
    parser.add_argument(
        "--references-dir",
        default="../references",
        help="references 目录路径 (默认 ../references)",
    )
    parser.add_argument(
        "--max-cards",
        type=int,
        default=10,
        help="每个朝代最多输出多少条 (默认 10)",
    )
    parser.add_argument(
        "--full-report",
        action="store_true",
        help="生成完整结构化 Markdown 报告（13 章节终极版）",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="完整报告输出路径（默认: {方剂名}历代注解.md）",
    )
    args = parser.parse_args()

    base = (Path(__file__).resolve().parent / args.references_dir).resolve()
    cards_path = base / "text_distillation" / "evidence_cards.jsonl"

    if not cards_path.exists():
        print(f"错误: 找不到数据文件 {cards_path}")
        print("请检查 --references-dir 参数")
        return

    print(f"正在搜索「{args.keyword}」...", file=sys.stderr)
    matches = search_cards(args.keyword, cards_path)
    print(f"找到 {len(matches)} 条相关记录", file=sys.stderr)

    # 分类：主卡片 vs 次卡片
    primary, secondary = classify_cards(matches, args.keyword)
    print(f"其中直接相关（title 匹配）: {len(primary)} 条", file=sys.stderr)
    print(f"间接提及: {len(secondary)} 条\n", file=sys.stderr)

    if not primary:
        print(f"未找到与「{args.keyword}」直接相关的记录（仅{len(secondary)}条间接提及）。")
        print("请尝试更精确的关键词。")
        return

    # 完整报告模式
    if args.full_report:
        report = generate_full_report(args.keyword, primary, len(matches))
        if not report:
            return

        output_path = args.output
        if not output_path:
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', args.keyword)
            output_path = f"{safe_name}历代注解.md"

        Path(output_path).write_text(report, encoding="utf-8")
        print(f"✅ 完整报告已保存至: {output_path}")
        return

    # 默认表格模式
    print(generate_legacy_table(args.keyword, primary, args.max_cards))


if __name__ == "__main__":
    main()