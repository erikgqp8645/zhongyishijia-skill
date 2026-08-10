---
name: simple_sync
purpose: 3-machine (单位 Mac / 家里 Mac / 家里 Windows) direct-main-branch workflow for zhongyishijia-skill — simpler than worktree, uses git pull --rebase + direct push to main
trigger: 「多机器同步」「回家」「出门」「push check」「before_leaving」「3 机方案」「simplified」
date_verified: 2026-08-10
replaces: WORKTREE_GUIDE.md (2026-08-10 v2 rolled back — worktree ambiguous skill loader conflict)
machines:
  - id: office-mac
    hostname: Mac-mini.local (单位)
    role: 主工作机,大部分 commit 来自这里
    path: ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/
  - id: home-mac
    hostname: 家里 Mac-mini
    role: 家里 Mac 备用工作机
    path: ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/
  - id: home-win
    hostname: 家里 Windows
    role: 家里 Windows 备用工作机
    path: %USERPROFILE%\.hermes\skills\zhongyishijia-expert-mentor-lineage\
---

# zhongyishijia-skill 三机直接同步工作流

## 一、为什么是这套方案(对比 worktree)

**之前 worktree 方案的痛点**(2026-08-10 验证后回滚):
- 4 个 worktree 都在 `~/.hermes/skills/` 下 → Hermes skill loader 报 `Ambiguous skill name`,加载失败
- 移动到 `~/.hermes/worktrees/` 修复了 loader 问题,但每个 worktree 还是独立目录,books_json (206MB) 重复 checkout 慢
- 每周/每月合并 office / home-mac / home-win 三个分支到 main,3 个潜在冲突源

**本方案的核心思想**:
> **三台机器共用同一个 main 分支,不开 worktree,不开新分支**。

每台机器上只有 1 个工作目录,所有改动直接 commit 到 main,push 到 origin/main。

**优点**:
- ✅ 零配置,零分支管理
- ✅ push/pull 是 git 最基本的操作,不会有 skill loader ambiguous
- ✅ 大文件只在每台机器 checkout 一次(每台机器首次 git clone)
- ✅ 「我的工作状态在远端」 — 任何机器 pull 后都是最新

**缺点**:
- ⚠️ 三台机器**同时编辑同一个文件会冲突**(但单人编辑场景概率极低)
- ⚠️ 没有「主题隔离」(改了 office 文件不影响 home-mac 文件)

─────────────────────────────────────────────────────

## 二、各机器首次 setup

### 2.1 单位 Mac (当前,已完成)

路径:`~/.hermes/skills/zhongyishijia-expert-mentor-lineage/`,分支 main,远端追踪 origin/main。

不需要任何额外操作。

### 2.2 家里 Mac (首次回家前)

**方案 A — 在单位机预先 bundle**(推荐):

```bash
# 在单位机上
mkdir -p ~/.hermes/skills-bundles

# 1. 创建一个 bare 仓库(只有 git objects,没有 working tree)
git clone --bare https://github.com/erikgqp8645/zhongyishijia-skill.git \
    ~/.hermes/skills-bundles/zhongyishijia-skill.git

# 2. 验证
ls ~/.hermes/skills-bundles/zhongyishijia-skill.git/objects/ | head -5

# 3. (可选)用 U 盘 / iCloud / 微信传文件 把这个目录拷到家里 Mac
#    目标路径: ~/.hermes/skills-bundles/zhongyishijia-skill.git
```

```bash
# === 回家后,在家里 Mac 上 ===
mkdir -p ~/.hermes/skills
cd ~/.hermes/skills

# 从本地 bundle 克隆(快,不依赖网速)
git clone ~/.hermes/skills-bundles/zhongyishijia-skill.git \
    zhongyishijia-expert-mentor-lineage

cd zhongyishijia-expert-mentor-lineage

# 切换 remote 到 GitHub
git remote set-url origin https://github.com/erikgqp8645/zhongyishijia-skill.git

# 验证
git branch --show-current   # 应输出: main
git status                  # 应输出: Your branch is up to date
```

