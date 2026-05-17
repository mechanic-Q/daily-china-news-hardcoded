---
status: complete
phase: 05-newspaper-render
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md
started: 2026-05-17T12:00:00Z
updated: 2026-05-17T13:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. step8.py 生成报纸
expected: 运行 step8.py 传入合法日期，生成 HTML + PNG 输出文件。
result: pass

### 2. 报纸报头与期号
expected: 生成的报纸顶部显示"每日新中国"标题、红色标语"中国很大 我想去看看"、右上角日期+期号（从2026-04-19起算）。
result: pass

### 3. 双栏布局与内容平衡
expected: 报纸主体为左/右双栏，新闻按栏目分组显示，左右栏内容量大致平衡。
result: pass

### 4. 八个栏目正确显示
expected: 报纸包含全部8个栏目：科研/农业/扶贫/能源/医疗/科技/材料/军事，每个有内容的栏目各占一个区块。
result: pass

### 5. 空栏目不渲染
expected: 没有新闻内容的栏目不出现在报纸上。
result: pass

### 6. PNG 截图质量
expected: 生成的 PNG 为 2x 分辨率（~2200px 宽），白边已裁剪，画面干净无多余空白。
result: pass

### 7. --dry-run 模式
expected: 传入 --dry-run 时生成 HTML 但跳过截图，终端明确提示"截图已跳过"。
result: pass

### 8. run_all.sh 全管道串联
expected: `bash run_all.sh --date 2026-05-14` 依次执行 step1_3→step4→step6→step7→step8，最后一行打印"✅ 全管道完成"。
result: pass

### 9. run_all.sh 参数校验
expected: 无 --date 时默认今天；--date 传无效日期时报错退出。
result: pass

### 10. run_all.sh 失败即停
expected: 中间某步失败（如 API 调用出错）时立即停止，不继续执行后续步骤。
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
