# `zhongyishijia-skill` 推送 SOP(feat/* → main 手动 PR 流程)

> **触发**:Erik 说「可以, 蒸馏 然后 推送」+ 紧接着说「是合并到 main」时,本 skill 的推送必须走**两步**:① 先推 `feat/<topic>-<date>` 分支到 origin,② 本地 `ff-only merge feat → main` + `git push origin main`(Erik 显式授权代行手动 PR)。
>
> **数据源**:2026-09-17 阴疮专题蒸馏 + 推送实战固化(commit `32f0191` → `844c85a` → `737abb6`)。

---

## 一、推送流程(6 步,本 skill 特有)

### Step 1: 检查本地 git 状态

```bash
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage
git status -sb
git log --oneline @{u}..HEAD  # 应为空(无领先 commit)
```

**预期**:
- 默认分支是 `main`(不是 `feat/*`)
- 工作区可有 M / ?? 文件(待推送的内容)
- 不应有未推送 commit(本地未推送意味着上次推送失败,需先调查)

### Step 2: 创建 feat 分支

```bash
git checkout -b "feat/<topic-keyword>-<YYYY-MM-DD>"
# 例: git checkout -b "feat/yin-chuang-treatment-2026-09-17"
git status -sb   # 验证: ## feat/<topic-keyword>-<YYYY-MM-DD> ...有 M / ?? 文件
```

**Pitfall — 分支名约定**:`feat/<keyword>-<date>` 双段式,keyword 用 kebab-case,date 用 `YYYY-MM-DD` 格式,总长 ≤ 64 字符。**不要**用 `add-topic`(单一动词太弱)/ `2026-09-17`(纯日期无内容)。

### Step 3: 一次性 add + commit

```bash
git add references/<new_file>.md SKILL.md
git status -sb   # 验证: M/A 行(已 staged),无 ?? 残留
git commit -m "feat: 蒸馏「<topic>」专题 + Reference Priority #N 登记

- 新增 references/<topic>.md (<size> / <lines>):
  <核心结构概要 3-5 行>

- SKILL.md Reference Priority 追加 #N(编号连续 1-N 无 gap)
- data: <symptom_query / text_search> <关键词> <命中数>
- trigger: 「<kw1>」「<kw2>」..."
```

**Pitfall — commit message 模板**:**必须**包含 4 段:
- 一行标题(`feat:` / `fix:` / `docs:` / `refactor:`)
- `- 新增 references/<file>` 段(文件大小 + 核心内容 bullet 3-5)
- `- SKILL.md` 段(同步了什么 + 编号连续验证)
- `- data` 段(corpus 查询命令 + 命中数)
- `- trigger` 段(触发词列表)

**Erik 偏好**:commit message 要包含**足够上下文**让任何未来 agent 不需要 git log -p 就能理解本次变更意图。

### Step 4: 推送 feat 分支到 origin(设 upstream)

```bash
git push -u origin "feat/<topic-keyword>-<YYYY-MM-DD>"
```

**预期输出**:
```
remote: Create a pull request for 'feat/<topic-keyword>-<YYYY-MM-DD>' on GitHub by visiting:
remote:      https://github.com/erikgqp8645/zhongyishijia-skill/pull/new/feat/<topic-keyword>-<YYYY-MM-DD>
remote:
To https://github.com/erikgqp8645/zhongyishijia-skill.git
 * [new branch]      feat/... -> feat/...
branch 'feat/...' set up to track 'origin/feat/...'.
```

### Step 5: 等 Erik 确认「是合并到 main」后再 ff-only merge + push main

**关键铁律(本 skill 头部约定)**:「main 由老锅手动 PR」——所以**默认情况**下不应该自动 push main。但 Erik 显式说「是合并到 main」= 授权代行手动 PR,**此时**才能走以下流程:

```bash
# 5a. 检查 feat 分支 commit 已推
git log --oneline feat/<topic-keyword>-<YYYY-MM-DD> -1   # 必须有 commit

# 5b. 切换 main + ff-only merge(纯快进,无冲突)
git checkout main
git merge --ff-only feat/<topic-keyword>-<YYYY-MM-DD>
# 预期: Fast-forward, SKILL.md + references/<topic>.md 等文件被推入 main

# 5c. 推送 main
git push origin main
# 预期: <old_head>..<new_head>  main -> main

# 5d. 验证
git log --oneline -3   # main 应停在 feat 的 commit
git status -sb         # 干净, ## main...origin/main
```

