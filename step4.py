#!/usr/bin/env python3
"""
Step 4: 栏目分类筛选 — 从 0新闻_粗筛.md 生成 1新闻_链接.md
读取 step1_3.py 的输出，按 9 栏目分类 → 质量过滤 → 优先级排序 → 精选输出

用法:
    python3 step4.py                      # 处理今天
    python3 step4.py --date 2026-05-10     # 处理指定日期
    python3 step4.py --dry-run              # 预览，不写文件
"""

import datetime
import json
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from llm_client import call_llm, LLMCallError
from news_archive import normalize_url

from daily.common import BASE_DIR, COLUMN_ORDER, parse_common_args as parse_args, detect_source, clean_news_title

WORLD_CLASS_THRESHOLD = 7
WORLD_CLASS_CATEGORY = '🔬 世界性科研突破'
AGG_RELEV_BASE = 0.5
AGG_IMP_W = 0.3
AGG_TIME_W = 0.2

HIGH_CONFIDENCE_MIN_SCORE = 6
HIGH_CONFIDENCE_MARGIN = 3

LLM_BATCH_SIZE = 20

EXCLUDE_TITLES = [
    '春雨落', '百谷生', '谷雨', '舞蹈诗剧', '三月三', '时装周',
    'DELVAUX', '世界超级摩托车', '节气', '立夏', '立春', '立冬',
    '冬至', '夏至', '春分', '秋分', '惊蛰', '芒种', '白露',
    '寒露', '霜降', '小满',
    '娱乐', '明星', '八卦', '综艺', '影视', '网剧', '歌星',
    '演唱会', '直播', '网红', '选秀', '真人秀',
]

EXCLUDE_NEGATIVE = [
    '审查调查', '违纪违法', '纪律审查', '监察调查', '落马', '双开',
    '接受审查', '涉嫌严重',
]

DIPLOMATIC_PROTOCOL = [
    '会见', '访问', '出席', '接见', '晤', '磋商', '峰会', '联合声明', '公报',
]

OUTLOOK_WORDS = [
    '有较好基础', '稳中向好', '稳步推进', '总体平稳', '稳定',
    '扩量提质', '可靠替代', '形势',
]

OUTLOOK_RESCUE_WORDS = [
    '印发', '实施', '启动', '部署', '工程', '规划', '计划', '项目', '方案',
]

NON_RESEARCH_TITLES = [
    '灾害', '调查评估', '溃坝', '规划', '权威发布',
    '公报', '会见', '声明',
]

FRONTIER_DOMAIN_WORDS = [
    '光刻机', 'EUV', '先进制程', '刻蚀机', 'EDA', 'AI芯片', '存储芯片',
    '大飞机', '航空发动机', '涡扇', 'C919', 'C929',
    '大模型', '算力', 'GPU', '训练集群', '光模块',
    '核聚变', '人造太阳', '第四代核电', '高温气冷堆',
    '量子计算机', '量子通信', '量子芯片',
    '高铁', '数控机床', '工业软件', '工业机器人',
    '空间站', '探月', '探火', '重型运载',
    '商业航天', '新能源电池', '固态电池', '高端医疗',
    '合成生物', '人工合成', '基因编辑', '脑机接口',
]

B2_ACHIEVEMENT_WORDS = [
    '全产业链', '规模化量产', '国产化', '自主可控',
    '打破封锁', '不再依赖', '国产替代',
    '首次', '首例', '世界首', '全球首', '攻克',
    '填补空白', '研制成功', '颠覆', '下线', '投产', '实现量产',
    '全栈',
]

B2_ROUTINE_WORDS = [
    '交付', '年度',
]

A_BODY_SIGNALS = [
    '世界首次', '全球首次', '世界首例', '全球首例',
    '首例', '发表', '期刊', '论文',
    '克隆效率', '一系法', '研制成功', '填补空白',
]

BODY_FETCH_TIMEOUT = 15

CHINA_KEYWORDS = [
    '习近平', '总书记',
    '中国', '我国', '国产', '中华', '中方', '在华', '访华', '驻华', '对华', '涉华',
    '中央', '纪委', '监委', '国务院',
    '全国政协', '全国人大', '十四届',
    '商务部', '外交部', '国防部', '工信部', '公安部',
    '解放军', '武警',
    '中美', '中俄', '中非', '中日', '中欧', '中法', '中德', '中英', '中韩',
    '中越', '中澳', '中巴', '中阿', '两岸',
    '北京', '上海', '深圳', '广东', '浙江', '江苏', '山东', '四川', '河南',
    '湖北', '湖南', '河北', '福建', '安徽', '辽宁', '陕西', '云南', '贵州',
    '广西', '山西', '吉林', '黑龙江', '江西', '重庆', '天津',
    '内蒙古', '新疆', '甘肃', '海南', '宁夏', '青海', '西藏',
    '香港', '澳门',
    '南海', '台海',
    '神舟', '天宫', '嫦娥', '长征', '北斗',
    '南水北调', '一带一路', '大湾区',
    '乡村振兴', '扶贫', '脱贫', '共同富裕',
    '中科院', '工程院',
    '十五五', '十四五',
    '两会',
]

