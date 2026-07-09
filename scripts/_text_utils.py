#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本工具模块 — 共享 esc() + extract_herbs()

所有输出 Markdown / 提取药名的脚本统一使用此模块。
"""

from __future__ import annotations

import html
import re


# ── NOISE 词表（扩展版）────────────────────────────────────────────
# 排除：通用非药名 + 炮制关键词 + 剂型/服用关键词
HERB_NOISE: set[str] = {
    # 通用非药名
    "一方", "各等分", "各等份", "等分", "一方各", "兼给", "各半",
    "各", "每服", "右为", "右七味", "右六味", "右八味",
    "右九味", "右十味", "一两", "二两", "三两", "二枚", "三枚",
    # 炮制关键词（避免误提取"去皮脐"等）
    "去皮", "去节", "去核", "去心", "去芦", "去骨",
    "去脐", "去刺", "去翅", "去鳞", "去蒂", "去膂",
    "炙", "炒", "煨", "烘", "酒浸", "醋浸", "水洗",
    "米泔浸", "泔浸", "泔洗",
    "炮", "煅", "煮", "蒸", "焙", "炙甘草",
    # 剂型/服用关键词
    "丸", "汤", "散", "膏", "煎", "渍", "酿", "末",
    "服", "钱匕", "钱", "匕", "盏", "升", "合",
}


def safe_utf8(val, default: str = "") -> str:
    """SQLite 原始值（UTF-8） → UTF-8 字符串"""
    if val is None:
        return default
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)


def s(val) -> str:
    """安全转字符串（SQLite UTF-8 bytes→UTF-8），并去除首尾空白"""
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace").strip()
    return str(val).strip()


def esc(text: str, limit: int = 0) -> str:
    """解码 HTML 实体 + 转义 | 和换行符，并在指定长度截断（转义在截断之前执行）

    - 先调用 html.unescape() 解 &amp; &quot; &nbsp; 等 HTML 实体
    - ``|`` → ``｜``（全角竖线，防止 Markdown 表格断行）
    - 换行符 → 空格
    - 先解码实体，再转义，再截断
    """
    text = html.unescape(text)
    text = re.sub(r"[|\n\r]", " ", text)
    text = text.strip()
    if limit > 0 and len(text) > limit:
        text = text[:limit] + "…"
    return text


def extract_herbs(chufang: str) -> list[str]:
    """从 ChuFang 字段提取药名列表

    策略：先用（）分割去除炮制指令段，再按分隔符提取药名。
    例: "天雄（炮.去皮.脐）麻黄（去节）" → ["天雄", "麻黄"]
    """
    if not chufang:
        return []
    herbs: list[str] = []

    # 第 1 步：去除炮制指令段
    cleaned = re.sub(r"[（(][^)）]*[)）]", "", chufang)

    # 第 2 步：按分隔符分割
    parts = re.split(r"[,，。、\s]+", cleaned)

    # 第 3 步：NOISE 过滤 + 药名提取
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^([一-龥]{2,10})", part)
        if m:
            name = m.group(1).strip()
            if name not in HERB_NOISE:
                herbs.append(name)
    return herbs
