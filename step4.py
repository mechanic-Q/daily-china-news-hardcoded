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
import re
import sys
from pathlib import Path

from llm_client import call_llm, LLMCallError

BASE_DIR = Path("/mnt/e/每日新中国")

COLUMN_ORDER = [
    '🔬 世界性科研突破',
    '🤖 AI智能前沿',
    '🌾 农业',
    '🤝 扶贫',
    '⚡ 能源',
    '🏥 医疗',
    '🚀 科技',
    '🧱 材料',
    '🎖️ 军事',
]

WORLD_CLASS_THRESHOLD = 7
WORLD_CLASS_CATEGORY = '🔬 世界性科研突破'
AGG_RELEV_BASE = 0.5
AGG_IMP_W = 0.3
AGG_TIME_W = 0.2

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
        )
        return ans.strip().startswith("是")
    except Exception:
        import traceback
        traceback.print_exc()
        return False


def parse_args():
    dry = "--dry-run" in sys.argv
    date_str = None
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"错误: 日期格式无效: {date_str}")
            sys.exit(1)
    else:
        dt = datetime.date.today()
    return dt, dry


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


CATEGORY_KEYWORDS = {
    '🔬 世界性科研突破': {
        '诺贝尔': 5, '世界首次': 5, '全球首次': 5, '首次发现': 5,
        '基因': 4, '量子': 4, '干细胞': 4, 'iPS': 4, '重编程': 4,
        'p53': 4, '化学小分子': 4, '考古发现': 4, '考古': 3,
        '航天': 3, '卫星': 3, '探测': 3, '嫦娥': 3, '天宫': 3,
        '火星': 3, '月球': 3, '宇宙': 3, '火箭发射': 3,
        '发现': 2, '突破': 2,
        '研究': 1, '实验': 1, '论文': 1,
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
    },
    '🤝 扶贫': {
        '精准扶贫': 5, '易地搬迁': 4, '扶贫': 4, '脱贫': 4,
        '对口帮扶': 3, '消费扶贫': 3, '驻村书记': 3,
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
        '机器人': 3, '无人机': 3, '科创': 2,
        '数字': 2, '数据': 2, '智能': 2,
        '科技': 2, '创新': 1, '生产线': 1,
        '专利': 2, '中关村': 2,
        '经济': 1, '产业': 1, '发展': 1, '建设': 1, '项目': 1,
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


def detect_source(url):
    if 'cankaoxiaoxi' in url or 'ckxxapp' in url:
        return '参考消息'
    if 'military.cctv' in url:
        return '央视军事'
    if 'news.cctv' in url:
        return '央视新闻'
    if 'cas.cn' in url:
        return '中科院'
    if 'cnnpn.cn' in url or 'cnnc.com' in url:
        return '中核集团'
    if 'people.com.cn' in url:
        return '人民日报'
    if 'news.cn' in url or 'xinhuanet' in url:
        return '新华社'
    return '综合'


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


def assign_category(signals):
    relev = signals['relevance']
    world_raw = relev.get(WORLD_CLASS_CATEGORY, 0)
    if world_raw >= WORLD_CLASS_THRESHOLD:
        return WORLD_CLASS_CATEGORY
    scores = aggregate_scores(signals)
    best_col = max(scores, key=scores.get)
    if scores[best_col] == 0:
        return None
    return best_col


def score_signals(title, source):
    from llm_client import call_llm
    try:
        prompt = (
            f"分析以下新闻标题，从9个维度各给出0-10的relevance评分，以及importance(0-10)和timeliness(0-10)。"
            f"只输出JSON。\n\n标题：{title}\n\n"
            f"9维度：{', '.join(COLUMN_ORDER)}\n\n"
            f"JSON格式：{{\"relevance\": {{\"🔬 世界性科研突破\": 0, ...}}, \"importance\": 0, \"timeliness\": 0}}"
        )
        raw = call_llm("column-score", messages=[{"role": "user", "content": prompt}])
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        signals = json.loads(raw)
        if _validate_signals(signals):
            return signals
        return None
    except Exception:
        return None


def build_classification_result(today):
    today_str = today.strftime("%Y-%m-%d")
    input_path = BASE_DIR / today_str / "0新闻_粗筛.md"

    articles = parse_0(input_path, today)
    if not articles:
        return {}, []

    articles = [a for a in articles if is_quality_news(a["title"])]

    china_pass = []
    china_llm = []
    for a in articles:
        if is_china_related(a["title"]):
            china_pass.append(a)
        elif is_china_source(a["url"]):
            china_llm.append(a)
    llm_confirmed = []
    for a in china_llm:
        if llm_is_china_related(a["title"]):
            llm_confirmed.append(a)
    articles = china_pass + llm_confirmed

    classified = {col: [] for col in COLUMN_ORDER}
    llm_fail_count = 0

    for a in articles:
        source = detect_source(a['url'])
        signals = score_signals(a['title'], source)
        if signals is not None:
            a['signals'] = signals
            a['score_source'] = 'llm'
            scores = aggregate_scores(signals)
            cat = assign_category(signals)
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
            lines.append(f"### [{src}] {a['title']}")
            lines.append(f"URL：{a['url']}")
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


def main():
    today, dry_run = parse_args()
    run(today, dry_run)


if __name__ == "__main__":
    main()