CHINA_DOMAINS = [
    'xinhuanet.com', 'news.cn', 'people.com.cn', 'cctv.com',
    'chinanews.com', 'china.com.cn', 'ce.cn', 'cnr.cn',
    'gmw.cn', 'youth.cn', 'cas.cn',
    'cnnpn.cn', 'cnnc.com',
    'ckxxapp.ckxx.net', 'cankaoxiaoxi.com',
]


def is_china_related(title):
    for kw in CHINA_KEYWORDS:
        if kw in title:
            return True
    return False


def is_china_source(url):
    for domain in CHINA_DOMAINS:
        if domain in url:
            return True
    return False


def llm_is_china_related(title):
    try:
        from llm_client import call_llm
        ans = call_llm(
            "china-relevance",
            messages=[{"role": "user", "content": f"判断以下新闻标题内容主体上是否直接与中国相关（报道或讨论中国事务/中国人/中国企业/中国政府/中美关系等）。只回答\"是\"或\"否\"。\n\n标题：{title}"}],
            extra_body={"reasoning_effort": "none"},
        )
        return ans.strip().startswith("是")
    except Exception:
        import traceback
        traceback.print_exc()
        return False


def _strip_llm_json(raw):
    """去除 think 块和 markdown fence，返回可 json.loads 的字符串。"""
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()


def _extract_json_array(raw):
    """从 LLM 返回文本中提取第一个 JSON 数组，容忍前后说明文字。"""
    if not raw or not raw.strip():
        raise ValueError("empty LLM response")
    raw = _strip_llm_json(raw)
    if raw.startswith('['):
        return json.loads(raw)
    m = re.search(r'\[.*?\]', raw, re.DOTALL)
    if m:
        return json.loads(m.group())
    return json.loads(raw)


def _parse_china_json_array(raw: str, expected_count: int) -> list[bool]:
    parsed = _extract_json_array(raw)
    if not isinstance(parsed, list):
        raise ValueError("china batch 返回非列表")
    result_map = {}
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError(f"china batch item 非对象: {item!r}")
        idx = item.get("index")
        val = item.get("is_china_related")
        if type(idx) is not int or type(val) is not bool:
            raise ValueError(f"类型错误: index={idx!r}, is_china_related={val!r}")
        if idx < 0 or idx >= expected_count:
            raise ValueError(f"index {idx} 超出范围 [0, {expected_count})")
        if idx in result_map:
            raise ValueError(f"重复 index: {idx}")
        result_map[idx] = val
    if len(result_map) != expected_count:
        raise ValueError(f"缺项: 期望 {expected_count} 项，收到 {len(result_map)} 项")
    return [result_map[i] for i in range(expected_count)]


def _parse_score_json_array(raw: str, expected_count: int) -> list[dict]:
    parsed = _extract_json_array(raw)
    if not isinstance(parsed, list):
        raise ValueError("score batch 返回非列表")
    result_map = {}
    for item in parsed:
        if not isinstance(item, dict):
            raise ValueError(f"score batch item 非对象: {item!r}")
        idx = item.get("index")
        if type(idx) is not int:
            raise ValueError(f"index 类型错误: {idx!r}")
        if idx < 0 or idx >= expected_count:
            raise ValueError(f"index {idx} 超出范围 [0, {expected_count})")
        if idx in result_map:
            raise ValueError(f"重复 index: {idx}")
        signals = {
            "relevance": item.get("relevance"),
            "importance": item.get("importance"),
            "timeliness": item.get("timeliness"),
        }
        if not _validate_signals(signals):
            raise ValueError(f"signals schema 不完整: index={idx}")
        result_map[idx] = signals
    if len(result_map) != expected_count:
        raise ValueError(f"缺项: 期望 {expected_count} 项，收到 {len(result_map)} 项")
    return [result_map[i] for i in range(expected_count)]


def _chunks(items, size):
    """按固定大小切分 list。"""
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _normalized_event_title(title):
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]+', '', unicodedata.normalize('NFKC', title).lower())