### Step 6: 清理 feat 分支(本地 + 远端)

```bash
git branch -d "feat/<topic-keyword>-<YYYY-MM-DD>"  # 本地删除(已被 main 包含,安全)
git push origin --delete "feat/<topic-keyword>-<YYYY-MM-DD>"  # 远端删除
git branch -a   # 验证: 仅 main + remotes/origin/main
```

**Pitfall — 必须在 Step 5 之后才执行 Step 6**:如果先删了 feat 分支但 main 还没合并,就丢失了 commit。

---

## 二、推送验证 SOP(必须做,不能跳)

### 2.1 GitHub raw cache 滞后陷阱(本 session 实测)

**症状**:`git push` 成功 + `gh api` 返回正确内容,但 `curl https://raw.githubusercontent.com/...` 返回旧版本。

**实测数据**(2026-09-17 阴疮推送):
- `git push origin main` 成功后立即 curl → `content-length: 35292`(新版本正确)
- 30 秒后 curl → `content-length: 28813`(回退到旧版!)→ 这是 **GitHub raw cache 滞后**
- 用 `gh api repos/<owner>/<repo>/contents/<path>` 验证 → 返回新版本(`content-length: 35292`)→ 权威

**根因**:`raw.githubusercontent.com` 走 Fastly/Varnish CDN,不同 edge 节点 cache TTL 不一致(常见 5-30 分钟)。

**解决方案**:

```bash
# 1. 权威验证(不走 CDN,直接走 GitHub API)
gh api repos/erikgqp8645/zhongyishijia-skill/contents/<file-path> \
   --jq '.content' | base64 -d | <verify-command>

# 2. 或者等 8 秒后重试 raw curl(有时有效)
sleep 8 && curl -sI "https://raw.githubusercontent.com/.../<file-path>" | grep -i content-length

# 3. 如果还不一致,以 gh api 为准(权威源)
```

### 2.2 推送验证三件套(mandatory)

```bash
# 1. 文件存在 + 大小正确(本地 vs 推送)
echo "本地:" && ls -lh <file-path>
echo "推送:" && gh api repos/erikgqp8645/zhongyishijia-skill/contents/<file-path> --jq '.size'

# 2. SKILL.md 中新专题命中数(预期 = N,本 skill 是 1,不是 3)
gh api repos/erikgqp8645/zhongyishijia-skill/contents/SKILL.md --jq '.content' | base64 -d | grep -c "<new-file-basename>.md"

# 3. main commit 指针
git log --oneline -1 main
gh api repos/erikgqp8645/zhongyishijia-skill/commits/main --jq '.sha[:7]'  # 验证两值相等
```

---

## 三、`feat/*` 分支策略的实战权衡

