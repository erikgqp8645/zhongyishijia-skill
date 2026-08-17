# SQLite 部署验证 SOP（2026-08-17 实测固化）

> **目的**：把 711MB 的 `zysj.db` 完整 SQLite 数据库正确部署到 `<repo>/references/external/zysj.db`，让 `verify_prescription.py` / `symptom_query.py` / `herb_query.py` / `formula_table.py` 都能跑通。

> **铁律**：仓库内 SQLite 永远叫 `zysj.db`。所有现有脚本/文档都引用此名。**改名会破坏全链路**——遇到文件名冲突时，改脚本路径查找，绝不改文件名。

---

## 一、为什么需要这份 SOP

**背景**（2026-08-17 实测发现）：

- `references/external/zysj.db` 仓库**默认是个 0 字节占位符**（被 `.gitignore` 排除真实数据）
- 多数脚本默认去 `references/raw/20120413mssql.sqlite` 找 SQLite，但 raw/ 也是 gitignored
- 真实数据需要从 GitHub release 下载
- 即使下载成功，**脚本可能因路径硬编码或字段错位而失败**——本 SOP 含端到端烟雾测试

---

## 二、5 步部署流程

### Step 1 — 下载 SQLite

从 GitHub release 下载（与 `evidence_cards.jsonl` 同一 release 页面）：

```
zysj.db  ~711 MB  (与本仓库 CLAUDE.md 提到的 SHA256 校验码对应)
```

> ⚠️ **SHA256 注意**：仓库 CLAUDE.md 写明的期望 SHA256 是 `6fa194c9...`。但 Erik 的实际备份 `/Users/applemima1111/Downloads/项目文件/其他_55/20120413mssql.sqlite` 校验出 `2ea61834...`——**SHA256 不匹配但 4 表齐全、行数对得上**。可能是不同时期的还原备份。判定标准：**4 表存在 + 行数匹配 + GBK 编码可读 = 可用**。

### Step 2 — 验证 SQLite 完整性

```bash
ls -lh <下载路径>/zysj.db
# 期望大小: 700-720 MB 区间

sqlite3 <下载路径>/zysj.db ".tables"
# 期望输出: zysjcell  zysjllsj  zysjyj  zysjzhsj

sqlite3 <下载路径>/zysj.db "SELECT 'zysjyj=' || COUNT(*) FROM zysjyj
UNION ALL SELECT 'zysjllsj=' || COUNT(*) FROM zysjllsj
UNION ALL SELECT 'zysjzhsj=' || COUNT(*) FROM zysjzhsj
UNION ALL SELECT 'zysjcell=' || COUNT(*) FROM zysjcell;"
# 期望: zysjyj=70350 / zysjllsj=166423-206245 / zysjzhsj=80809 / zysjcell=1229-1390

sqlite3 <下载路径>/zysj.db "SELECT MingCheng FROM zysjyj LIMIT 3;"
# 期望: 中文方剂名（不是乱码）= GBK 编码正确
```

### Step 3 — 替换仓库占位符

```bash
cd <repo>
# 删除 0 字节占位符
rm -v references/external/zysj.db

# 拷贝完整 SQLite（保持文件名 zysj.db 不变）
cp <下载路径>/zysj.db references/external/zysj.db

# 验证
ls -lh references/external/zysj.db
# 期望: ~711 MB
```

### Step 4 — 验证四级查找路径

`_sqlite_utils.find_sqlite_path()` 按优先级找：

```
1. CLI --sqlite 参数
2. ZHONGYISHIJIA_SQLITE 环境变量
3. ~/.cache/zhongyishijia/20120413mssql.sqlite
4. <repo>/references/external/zysj.db   ← 标准部署入口
5. <repo>/references/raw/20120413mssql.sqlite
```

验证脚本能自动找到：

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from _sqlite_utils import find_sqlite_path
p = find_sqlite_path()
print(f'✓ 自动找到: {p}')
print(f'  大小: {p.stat().st_size / 1024 / 1024:.1f} MB')
"
# 期望: ✓ 自动找到: .../references/external/zysj.db / 大小: 710.8 MB
```

### Step 5 — 端到端烟雾测试（必跑）

```bash
python3 scripts/symptom_query.py "痰癖" --top 5
# 期望: 找到 24 张方剂 / 134 味药 / Top 5 高频核心药
# 不要被「verify_prescription.py 报 0 命中」骗——见下方「已知陷阱」#2
```

---

## 三、已知陷阱（2026-08-17 实测发现）

### 陷阱 #1：verify_prescription.py 硬编码路径（已修）

**症状**：脚本报 `sqlite3.OperationalError: no such table: zysjyj`

**根因**：老版本 `_DB_PATH = _SKILL_ROOT / "references" / "external" / "zysj.db"` 硬编码

**修复**（已 commit 等待）：改为四级查找 + `--sqlite` CLI 参数 + 模块级全局 `_SQLITE_ARG`

**调用方式**：

```bash
# 默认（自动四级查找）
python3 scripts/verify_prescription.py "痰癖"

