# Phase 6: 正文提取修复 - Summary

**Completed:** 2026-05-17
**Files modified:** step6.py

## What was built

修复 step6.py 正文提取策略链中的5类污染，使输出正文干净可用。

### Key changes

| Function | Purpose |
|----------|---------|
| `_preprocess_html(html)` | 在层1/2/4提取前剥离 `<script>` 和 `<style>` 块（层3 ckxx除外——内容在JS变量中） |
| `_postprocess_text(text)` | HTML实体解码 + 视频标记清理 + 播放器UI文字清理 + 段落去重 |
| `_is_contaminated(text)` | 检测CSS、JS、导航垃圾信号 |
| `_aggressive_clean(html, url)` | 二次重试：HTML注释剥离 + inline style剥离（ckxx跳过） |

### E2E results (2026-05-17 data)

| Article | Before | After | Verdict |
|---------|--------|-------|---------|
| 参考消息（DNA进化） | JS混入（`var ih`） | 1241字，干净 | ✅ |
| 央视新闻（天宫日志） | 视频标记+重复+实体 | 657字，干净 | ✅ |
| 央视军事（火箭炮训练） | 459字，成功 | 459字，成功 | ✅ |
| 人民日报（贵州农业） | CSS+导航污染 | 1641字，干净 | ✅ |
| 人民日报（能源强国）×2 | CSS+导航污染 | 2071字，干净 | ✅ |
| 参考消息（国防培训） | JS混入 | 663字，干净 | ✅ |
| 中科院（天津工生所） | 1430字，成功 | 1430字，成功 | ✅ |
| 央视军事（火箭禁止） | 提取失败 | 提取失败 | ⚠ 预期 |
| 参考消息（医疗创新） | 提取失败 | 提取失败 | ⚠ 预期 |

### Quality verification

- ✅ 无 JS 代码污染
- ✅ 无 CSS 样式污染
- ✅ 无 HTML 实体未解码
- ✅ 无视频播放器标记/UI文字
- ✅ 无重复段落
- ✅ 输出格式不变（下游 step7.py 无需修改）

### Requirements covered

- EXT-01: 提取前剥离 script/style ✅
- EXT-02: HTML实体解码 ✅
- EXT-03: 视频标记/播放器UI清理 ✅
- EXT-04: 污染检测+重试回退 ✅
- EXT-05: 人民日报专用提取策略 ✅
