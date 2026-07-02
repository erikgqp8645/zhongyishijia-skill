#!/usr/bin/env python3
"""增强版 search - 同时搜索 references 和 markdown 数据源"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

# 项目根 (markdown 目录)
PROJECT_ROOT = Path(r'C:\Users\hxst01\Documents\aicoding\zhongyishijia\data')
MD_DIR = PROJECT_ROOT / 'markdown'

# 类别关键词映射 (query 包含这些词时, 优先搜对应目录)
CATEGORY_HINTS = {
    '中药': ['人参', '黄芪', '当归', '甘草', '药性', '归经', '性味', '处方'],
    '临床': ['伤寒', '温病', '金匮', '经方', '方剂'],
    '古医': ['黄帝内经', '素问', '灵枢', '难经'],
}

def match_query(text: str, query: str) -> bool:
    return query.lower() in text.lower() if query else False

def search_md(query: str, limit_per_cat: int = 20) -> list:
    """搜 markdown 目录, 按类别返回"""
    results = []
    if not MD_DIR.exists():
        return results
    for cat_dir in sorted(MD_DIR.iterdir()):
        if not cat_dir.is_dir():
            continue
        for md_file in cat_dir.glob('*.md'):
            try:
                text = md_file.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            if match_query(text, query):
                # 找出 query 所在行的上下文
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if match_query(line, query):
                        ctx_start = max(0, i - 1)
                        ctx_end = min(len(lines), i + 3)
                        ctx = ' | '.join(lines[ctx_start:ctx_end]).strip()[:200]
                        results.append({
                            'category': cat_dir.name,
                            'file': md_file.name,
                            'path': f'markdown/{cat_dir.name}/{md_file.name}',
                            'line': i + 1,
                            'context': ctx,
                        })
                        if len([r for r in results if r['category'] == cat_dir.name]) >= limit_per_cat:
                            break
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('query')
    parser.add_argument('--limit', type=int, default=30)
    parser.add_argument('--references-dir', default='../references')
    args = parser.parse_args()

    print(f'=== 搜索: {args.query!r} ===\n')
    results = search_md(args.query, limit_per_cat=5)
    if not results:
        print('(无结果)')
        return
    by_cat = {}
    for r in results:
        by_cat.setdefault(r['category'], []).append(r)
    for cat, items in by_cat.items():
        print(f'## {cat} ({len(items)} 条匹配)')
        for r in items[:3]:
            print(f'  {r["file"]}:{r["line"]}: {r["context"]}')
        print()
    print(f'总计: {len(results)} 条')

if __name__ == '__main__':
    main()