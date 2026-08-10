#!/usr/bin/env bash
# before_leaving.sh — 出门前 git 状态检查脚本
#
# 用途: 换机器(回家/回单位)前检查 git 工作树干净,
#        且本地 commit 都已 push 到 origin/main。
#        防止「改完忘了 push」或「有未提交改动」。
#
# 适用: zhongyishijia-skill 多机协作(单位 Mac / 家里 Mac / 家里 Windows)
#
# 用法:
#   bash scripts/before_leaving.sh           # 检查模式(只报告,不修改)
#   bash scripts/before_leaving.sh --fix     # 检查 + 自动修复(未 push 的 commit 提示 push)

set -euo pipefail

# 颜色(在不支持 ANSI 颜色的终端会输出原始字符,但不影响判断)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 解析参数
FIX_MODE=false
for arg in "$@"; do
    case "$arg" in
        --fix) FIX_MODE=true ;;
        --help|-h)
            echo "用法: bash scripts/before_leaving.sh [--fix]"
            echo ""
            echo "  (无参数) 检查模式:只报告问题,不修改"
            echo "  --fix      修复模式:发现未 push 的 commit 会自动 git push"
            echo ""
            echo "退出码:"
            echo "  0 = 一切干净,可以放心换机器"
            echo "  1 = 有问题需要处理"
            exit 0
            ;;
        *)
            echo "未知参数: $arg"
            echo "用法: bash scripts/before_leaving.sh [--help|--fix]"
            exit 2
            ;;
    esac
done

# 必须在 git 仓库里
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo -e "${RED}❌ 错误: 当前目录不是 git 仓库${NC}"
    echo "请在 zhongyishijia-expert-mentor-lineage 仓库根目录运行此脚本"
    exit 1
fi

# 当前分支
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo -e "${RED}❌ 错误: 当前分支是 '$BRANCH',不是 main${NC}"
    echo "本脚本只检查 main 分支状态。请先:"
    echo "  git checkout main"
    exit 1
fi

echo "=========================================="
echo "  before_leaving.sh — 出门前 git 状态检查"
echo "  仓库: $(git rev-parse --show-toplevel)"
echo "  分支: $BRANCH"
echo "  HEAD: $(git rev-parse --short HEAD)"
echo "=========================================="
echo ""

# 检查 1:working tree 是否有未提交的改动
echo -e "${YELLOW}[检查 1/3]${NC} 未提交的改动..."
if [ -z "$(git status --porcelain)" ]; then
    echo -e "  ${GREEN}✅ working tree 干净${NC}"
else
    echo -e "  ${RED}❌ 有未提交的改动:${NC}"
    git status --short | sed 's/^/    /'
    echo ""
    echo -e "  ${YELLOW}提示:${NC} 处理方式:"
    echo "    - 想保留:  git add <文件> && git commit -m \"<描述>\""
    echo "    - 想丢弃:  git restore <文件>"
    echo ""
    EXIT_CODE=1
fi
echo ""

# 检查 2:本地是否有未 push 的 commit
echo -e "${YELLOW}[检查 2/3]${NC} 未 push 的 commit..."
# 先 fetch,确保本地知道远端最新
echo "  正在 fetch origin/main..."
git fetch origin main --quiet 2>&1 || {
    echo -e "  ${RED}❌ git fetch 失败(可能是网络问题)${NC}"
    exit 1
}

UNPUSHED=$(git log origin/main..HEAD --oneline 2>/dev/null || true)
if [ -z "$UNPUSHED" ]; then
    echo -e "  ${GREEN}✅ 本地所有 commit 都已 push 到 origin/main${NC}"
else
    N=$(echo "$UNPUSHED" | wc -l | tr -d ' ')
    echo -e "  ${RED}❌ 有 $N 个 commit 未 push:${NC}"
    echo "$UNPUSHED" | sed 's/^/    /'
    echo ""

    if [ "$FIX_MODE" = true ]; then
        echo -e "  ${YELLOW}--fix 模式: 自动 git push origin main${NC}"
        git push origin main
        echo -e "  ${GREEN}✅ push 完成${NC}"
    else
        echo -e "  ${YELLOW}提示:${NC} 运行 'git push origin main' 推送,或重新运行本脚本加 --fix"
    fi
    echo ""
    EXIT_CODE=1
fi
echo ""

# 检查 3:本地是否落后于远端
echo -e "${YELLOW}[检查 3/3]${NC} 本地是否落后 origin/main..."
AHEAD=$(git log HEAD..origin/main --oneline 2>/dev/null || true)
if [ -z "$AHEAD" ]; then
    echo -e "  ${GREEN}✅ 本地与 origin/main 同步${NC}"
else
    N=$(echo "$AHEAD" | wc -l | tr -d ' ')
    echo -e "  ${YELLOW}⚠  本地落后 origin/main $N 个 commit:${NC}"
    echo "$AHEAD" | sed 's/^/    /'
    echo ""
    echo -e "  ${YELLOW}提示:${NC} 运行 'git pull --rebase' 同步"
    echo ""
    # 落后不阻断出门(回家后 pull 就行),不设 EXIT_CODE
fi
echo ""

# 总结
echo "=========================================="
if [ "${EXIT_CODE:-0}" = "0" ]; then
    echo -e "  ${GREEN}✅ All clean. Safe to switch machines.${NC}"
    echo ""
    echo "  下一步:"
    echo "    - 出门/回家切换机器"
    echo "    - 到新机器第一件事: cd <仓库路径> && git pull --rebase"
else
    echo -e "  ${RED}❌ 有问题需要处理(见上文)${NC}"
    echo ""
    echo "  修复方式:"
    echo "    1. 处理未提交的改动 (commit 或 restore)"
    echo "    2. git push origin main  (推送未 push 的 commit)"
    echo "    3. git pull --rebase     (拉取远端最新,通常回家后做)"
    echo ""
    echo "  或者: bash scripts/before_leaving.sh --fix  自动 push"
fi
echo "=========================================="

exit "${EXIT_CODE:-0}"