def _is_duplicate_candidate(a, b):
    if a.get('date') != b.get('date'):
        return False
    left_url = normalize_url(a.get('url', ''))
    right_url = normalize_url(b.get('url', ''))
    if left_url and left_url == right_url:
        return True
    left = _normalized_event_title(a['title'])
    right = _normalized_event_title(b['title'])
    if left == right:
        return True
    left_pairs = {left[i:i + 2] for i in range(len(left) - 1)}
    right_pairs = {right[i:i + 2] for i in range(len(right) - 1)}
    overlap = len(left_pairs & right_pairs) / len(left_pairs | right_pairs) if left_pairs and right_pairs else 0
    longest = SequenceMatcher(None, left, right).find_longest_match().size
    return overlap >= 0.3 or longest >= 8


def find_duplicate_candidate_groups(articles):
    """返回疑似同事件的索引组；只发现候选，不在此处删除。"""
    links = {i: set() for i in range(len(articles))}
    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            if _is_duplicate_candidate(articles[i], articles[j]):
                links[i].add(j)
                links[j].add(i)

    groups = []
    seen = set()
    for start, neighbours in links.items():
        if start in seen or not neighbours:
            continue
        stack = [start]
        group = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            group.append(current)
            stack.extend(links[current] - seen)
        groups.append(sorted(group))
    return groups