| 策略 | 优点 | 缺点 | 适用场景 |
|---|---|---|---|
| **A. 直推 main**(本 skill 旧方式) | 一步完成,快 | 违反 SKILL.md「main 由老锅手动 PR」约定 | — |
| **B. feat/* + 本地 ff-merge + push main**(本 session 实战) | 留 PR 记录 + 仍保留 main 自动前移 | 多一步分支创建 | **Erik 显式授权**时 |
| **C. feat/* + gh pr create + gh pr merge --squash**(纯 PR 流程) | 完整 PR 记录 | 需要 gh pr merge,本地 main 不自动前移 | Erik 期望留 PR 历史时 |
| **D. 本地 main ff-merge,远端不 push**(等 Erik 自己 push) | 最安全 | Erik 还得手动 push | **不确定 Erik 意图**时 |

**默认走 B**(本 session 实战模式)。**Erik 没明确意图时**用 D 并提示「main 未推送,请 Erik 确认」。

---

## 四、与 yilin-mentor-lineage 推送 SOP 的关键差异

| 维度 | yilin-mentor-lineage | zhongyishijia-expert-mentor-lineage |
|---|---|---|
| 分支策略 | `master`(默认分支) | `main` + `feat/*` 旁路 |
| 主分支谁推 | 老锅直接 push master | **老锅手动 PR**(禁止自动 push main) |
| 工作流 | clone-to-/tmp + 完整版覆盖简化版 + 单 commit | 本地 feat/* 分支 + ff-merge main |
| Push 后清理 | /tmp 目录删除 + git status 干净 | 本地 + 远端 feat 分支删除 |
| Cache 验证 | curl raw.githubusercontent.com | **必须用 gh api**(cache 滞后更严重) |

**重要**:**不要**把 yilin-mentor-lineage 的「clone-to-/tmp」套路套到这个 skill——本地已经在 skill 目录内(`~/.hermes/skills/zhongyishijia-expert-mentor-lineage/`),不需要再 clone 到 /tmp。

---

## 五、常见错误模式(踩过的坑)

### 5.1 切 main 失败:「Your local changes would be overwritten」

**根因**:feat 分支上还有未 commit 的改动(比如新加的「1 处同步铁律」节没 commit),直接 `git checkout main` 会冲突。

**修复**:
```bash
git status -sb   # 确认 M 文件
git add .
git commit -m "docs(skill): <变更描述>"
git push origin feat/<topic-keyword>-<YYYY-MM-DD>   # 先把 feat 推上
git checkout main   # 此时无冲突
```

**预防**:每次 patch SKILL.md 后立即 commit + push(避免 working tree 堆积)。

### 5.2 `git branch -d` 失败:branch not fully merged

**根因**:feat 分支有 main 上没有的 commit(也就是没合并到 main)。**绝对不能**用 `-D` 强删(丢失 commit)。

**修复**:先 `git merge --ff-only feat/...` 把 main 推进到 feat,再 `git branch -d feat/...`。

### 5.3 Push 后 gh api 与 raw curl 不一致

按 2.1 节,gh api 权威,raw curl 是 cache。不要重试 raw curl 浪费时间。

### 5.4 SKILL.md 同步铁律示例命令自指 bug(本 session 实测)

**症状**:`grep -c "<filename>" SKILL.md` 返回 3(预期 1)。

**根因**:SKILL.md 的「校验规则」节内嵌的 bash 示例用了真实文件名(比如 `yin_chuang_treatment.md`),与 Reference Priority 列表中的真实登记行重叠,grep 不区分示例与登记,都计数。

**预防**:示例命令**永远用占位符**,不写真实文件名:

```bash
# 错的写法(自指 bug)
grep -c "yin_chuang_treatment.md" SKILL.md   # → 3(2 个在示例 + 1 个在 Reference Priority)

# 对的写法(占位符)
grep -c "<file_basename>.md" SKILL.md        # → 1(只在 Reference Priority 真实登记)
```

**实战 commit**:`737abb6 fix(skill): 修复 1 处同步铁律示例命令自指 bug(改用占位符)`

---

## 六、相关 Pitfall 联动

- **本 skill 「1 处同步铁律」节**(SKILL.md 行 18):本 skill 只在 Reference Priority 登记 1 次,不要去找 Trigger Vocabulary / Pre-built 节(yilin-mentor-lineage 风格)
- **`repo-bidirectional-sync` skill**(cross-skill):Erik 推送 SOP 的通用模式,本 skill 是其 feat/* 分支策略的具体实现
- **`github-workflow` skill**:gh CLI 认证 / PAT 处理 / 分支策略(已含本 skill 的 `feat/*` 约束)

---

## 附录:实战 commit 历史(2026-09-17 阴疮专题)

```
737abb6 fix(skill): 修复 1 处同步铁律示例命令自指 bug(改用占位符)
844c85a docs(skill): 同步铁律说明(1 处同步结构,vs yilin-mentor-lineage 的 3 处同步)
32f0191 feat: 蒸馏「阴疮」专题 + Reference Priority #33 登记
3203b9d docs(references): 新增颈肩腰腿痛膏药方大全 + 膏药方查询工作流   ← 原 main HEAD
```

**关键发现**:本 session 一次性产出 3 个 commit(feat + 同步铁律元注释 + 自指 bug 修复),反映 Erik 的「蒸馏 + 推送 + 合并到 main」连续流。**未来同类型 session 应主动规划 3 commit 结构**,而不是单 commit 堆叠。