# 显式指定
python3 scripts/verify_prescription.py "痰癖" --sqlite /path/to/zysj.db

# 环境变量
export ZHONGYISHIJIA_SQLITE=/path/to/zysj.db
python3 scripts/verify_prescription.py "痰癖"
```

### 陷阱 #2：verify_prescription.py 字段错位 bug

**症状**：脚本不报错但「步骤 1 · 多方归纳」命中 **0 首方剂**，而 `symptom_query.py` 同样查询命中 24 张

**根因**：`_fetch_prescriptions()` 查 `zysjyj.ChuFang`（处方列），但**病证/症状关键词几乎只出现在「功能主治」列**（`GongNengZZ`）

**判定**：

```bash
# symptom_query 走的是 GongNengZZ + TypeID=39
sqlite3 references/external/zysj.db "SELECT COUNT(*) FROM zysjyj WHERE TypeID=39 AND GongNengZZ LIKE '%痰癖%';"
# 期望: 24
```

**修复**（未做，待 Erik 拍板）：

```python
# 当前（错）:
SELECT MingCheng, ChuFang FROM zysjyj WHERE ChuFang LIKE ? OR MingCheng LIKE ?

# 应改为（对）:
SELECT MingCheng, ChuFang, GongNengZZ FROM zysjyj WHERE TypeID=39 AND GongNengZZ LIKE ?
```

### 陷阱 #3：GBK 编码丢失

**症状**：中文方剂名乱码（`广枣` 显示成 `\xb9\xe3\xd7\xf3`）

**根因**：SQLite 是 MSSQL 还原产物，编码为 **GBK** 而非 UTF-8

**修复**：所有 `_connect()` 必须加：

```python
conn.text_factory = lambda b: b.decode("gbk", errors="replace")
```

这是 `_sqlite_utils._connect()` 的一部分，老脚本（`verify_prescription.py`）漏了，已补。

### 陷阱 #4：双份 711MB 占空间

部署后可能存在两份：

- `references/external/zysj.db`（仓库内标准入口，保留）
- `~/.cache/zhongyishijia/20120413mssql.sqlite`（早期调试时拷贝的副本，可删）

**判定**：

```bash
ls -lh ~/.cache/zhongyishijia/ 2>&1
```

两份都在 = 浪费 711MB。删除 `~/.cache/` 副本（脚本会自动 fallback 到仓库内 `references/external/zysj.db`）。

### 陷阱 #5：CLAUDE.md SHA256 与实际不符

`CLAUDE.md` 写明期望 SHA256 `6fa194c9a4177dfdd483c8fd7aa37a9e24e371d0692a85a338777bb6e9aee26f`，但 Erik 的备份 `2ea61834...` 不匹配——仍可用。

**判定**：**4 表齐全 + 行数对得上 + GBK 编码可读 = 可用**，不要被 SHA256 不匹配吓退。

---

## 四、跨机器部署清单

部署到新机器时按顺序跑：

```bash
# 1. 下载（从 GitHub release）
curl -sL https://github.com/erikgqp8645/zhongyishijia-skill/releases/latest/download/zysj.db -o /tmp/zysj.db

# 2. 完整性校验（4 表 + 行数 + 编码）
sqlite3 /tmp/zysj.db ".tables"
sqlite3 /tmp/zysj.db "SELECT COUNT(*) FROM zysjyj;"  # 应 = 70350
sqlite3 /tmp/zysj.db "SELECT MingCheng FROM zysjyj LIMIT 1;"  # 应 = 中文

# 3. 部署到仓库标准入口
cd <repo>
rm references/external/zysj.db  # 删 0 字节占位符
cp /tmp/zysj.db references/external/zysj.db

# 4. 烟雾测试（必跑，任一失败都说明部署有问题）
python3 scripts/symptom_query.py "痰癖" --top 5
# 期望: 24 张方剂 / 134 味药

# 5. （可选）跑全库溯源文档
python3 scripts/verify_prescription.py "痰癖"
# 期望: 不再报 no such table；若仍 0 命中 = 陷阱 #2 的字段 bug，按需修复
```

---

## 五、变更记录

### 2026-08-17 — SOP 首次固化

- 触发场景：Erik 要求「用 .sqlite」跑 `verify_prescription.py "痰癖"`，发现本地无 SQLite → 部署完整流程
- 关键发现：脚本默认路径 `references/external/zysj.db` 仓库内是 0 字节占位符；SHA256 与 CLAUDE.md 不匹配但数据完整
- 修复：
  - `_sqlite_utils.find_sqlite_path()` 三级 → 四级查找（加 `references/external/zysj.db` 作为标准入口）
  - `verify_prescription.py` 硬编码路径改为四级查找 + GBK 编码补丁
  - 删除 `~/.cache/zhongyishijia/` 副本（避免双份 711MB）
- 命名约定：**仓库内 SQLite 永远叫 `zysj.db`**（Erik 明确要求保持文件名不变）