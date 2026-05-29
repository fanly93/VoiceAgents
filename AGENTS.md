# 项目说明

## gstack 使用

本项目使用项目级 gstack，安装在 `.agents/skills/` 下，不使用用户级 `~/.codex/skills/gstack*`。

优先调用生成后的 Codex skills：

- `$gstack-office-hours`
- `$gstack-browse`
- `$gstack-qa`
- `$gstack-review`
- `$gstack-autoplan`

不要调用根 `$gstack`。`.agents/skills/gstack` 是运行时目录和源码 checkout，根 `SKILL.md` 偏 Claude 路径；`$gstack-*` 才是 Codex 兼容入口。

本目录必须保持为 git repo，gstack 依赖 `git rev-parse --show-toplevel` 定位项目级 runtime。若失效，先确认：

```bash
git rev-parse --show-toplevel
```

手动运行 gstack 命令时使用项目级环境，避免写入用户级目录：

```bash
env HOME="$PWD/.gstack-home" GSTACK_HOME="$PWD/.gstack" GSTACK_STATE_DIR="$PWD/.gstack" PATH="$PWD/.bun/bin:$PATH" <gstack-command>
```

`$gstack-browse` 需要绑定 localhost；在 Codex 沙箱中可能需要申请非沙箱执行。

完整验证记录和排障细节见 `problems/gstack-project-local-usage-2026-05-28.md`。

## 分支开发规范

后续每个新需求必须从干净的 `main` 新建 feature branch 开发，不要直接在 `main` 上继续实现需求。

推荐流程：

```bash
git switch main
git pull --ff-only
git switch -c feat/<short-feature-name>
```

原因：`$gstack-review` 按“当前分支 vs base branch”审查 diff。若直接在已同步的 `main` 上开发并推送，标准 review 会显示没有分支差异，无法自然完成 PR 前置审查。

每个需求应在独立分支内完成：

1. 需求澄清 / spec / task 拆分
2. 代码实现与测试
3. `$gstack-review`
4. 修复 review findings
5. push / PR / merge

`$gstack-review` 必须在开发分支仍存在、且合并到 `main` 之前运行。它依赖“当前分支 vs base branch”的 diff；如果已经合并并同步到 `main`，标准 review 会没有分支差异，不能作为 PR 前置审查。

合并后如需收口，使用文档归档/一致性校验流程：检查 docs/spec/task/README 与实际实现、测试证据、安全边界和 out-of-scope 是否一致。此类检查可以补充 `$gstack-document-release`，但不能替代 merge 前的 `$gstack-review`。

在进入归档或下一阶段前，建议主动询问用户是否需要做一次一致性校验。