**方案 B — 家里 Mac 直接 git clone(如果网络通)**:

```bash
# === 回家后,在家里 Mac 上 ===
mkdir -p ~/.hermes/skills
cd ~/.hermes/skills

git clone https://github.com/erikgqp8645/zhongyishijia-skill.git \
    zhongyishijia-expert-mentor-lineage

cd zhongyishijia-expert-mentor-lineage
git branch --show-current   # 应输出: main
```

⚠️ **注意**:首次 git clone 会下载 books_json 206MB (LFS),需要 Git LFS 已安装。如果没装:
```bash
git lfs install    # 首次安装(只需一次)
```

### 2.3 家里 Windows (首次回家前)

**方案 A — 单位机先 bundle**(同上,Windows 上从 bundle 拉):

PowerShell:
```powershell
# 假设你用 U 盘把单位机的 bundle 目录拷到:
#   X:\hermes-skills-bundles\zhongyishijia-skill.git

cd $env:USERPROFILE\.hermes\skills\
git clone X:\hermes-skills-bundles\zhongyishijia-skill.git `
    zhongyishijia-expert-mentor-lineage

cd zhongyishijia-expert-mentor-lineage
git remote set-url origin https://github.com/erikgqp8645/zhongyishijia-skill.git
git branch --show-current   # 应输出: main
```

**方案 B — Windows 直接 git clone**:

PowerShell:
```powershell
mkdir $env:USERPROFILE\.hermes\skills\
cd $env:USERPROFILE\.hermes\skills\

git clone https://github.com/erikgqp8645/zhongyishijia-skill.git `
    zhongyishijia-expert-mentor-lineage

cd zhongyishijia-expert-mentor-lineage
git branch --show-current   # 应输出: main
```

⚠️ Windows 一次性配置:
```powershell
# 设置 git 身份(否则 commit author 错)
git config --global user.name "Erik"
git config --global user.email "41559617+erikgqp8645@users.noreply.github.com"

# 安装 Git LFS(如果要用 books_json)
git lfs install

# 如果有中文文件名乱码
git config --global core.quotepath off
```

─────────────────────────────────────────────────────

## 三、日常 SOP

### 3.1 单位机(主战场)

```bash
# 1. 进入工作目录
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/

# 2. 改文件
# (vim SKILL.md / 编辑 references/xxx.md)

# 3. 提交并推送
git status                              # 看改了什么
git add <改过的文件>                    # 显式 add,不用 -A
git commit -m "<一句话描述>"
git push                                # 直接 push 到 origin/main
```

### 3.2 家里 Mac (回家后)

```bash
# 1. 进入
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/

# 2. 拉取单位机的最新
git pull --rebase
# rebase 会自动把你的本地 commit 放到远端最新之上
# 如果 rebase 过程中有冲突,git 会要求你手动解决

# 3. 改文件
# 4. 提交
git add <files>
git commit -m "home-mac: <描述>"
git push
```

### 3.3 家里 Windows (回家后)

PowerShell:
```powershell
# 1. 进入
cd $env:USERPROFILE\.hermes\skills\zhongyishijia-expert-mentor-lineage\

# 2. 拉取最新
git pull --rebase

# 3. 改
# 4. 提交推送
git add <files>
git commit -m "home-win: <描述>"
git push
```

─────────────────────────────────────────────────────

## 四、回家 / 回单位前的强制检查

**重要习惯**:换机器前先跑这个脚本,确保没有遗留工作。

```bash
# 单位机下班前(出门前)
bash scripts/before_leaving.sh
# 输出应类似: ✅ All clean. Safe to switch machines.

