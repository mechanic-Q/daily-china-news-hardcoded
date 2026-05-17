# Project Instructions for AI Agents

## 分支策略（自 Phase 6 起）

每个 GSD phase 的 discuss 阶段开头，必须先创建 feature 分支：

```bash
git checkout -b phase-{NN}-{name}
```

例如 Phase 7 讨论开头：`git checkout -b phase-07-column-balance`

所有 plan/execute/verify 的 commits 在该分支上进行。ship 时 push → `gh pr create` → merge，然后切回 main 继续。
