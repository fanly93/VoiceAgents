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
