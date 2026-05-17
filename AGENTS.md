# Project Instructions for AI Agents

## 分支策略（自 Phase 6 起）

每个 GSD phase 的 discuss 阶段开头，必须先创建 feature 分支：

```bash
git checkout -b phase-{NN}-{name}
```

例如 Phase 7 讨论开头：`git checkout -b phase-07-column-balance`

所有 plan/execute/verify 的 commits 在该分支上进行。ship 时 push → `gh pr create` → merge，然后切回 main 继续。

## 分支自动检测

每次 GSD phase 的 discuss 阶段，在进入灰色地带讨论前（present_gray_areas），检测当前 git 分支：

- 如果在 `main` 上 → 自动 `git checkout -b phase-{NN}-{slug}`
- 如果已在 feature 分支上 → 正常继续

这确保即使忘记手动建分支，workflow 也能自动补救。