# 家里机出门前(回单位前)
bash scripts/before_leaving.sh
```

如果脚本报告 ❌,**脚本会引导你 push 或 commit**,不要跳过这一步。

─────────────────────────────────────────────────────

## 五、可能遇到的问题 + 解决

### 问题 1:push 被拒绝(remote 领先)

```
! [rejected]        main -> main (fetch first)
```

**根因**:另一台机器刚 push 过,你的本地 main 不是最新。

**解决**:
```bash
# 方案 1:rebase(推荐,保留线性历史)
git pull --rebase
# 如果 rebase 冲突,git 会告诉你,解决后:
git add <冲突解决后的文件>
git rebase --continue
git push

# 方案 2:merge(产生 merge commit)
git pull
git push
```

### 问题 2:rebase 冲突

rebase 冲突时:
1. git 会标出冲突文件(`<<<<<<< HEAD`)
2. 手动编辑冲突文件,选留哪部分
3. `git add <冲突解决文件>`
4. `git rebase --continue`
5. 如果想放弃 rebase:`git rebase --abort`

### 问题 3:Windows CRLF 行尾污染

**症状**:`git diff` 显示文件全改了,行尾有 `^M`。

**未来方案**(待你确认要不要加):在仓库根目录加 `.gitattributes` 强制 LF。
```
* text=auto eol=lf
```

**临时解决**(如果已污染):
```bash
git rm --cached -r .
git reset --hard
# 应该看到所有文件以 LF checkout
```

### 问题 4:Git LFS 拉不到 books_json

```bash
# 首次需要安装 LFS
git lfs install

# 拉所有 LFS 对象
git lfs pull

# 检查 LFS 状态
git lfs ls-files
```

### 问题 5:忘记了某个机器的状态

**远程是事实来源**。在任何机器上:
```bash
git fetch origin
git log origin/main --oneline -10    # 看远端最新 10 个 commit
git log --oneline -5                 # 看本地最新 5 个 commit
```

如果本地落后:`git pull --rebase`。
如果本地领先(说明本地有未 push):`git push`。

─────────────────────────────────────────────────────

## 六、换机器前检查清单(纸质版,贴显示器上)

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   □ 出门前跑 bash scripts/before_leaving.sh         │
│   □ 输出 ✅ 才能放心换机器                          │
│                                                     │
│   □ 到家后第一件事: git pull --rebase               │
│   □ 上班后第一件事: git pull --rebase               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

─────────────────────────────────────────────────────

## 七、紧急恢复

### 误删了某个机器的本地仓库

不要慌,**远端是事实来源**:
```bash
# 重新 clone
git clone https://github.com/erikgqp8645/zhongyishijia-skill.git \
    <恢复到原路径>
```

### 误 commit 到 main 想撤回

```bash
# 撤回最近一次 commit(保留改动在工作区)
git reset --soft HEAD~1

# 撤回最近一次 commit(丢弃改动)
git reset --hard HEAD~1
```

**注意**:如果已经 push,需要 `git push --force-with-lease`(用 --force-with-lease 比 --force 安全,会检查远端没被别人改过)。

### 远端 main 出现异常 commit

```bash
# 1. 找出异常 commit 的前一个 SHA
git log origin/main --oneline -5

# 2. 强制回到那个 SHA
git reset --hard <好commit的SHA>
git push --force-with-lease origin main
```

─────────────────────────────────────────────────────

## 八、为什么不用 worktree(决策日志)

**2026-08-10**:试过 worktree 方案,3 个副 worktree 都在 `~/.hermes/skills/` 下 → Hermes skill loader 报 `Ambiguous skill name`,加载失败 → 移到 `~/.hermes/worktrees/` 修复 → 但仍是 4 个独立目录,books_json 206MB 重复 checkout 慢 + 3 个分支需要合并。

**评估**:对单人 3 机协作来说,worktree 是过度工程。直接 main 分支 + `git pull --rebase` 更适合这种场景。

**教训**:`git worktree` 适合**多分支并行开发**(开发新功能时独立 worktree),不适合**多机器同步同一分支**(用主仓库直接干)。

─────────────────────────────────────────────────────

## 九、一句话核心心法

**「三机一个 main,pull --rebase,出门前 bash scripts/before_leaving.sh,远端是事实来源」**

═══════════════════════════════════════════════