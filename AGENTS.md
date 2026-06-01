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

## 小步提交与实验隔离

后续开发必须避免长时间堆积未提交代码。每完成一个可以独立验证的小功能、修复或文档一致性更新，都应先运行相关测试并提交一个 checkpoint commit，再继续下一项工作。

推荐节奏：

1. 明确当前小目标及对应 spec / task 条目。
2. 只修改完成该小目标所需的文件。
3. 运行最小相关测试；影响面较大时运行全量测试。
4. 检查 `git diff --stat` 和 `git diff --check`。
5. 提交当前小目标，再进入下一轮修改。

如果单个未提交 diff 已经超过一个清晰功能边界，或出现大量跨层修改，必须暂停继续开发，先向用户汇报当前 diff 结构，提出拆分提交方案并等待确认。不要在没有 checkpoint 的情况下继续叠加调试修复。

探索性测试、浏览器自动化探针、合成音频、临时脚本、日志样本等必须与正式实现隔离。默认放入 `test-artifacts/`、`.voiceagents/` 或其他已忽略目录，不得和生产代码、正式测试用例混在同一个提交里。只有当用户明确要求保留为项目工具，并经过命名、文档和测试整理后，才允许纳入版本控制。

当真实环境验证发现 spec、tasks 或实现可能偏离时，先做根因分析并记录偏离点，不要边测试边扩大实现范围。若需要修改 spec 或改变验收口径，应先汇报影响和修复方案，用户确认后再实施。

提交前必须确认：

- 不包含 `.env`、API key、client secret、tool token、原始音频、SDP、Authorization header 等敏感信息。
- 不包含临时大文件或只为本地调试服务的二进制资产。
- 测试结果和提交内容匹配，不能把未验证的大范围改动混入小提交。
