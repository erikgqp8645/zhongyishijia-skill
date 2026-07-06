[根目录](../../CLAUDE.md) > **agents**

# agents — Agent 适配器

> **职责**：为不同 Agent runtime 提供 lineage-skill 兼容的接口声明。
> **状态**：已生成（v1.0）。

---

## 模块职责

把本 skill 暴露给不同 Agent 平台的标准接口（OpenAI/Codex 与 OpenClaw），每个 YAML 文件描述：

- 显示名 / 短描述
- 默认 prompt（如何调用本 skill）
- 权限策略（是否允许隐式调用）

---

## 文件清单

| 文件 | 平台 | 大小（约） | 说明 |
|------|------|-----------:|------|
| `openai.yaml` | OpenAI / Codex / GPT | 0.4 KB | `interface.display_name` + `policy.allow_implicit_invocation: true` |
| `openclaw.yaml` | OpenClaw | 0.7 KB | 同上 + Trust surface 注释（说明本 skill 只读 references + 运行本地脚本） |

---

## 入口与启动

两个 YAML 都是声明性配置，**没有可执行入口**。它们被对应平台的 Agent runtime 加载，决定：

1. Skill 在 UI 中如何显示（`display_name` / `short_description`）
2. 默认调用方式（`default_prompt`）
3. 是否允许 Agent 在不显式调用的情况下隐式触发（`allow_implicit_invocation`）

---

## 对外接口

### openai.yaml 接口契约

```yaml
interface:
  display_name: "zhongyishijia Course Skill"
  short_description: "Source-grounded course Q&A, review, and workflows."
  default_prompt: "Use $zhongyishijia-expert-mentor-lineage to answer questions about zhongyishijia and cite the course sources."

policy:
  allow_implicit_invocation: true
```

### openclaw.yaml 接口契约

```yaml
interface:
  display_name: "zhongyishijia Course Skill"
  short_description: "Source-grounded course Q&A, review, and workflows."
  default_prompt: "Use zhongyishijia-expert-mentor-lineage to answer questions about zhongyishijia and cite the course sources."
```

OpenClaw 版本额外包含 Trust surface 注释（YAML 注释），声明本 skill 的可信操作边界。

---

## 关键依赖与配置

- **依赖**：对应的 Agent runtime（OpenAI / Codex / OpenClaw）
- **不依赖**：Python 包、SQLite、网络

---

## 测试与质量

无自动测试。两个 YAML 的正确性靠对应 Agent runtime 的加载校验保证：

- OpenAI/Codex：通过 `codex` CLI 加载验证
- OpenClaw：通过 `openclaw` CLI 加载验证

---

## 常见问题 (FAQ)

**Q: 为什么没有 `claude.yaml`？**
A: Claude 通过根目录的 `SKILL.md` 与 `CLAUDE.md` 自动识别 lineage-skill 格式，不需要单独的 YAML 适配。

**Q: `allow_implicit_invocation: true` 的风险？**
A: Agent 可能未经用户明确请求就调用本 skill。若不希望此行为，改为 `false`。

---

## 相关文件清单

- [`../SKILL.md`](../SKILL.md) — Agent 通用入口描述
- [`../README.md`](../README.md) — 人类开发者入口
- [`../lineage_manifest.json`](../lineage_manifest.json) — 元数据（声明 roles: expert + mentor）

---

## 变更记录 (Changelog)

### 2026-07-06
- 新增本模块 CLAUDE.md
- 无代码改动