#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite 工具模块 — 共享 find_sqlite_path() + Windows stdout 修复

所有访问 20120413mssql.sqlite 的脚本统一使用此模块。
"""

from __future__ import annotations

import io
import sys
from pathlib import Path


def setup_windows_stdout() -> None:
    """Windows 终端 UTF-8 修复"""
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        except Exception:
            pass


def find_sqlite_path(sqlite_arg: str | None = None) -> Path:
    """三级查找 SQLite 文件路径

    优先级：
    1. CLI 显式参数
    2. ~/.cache/zhongyishijia/20120413mssql.sqlite
    3. ~/.local/share/zhongyishijia/20120413mssql.sqlite
    4. <repo>/references/raw/20120413mssql.sqlite
    """
    candidates: list[Path] = []
    if sqlite_arg:
        candidates.append(Path(sqlite_arg))
    candidates.extend([
        Path.home() / ".cache" / "zhongyishijia" / "20120413mssql.sqlite",
        Path.home() / ".local" / "share" / "zhongyishijia" / "20120413mssql.sqlite",
        Path(__file__).resolve().parent.parent / "references" / "raw" / "20120413mssql.sqlite",
    ])
    for c in candidates:
        if c and c.exists() and c.is_file():
            return c
    raise FileNotFoundError(
        "找不到 20120413mssql.sqlite。请：\n"
        "1. 设置环境变量：ZHONGYISHIJIA_SQLITE=/path/to/20120413mssql.sqlite\n"
        "2. 或放到 ~/.cache/zhongyishijia/20120413mssql.sqlite\n"
        "3. 或放到 <project>/references/raw/20120413mssql.sqlite\n"
        "4. 或使用 --sqlite 参数指定路径"
    )