def llm_review_duplicate_candidates(articles, candidate_groups):
    """让 LLM 复核疑似组；只删除 LLM 明确判为同一事件的条目。"""
    removed = set()
    audit = []
    for candidates in candidate_groups:
        prompt = (
            "判断以下疑似新闻是否报道同一具体事件。只有主体、对象、动作、核心数据和时间共同指向同一事实才可合并。"
            "同类型不等于同一事件；主体不同（例如不同人物逝世、不同机构发布）必须保留为独立事件。"
            "可拆成多个重复组；独立事件不要列入。只输出 JSON 对象，duplicate_groups 每项包含 indices、keep、reason。\n\n"
            + "\n".join(f"[{local}] {articles[global_i]['title']}" for local, global_i in enumerate(candidates))
            + '\n\nJSON格式：{"duplicate_groups":[{"indices":[0,1],"keep":0,"reason":"共同事实"}]}'
        )
        raw = call_llm(
            "event-dedup",
            messages=[
                {"role": "system", "content": "你只能输出 JSON 对象，不要输出 markdown 或其他文字。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            extra_body={"reasoning_effort": "none"},
        )
        try:
            parsed = json.loads(_strip_llm_json(raw))
        except (TypeError, json.JSONDecodeError) as e:
            raise ValueError(f"event-dedup JSON 无效: {e}") from e
        groups = parsed.get('duplicate_groups') if isinstance(parsed, dict) else None
        if not isinstance(groups, list):
            raise ValueError("event-dedup 返回缺少 duplicate_groups 列表")
        used = set()
        for group in groups:
            indices = group.get('indices') if isinstance(group, dict) else None
            keep = group.get('keep') if isinstance(group, dict) else None
            reason = group.get('reason') if isinstance(group, dict) else None
            if (not isinstance(indices, list) or len(indices) < 2
                    or any(type(i) is not int or i not in range(len(candidates)) for i in indices)
                    or type(keep) is not int or len(set(indices)) != len(indices) or keep not in indices
                    or not isinstance(reason, str) or not reason.strip()
                    or used.intersection(indices)):
                print(f"⚠ event-dedup schema 无效，跳过该组: {group!r}", file=sys.stderr)
                continue
            used.update(indices)
            global_indices = [candidates[i] for i in indices]
            global_keep = candidates[keep]
            dropped = [i for i in global_indices if i != global_keep]
            removed.update(dropped)
            audit.append({
                "indices": global_indices,
                "keep": global_keep,
                "removed": dropped,
                "reason": reason.strip(),
            })
    return [article for i, article in enumerate(articles) if i not in removed], audit


def llm_is_china_related_batch(articles):
    """批量涉华判断；返回通过涉华判断的 article 列表，失败时按 batch 回退单条 llm_is_china_related。"""
    confirmed = []
    batch_disabled = False
    for batch in _chunks(articles, LLM_BATCH_SIZE):
        if batch_disabled:
            for a in batch:
                if llm_is_china_related(a['title']):
                    confirmed.append(a)
            continue

        batch_titles = [a['title'] for a in batch]
        prompt_lines = [f"[{i}] {title}" for i, title in enumerate(batch_titles)]
        prompt = (
            "判断以下新闻标题是否与中国相关（报道或讨论中国事务/中国人/中国企业/中国政府/中美关系等）。"
            "返回 JSON 数组，每项包含 index 和 is_china_related（布尔值）。\n"
            "只输出 JSON 数组，不要输出解释、markdown 或空内容。\n\n"
            + "\n".join(prompt_lines) +
            '\n\nJSON格式：\n[{"index": 0, "is_china_related": true}, ...]'
        )

        results = None
        last_error = None
        for attempt in range(2):
            try:
                from llm_client import call_llm
                raw = call_llm(
                    "china-relevance",
                    messages=[
                        {"role": "system", "content": "你只能输出 JSON 数组，不要输出任何其他文字。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    extra_body={"reasoning_effort": "none"},
                )
                if os.environ.get('DEBUG_LLM_BATCH'):
                    print(f"  [DEBUG china-relevance batch] raw[:200]: {raw[:200]!r}")
                results = _parse_china_json_array(raw, len(batch))
                break
            except Exception as e:
                last_error = e
                if attempt == 0:
                    print("  ⚠ batch 涉华判断 JSON 解析失败，重试一次")

        if results is not None:
            for i, a in enumerate(batch):
                if results[i]:
                    confirmed.append(a)
            continue

        print(f"  ⚠ batch 涉华判断不可用，本轮改用单条 fallback: {last_error}")
        batch_disabled = True
        for a in batch:
            if llm_is_china_related(a['title']):
                confirmed.append(a)
    return confirmed


def parse_0(path, today):
    if not path.exists():
        print(f"文件不存在: {path}")
        return []
    content = path.read_text("utf-8")
    articles = []
    today_str = today.strftime("%Y-%m-%d")
    for m in re.finditer(r'- \[(.*?)\] (.*?) \| (https?://[^\s]+) ([✅❌])', content):
        date = m.group(1).strip()
        title = m.group(2).strip()
        url = m.group(3).strip()
        if m.group(4) == '✅' and date == today_str:
            title = clean_news_title(title)
            articles.append({"date": date, "title": title, "url": url})
    return articles


def is_quality_news(title):
    for kw in EXCLUDE_TITLES:
        if kw in title:
            return False
    for kw in EXCLUDE_NEGATIVE:
        if kw in title:
            return False
    return True


def _is_conditional_excluded(title, trigger_words, rescue_words=None, rescue_categories=None):
    """条件排除:命中 trigger_words 且不命中 rescue -> True.
    - rescue_words: title中需匹配的挽救词(任一命中即不剔除)
    - rescue_categories: title命中任一栏目关键词则不剔除
    二者至少提供一个;都提供时任一满足即不剔除。
    """
    if not any(kw in title for kw in trigger_words):
        return False
    if rescue_words:
        if any(kw in title for kw in rescue_words):
            return False
    if rescue_categories:
        scores = score_all_categories(title)
        if any(scores.get(cat, 0) > 0 for cat in rescue_categories):
            return False
    return True


def _is_non_research_title(title):
    """True 表示标题命中非科研模式,不应通过世突 override"""
    return any(kw in title for kw in NON_RESEARCH_TITLES)


def _is_b2_breakthrough(title):
    """B2 单国全链突破 = 前沿域 ∧ 成就词(信号∪里程碑) ∧ ¬例行"""
    if not any(kw in title for kw in FRONTIER_DOMAIN_WORDS):
        return False
    if not any(kw in title for kw in B2_ACHIEVEMENT_WORDS):
        return False
    if any(kw in title for kw in B2_ROUTINE_WORDS):
        return False
    return True


def _fetch_page_text(url):
    """获取网页纯文本(HTML tag stripped),用于正文信号检测。
    失败时返回 None(静默,不阻塞 pipeline)。"""
    import urllib.request
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 10)',
                     'Accept': 'text/html, */*',
                     'Accept-Language': 'zh-CN,zh;q=0.9'},
        )
        with urllib.request.urlopen(req, timeout=BODY_FETCH_TIMEOUT) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        import re
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'&[a-z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:5000]
    except Exception:
        return None


CATEGORY_KEYWORDS = {
    '🔬 世界性科研突破': {
        '诺贝尔': 5, '世界首次': 5, '全球首次': 5, '首次发现': 5,
        '基因': 4, '量子': 4, '干细胞': 4, 'iPS': 4, '重编程': 4,
        'p53': 4, '化学小分子': 4, '考古发现': 4, '考古': 3,
        '嫦娥': 3, '天宫': 3, '火星': 3, '月球': 3, '宇宙': 3,
        '一系法': 3, '克隆': 3, '首例': 4, '杂交水稻': 3,
        '实体清单': 5, '瓦森纳': 5,
        '卡脖子': 4, '断供': 4, '出口管制': 4, '禁运': 4, '国产替代': 4,
        '封锁': 3, '自主可控': 3, '期刊': 2,
        '发现': 2,
        '研究': 1, '实验': 1, '论文': 1,
        '航天': 1, '卫星': 1, '探测': 1, '火箭发射': 1,
        '水稻': 1, '育种': 1,
    },
    '🤖 AI智能前沿': {
        '人工智能': 5, '大模型': 5, 'AI': 5, 'ChatGPT': 5, 'GPT': 5,
        'DeepSeek': 5, '通义千问': 5, '文心一言': 5, '豆包': 5,
        '智谱': 4, 'GLM': 4, 'LLM': 4, '多模态': 4,
        '机器学习': 4, '深度学习': 4, '神经网络': 4,
        '强化学习': 4, 'Transformer': 4, '扩散模型': 4,
        'AIGC': 3, '生成式': 3, '自动驾驶': 3, '智能体': 3,
        'AI Agent': 3, 'RAG': 3, '向量': 2, '语义': 2,
        '认知': 2, '算法': 2, '训练': 1, '推理': 1,
    },
    '🌾 农业': {
        '农业': 3, '粮食': 3, '农产品': 3, '农田': 3,
        '玉米': 2, '小麦': 2, '春播': 2, '春耕': 2, '育秧': 2,
        '农机': 2, '种业': 2, '耕地': 2, '畜牧': 2,
        '治沙': 2, '农村': 1, '蔬菜': 1, '水果': 1,
        '种植': 1, '养殖': 1, '渔业': 1, '生态': 1,
        '水稻': 2, '杂交稻': 2, '育种': 2, '稻': 1,
    },
    '🤝 扶贫': {
        '精准扶贫': 5, '易地搬迁': 4, '扶贫': 4, '脱贫': 4,
        '对口帮扶': 3, '消费扶贫': 3, '驻村书记': 3,
        '乡村振兴': 3, '巩固脱贫': 3, '乡村产业': 2,
        '农村人居': 2, '和美乡村': 2, '乡村建设': 2,
    },
    '⚡ 能源': {
        '核电': 4, '核能': 4, '人造太阳': 4,
        '光伏': 3, '风电': 3, '氢能': 3, '能源': 3,
        '电力': 2, '石油': 2, '原油': 2, '油价': 2, '燃料': 2,
        '电力装机': 2, '电网': 2, '清洁能源': 2,
        '节能': 1, '减排': 1, '碳中和': 1, '清洁': 1,
    },
    '🏥 医疗': {
        '医疗': 3, '疫苗': 3, '肿瘤': 3, '手术': 3, '医保': 3,
        '药品监管': 3, '健康管理': 2, '中药': 2, '健康中国': 2,
        '治病': 2, '冠心病': 2, '肝病': 2, '脂肪肝': 2,
        '疾病': 1, '药物': 1, '患者': 1, '医院': 1,
        '健康': 1, '卫生': 1,
    },
    '🚀 科技': {
        '龙芯': 4, '飞腾': 4, '鲲鹏': 4, '兆芯': 4,
        '芯片': 3, '5G': 3, '6G': 3, '算力': 3,
        '机器人': 3, '无人机': 3, '科创板': 2,
        '数字': 2, '数据': 2, '智能': 2,
        '科技': 2, '创新': 1, '生产线': 1,
        '专利': 2, '中关村': 2,
        '经济': 1, '产业': 1, '发展': 1, '建设': 1, '项目': 1,
        '卫星': 2, '航天': 2, '火箭': 2, '发射': 1,
    },
    '🧱 材料': {
        '新材料': 4, '稀土': 3, '钢铁': 3, '化工': 3,
        '矿产': 3, '重工': 2, '造船': 2,
        '制造业': 1, '工厂': 1, '装备': 1, '设备': 1,
    },
    '🎖️ 军事': {
        '火箭炮': 4, '导弹': 4, '航母': 4, '战机': 4, '军演': 4,
        '军区': 3, '军事': 3, '军队': 3, '海军': 3, '国防': 3,
        '官兵': 2, '训练': 2,
        '武器': 2, '反恐': 2, '军营': 2, '南海': 1, '台海': 1,
        '战略': 1, '安全': 1, '国际': 1, '关系': 1, '合作': 1,
    },
}


def score_all_categories(title):
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        s = sum(w for kw, w in keywords.items() if kw in title)
        if s > 0:
            scores[cat] = s
    return scores


def high_confidence_keyword_category(title):
    kw_scores = score_all_categories(title)
    if not kw_scores:
        return None, None
    sorted_cats = sorted(kw_scores.items(), key=lambda x: -x[1])
    best_cat, best_score = sorted_cats[0]
    second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
    if best_score >= HIGH_CONFIDENCE_MIN_SCORE and (best_score - second_score) >= HIGH_CONFIDENCE_MARGIN:
        return best_cat, kw_scores
    return None, None


def _score_by_keywords(title):
    kw_scores = score_all_categories(title)
    if not kw_scores:
        return {"relevance": {col: 0 for col in COLUMN_ORDER}, "importance": 0, "timeliness": 0}
    max_score = max(kw_scores.values())
    relevance = {col: min(kw_scores.get(col, 0), 10) for col in COLUMN_ORDER}
    importance = min(max_score, 10)
    timeliness = min(max(1, max_score // 2), 10)
    return {"relevance": relevance, "importance": importance, "timeliness": timeliness}


def llm_classify_single(articles):
    import re
    from llm_client import call_llm

    cat_names = list(CATEGORY_KEYWORDS.keys())
    cat_simple = {}
    for full in cat_names:
        simple = re.sub(r'^[^\s]+\s', '', full).strip()
        cat_simple[full] = full
        cat_simple[simple] = full

    results = {}
    for a in articles:
        prompt = f"从以下栏目中选一个最贴合的，只输出栏目名称，不要输出其他文字。\n\n栏目：AI智能前沿、科技、军事、医疗、能源、农业、科研突破、材料、扶贫\n\n标题：{a['title']}\n\n最贴合的栏目："

        try:
            raw = call_llm("column-classify", messages=[{"role": "user", "content": prompt}])
            cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            full_cat = cat_simple.get(cleaned.strip('。，、\'"').strip())
            if full_cat:
                results[a['title']] = full_cat
            else:
                for k, v in cat_simple.items():
                    if k in cleaned:
                        results[a['title']] = v
                        break
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  ⚠ LLM分类失败: {a['title'][:30]}... {e}")
    return results


def priority_score(title, category):
    score = 0
    for kw, w in [('世界首次', 5), ('全球首个', 5), ('首次', 3),
                   ('自主创新', 2), ('攻坚克难', 2), ('突破', 2),
                   ('我国', 1), ('国产', 1)]:
        if kw in title:
            score += w
    if category == '🔬 世界性科研突破':
        has_breakthrough = any(k in title for k in
            ['首次', '突破', '发现', '全球', '世界', '诺贝尔', '首台', '首个'])
        if not has_breakthrough:
            score = max(0, score - 2)
    scores = score_all_categories(title)
    score += scores.get(category, 0)
    return score


def _validate_signals(signals):
    if not isinstance(signals, dict):
        return False
    relev = signals.get('relevance')
    if not isinstance(relev, dict):
        return False
    for col in COLUMN_ORDER:
        if col not in relev:
            return False
    if set(relev.keys()) != set(COLUMN_ORDER):
        return False
    for key in ('importance', 'timeliness'):
        val = signals.get(key)
        if not isinstance(val, (int, float)):
            return False
        if val < 0 or val > 10:
            return False
    return True


def aggregate_scores(signals):
    relev = signals['relevance']
    imp = signals['importance']
    time_ = signals['timeliness']
    factor = AGG_RELEV_BASE + AGG_IMP_W * imp / 10 + AGG_TIME_W * time_ / 10
    return {col: relev[col] * factor for col in COLUMN_ORDER}


def assign_category(signals, title=None):
    relev = signals['relevance']
    world_raw = relev.get(WORLD_CLASS_CATEGORY, 0)
    if world_raw >= WORLD_CLASS_THRESHOLD:
        if title is None or not _is_non_research_title(title):
            return WORLD_CLASS_CATEGORY
    scores = aggregate_scores(signals)
    if title and _is_non_research_title(title):
        scores.pop(WORLD_CLASS_CATEGORY, None)
    if not scores:
        return None
    best_col = max(scores, key=scores.get)
    if scores[best_col] == 0:
        return None
    return best_col


def score_signals(title, source):
    try:
        prompt = (
            f"分析以下新闻标题，从9个维度各给出0-10的relevance评分，以及importance(0-10)和timeliness(0-10)。"
            f"只输出JSON，不要markdown或解释。\n\n标题：{title}\n\n"
            f"9维度：{', '.join(COLUMN_ORDER)}\n\n"
            f"JSON格式：{{\"relevance\": {{\"🔬 世界性科研突破\": 0, ...}}, \"importance\": 0, \"timeliness\": 0}}"
        )
        raw = call_llm("column-score", messages=[{"role": "user", "content": prompt}], extra_body={"reasoning_effort": "none"})
        signals = json.loads(_strip_llm_json(raw))
        if _validate_signals(signals):
            return signals
        return None
    except Exception:
        return None


def score_signals_batch(articles):
    """批量栏目评分；失败时返回 None 给调用方逐条 LLM 回退。"""
    results = [None] * len(articles)
    col_list = ', '.join(COLUMN_ORDER)
    for batch_start in range(0, len(articles), LLM_BATCH_SIZE):
        batch = articles[batch_start:batch_start + LLM_BATCH_SIZE]
        batch_size = len(batch)
        prompt_lines = []
        for i, a in enumerate(batch):
            prompt_lines.append(f"[{i}] {a['title']}")
        prompt = (
            "分析以下新闻标题，从9个维度各给出0-10的relevance评分，"
            "以及importance(0-10)和timeliness(0-10)。\n"
            "返回 JSON 数组，每项包含 index、relevance（全部9维度）、importance、timeliness。\n"
            "只输出 JSON 数组，不要输出解释、markdown 或空内容。\n\n"
            f"9维度：{col_list}\n\n"
            + "\n".join(prompt_lines)
            + '\n\nJSON格式：\n'
            '[{"index": 0, "relevance": {"🔬 世界性科研突破": 0, ...}, "importance": 0, "timeliness": 0}, ...]'
        )

        parsed = None
        last_error = None
        for attempt in range(2):
            try:
                raw = call_llm("column-score", messages=[{"role": "user", "content": prompt}], temperature=0.0, extra_body={"reasoning_effort": "none"})
                parsed = _parse_score_json_array(raw, batch_size)
                break
            except Exception as e:
                last_error = e
                if attempt == 0:
                    print(f"  ⚠ batch 栏目评分 JSON 解析失败，重试一次（{batch_size} 条）")

        if parsed is not None:
            for i in range(batch_size):
                results[batch_start + i] = parsed[i]
        else:
            print(f"  ⚠ batch 栏目评分失败，回退单条 LLM（{batch_size} 条）: {last_error}")
    return results


def build_classification_result(today):
    today_str = today.strftime("%Y-%m-%d")
    input_path = BASE_DIR / today_str / "0新闻_粗筛.md"

    articles = parse_0(input_path, today)
    if not articles:
        return {}, []

    articles = [a for a in articles if detect_source(a["url"])]
    articles = [a for a in articles if is_quality_news(a["title"])]
    articles = [a for a in articles if not _is_conditional_excluded(
        a["title"], DIPLOMATIC_PROTOCOL, rescue_categories=COLUMN_ORDER
    )]
    articles = [a for a in articles if not _is_conditional_excluded(
        a["title"], OUTLOOK_WORDS, rescue_words=OUTLOOK_RESCUE_WORDS
    )]

    china_pass = []
    china_llm = []
    for a in articles:
        if is_china_related(a["title"]):
            china_pass.append(a)
        elif is_china_source(a["url"]):
            china_llm.append(a)
    llm_confirmed = llm_is_china_related_batch(china_llm) if china_llm else []
    articles = china_pass + llm_confirmed

    duplicate_candidates = find_duplicate_candidate_groups(articles)
    if duplicate_candidates:
        articles, _ = llm_review_duplicate_candidates(articles, duplicate_candidates)

    classified = {col: [] for col in COLUMN_ORDER}
    llm_fail_count = 0

    llm_candidates = []
    for a in articles:
        if _is_b2_breakthrough(a['title']):
            a['signals'] = None
            a['score_source'] = 'keyword-b2'
            a['category'] = WORLD_CLASS_CATEGORY
            kw_scores = score_all_categories(a['title'])
            a['priority'] = priority_score(a['title'], WORLD_CLASS_CATEGORY) + kw_scores.get(WORLD_CLASS_CATEGORY, 0)
            classified[WORLD_CLASS_CATEGORY].append(a)
            continue
        cat_high, kw_scores_high = high_confidence_keyword_category(a['title'])
        if cat_high is not None:
            a['signals'] = None
            a['score_source'] = 'keyword-high-confidence'
            a['category'] = cat_high
            a['priority'] = priority_score(a['title'], cat_high) + kw_scores_high.get(cat_high, 0)
            classified[cat_high].append(a)
            continue
        llm_candidates.append(a)

    # G1: 正文信号 for A 原型 — 标题弱但正文有世界首例/期刊等
    remaining = []
    for a in llm_candidates:
        if any(kw in a['title'] for kw in ['研究', '科研', '进展', '实验', '试验', '育种', '水稻']):
            body = _fetch_page_text(a['url'])
            if body and any(kw in body for kw in A_BODY_SIGNALS):
                a['signals'] = None
                a['score_source'] = 'body-signal'
                a['category'] = WORLD_CLASS_CATEGORY
                kw_scores = score_all_categories(a['title'])
                a['priority'] = priority_score(a['title'], WORLD_CLASS_CATEGORY) + kw_scores.get(WORLD_CLASS_CATEGORY, 0)
                classified[WORLD_CLASS_CATEGORY].append(a)
                continue
        remaining.append(a)
    llm_candidates = remaining

    if llm_candidates:
        batch_signals = score_signals_batch(llm_candidates)
        for idx, a in enumerate(llm_candidates):
            signals = batch_signals[idx]
            source = detect_source(a['url'])
            if signals is not None:
                a['signals'] = signals
                a['score_source'] = 'llm-batch'
                scores = aggregate_scores(signals)
                cat = assign_category(signals, a['title'])
                if cat is None:
                    continue
                priority = scores.get(cat, 0)
            else:
                signals_single = score_signals(a['title'], source)
                if signals_single is not None:
                    a['signals'] = signals_single
                    a['score_source'] = 'llm'
                    scores = aggregate_scores(signals_single)
                    cat = assign_category(signals_single, a['title'])
                    if cat is None:
                        continue
                    priority = scores.get(cat, 0)
                else:
                    llm_fail_count += 1
                    kw_scores = score_all_categories(a['title'])
                    if not kw_scores:
                        continue
                    try:
                        sorted_cats = sorted(kw_scores.items(), key=lambda x: -x[1])
                        best_cat, best_score = sorted_cats[0]
                        second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
                        if best_score >= 4 and (best_score - second_score) >= 2:
                            cat = best_cat
                        else:
                            try:
                                results = llm_classify_single([a])
                                cat = results.get(a['title']) or best_cat
                            except Exception:
                                cat = best_cat
                    except Exception:
                        cat = max(kw_scores, key=kw_scores.get)
                    a['signals'] = None
                    a['score_source'] = 'keyword-fallback'
                    priority = priority_score(a['title'], cat) + kw_scores.get(cat, 0)
            a['category'] = cat
            a['priority'] = priority
            classified[cat].append(a)

    if articles:
        llm_fail_pct = llm_fail_count / len(articles) * 100
        if llm_fail_pct >= 30:
            print(f"\n⚠ column-score 降级率 {llm_fail_pct:.0f}%", file=sys.stderr)

    for col in classified:
        classified[col].sort(key=lambda x: -x.get('priority', 0))

    selected = []
    used_urls = set()
    for col in COLUMN_ORDER:
        pool = [a for a in classified[col] if a['url'] not in used_urls]
        if pool:
            pick = pool[0]
            pick['column'] = col
            selected.append(pick)
            used_urls.add(pick['url'])

    remaining = []
    for col in COLUMN_ORDER:
        for a in classified[col]:
            if a['url'] not in used_urls:
                remaining.append(a)
    remaining.sort(key=lambda x: -x.get('priority', 0))
    while len(selected) < 10 and remaining:
        pick = remaining.pop(0)
        if pick['url'] not in used_urls:
            pick['column'] = pick.get('category', COLUMN_ORDER[1])
            selected.append(pick)
            used_urls.add(pick['url'])

    return classified, selected


def run(today, dry_run):
    today_str = today.strftime("%Y-%m-%d")

    print(f"═══ Step 4: 分类筛选 ═══")
    print(f"日期: {today_str}")

    classified, selected = build_classification_result(today)

    if not classified:
        print("❌ 0新闻_粗筛.md 为空或无通过条目")
        return

    for col in COLUMN_ORDER:
        if classified[col]:
            top = classified[col][0]
            print(f"  {col}: {len(classified[col])}条 [最高={top.get('priority',0)}] {top['title'][:40]}")
        else:
            print(f"  {col}: 0条")

    print(f"\n精选: {len(selected)}条")
    for a in selected:
        ps = a.get('priority', 0)
        print(f"  [{ps}分] {a.get('column', '?')} | {a['title'][:50]}")

    lines = [f"# {today_str} 精选新闻（按栏目分类）\n"]
    for col in COLUMN_ORDER:
        col_selected = [a for a in selected if a.get('column') == col]
        if not col_selected:
            continue
        lines.append(f"\n## {col}\n")
        for a in col_selected:
            src = detect_source(a['url'])
            if not src:
                continue
            lines.append(f"### [{src}] {a['title']}")
            lines.append(f"URL：{a['url']}")
            lines.append(f"发布时间：{a['date']}")
            lines.append('')

    output_path = BASE_DIR / today_str / "1新闻_链接.md"
    if dry_run:
        print(f"\n═══ 预览: {output_path} ═══")
        print("\n".join(lines)[:2000])
    else:
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✅ 已写入: {output_path}")

    from news_archive import archive_articles_best_effort
    archive_articles_best_effort(today_str, classified, selected, dry_run)

    try:
        import archive_enrich
        archive_enrich.enrich_archive_best_effort(today_str, selected, dry_run=dry_run, include_images=False)
    except Exception as e:
        print(f"⚠ 归档正文/首图补全失败: {e}", file=sys.stderr)


def main():
    today, dry_run = parse_args()
    run(today, dry_run)


if __name__ == "__main__":
    main()
