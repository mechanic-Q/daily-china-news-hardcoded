#!/usr/bin/env python3
"""
Step 4: 栏目分类筛选 — 从 0新闻_粗筛.md 生成 1新闻_链接.md
读取 step1_3.py 的输出，按 8 栏目分类 → 质量过滤 → 优先级排序 → 精选输出

用法:
    python3 step4.py                      # 处理今天
    python3 step4.py --date 2026-05-10     # 处理指定日期
    python3 step4.py --dry-run              # 预览，不写文件
"""

import datetime
import re
import sys
from pathlib import Path

BASE_DIR = Path("/mnt/e/每日新中国")

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
    import os
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        return False
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.minimax.chat/v1", api_key=api_key)
        resp = client.chat.completions.create(
            model="minimax-m2.7",
            messages=[{"role": "user", "content": f"判断以下新闻标题内容主体上是否直接与中国相关（报道或讨论中国事务/中国人/中国企业/中国政府/中美关系等）。只回答\"是\"或\"否\"。\n\n标题：{title}"}],
            temperature=0.1, max_tokens=10, timeout=15,
        )
        answer = resp.choices[0].message.content.strip()
        return answer.startswith("是")
    except Exception:
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
    """解析 0新闻_粗筛.md，提取通过 HTTP 200 验证的条目"""
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
    """新闻质量过滤：排除非新闻内容 + 负面新闻"""
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
        'p53': 4, '化学小分子': 4, '考古发现': 4,
        '航天': 3, '卫星': 3, '探测': 3, '嫦娥': 3, '天宫': 3,
        '火星': 3, '月球': 3, '宇宙': 3,
    },
    '🌾 农业': {
        '农业': 3, '粮食': 3, '农产品': 3, '农田': 3,
        '玉米': 2, '小麦': 2, '春播': 2, '春耕': 2, '育秧': 2,
        '农机': 2, '种业': 2, '耕地': 2, '畜牧': 2,
        '治沙': 2, '农村': 1,
    },
    '🤝 扶贫': {
        '精准扶贫': 5, '易地搬迁': 4, '扶贫': 4, '脱贫': 4,
        '对口帮扶': 3, '消费扶贫': 3, '驻村书记': 3,
    },
    '⚡ 能源': {
        '核电': 4, '核能': 4, '人造太阳': 4,
        '光伏': 3, '风电': 3, '氢能': 3, '能源': 3,
        '电力': 2, '石油': 2, '原油': 2, '油价': 2, '燃料': 2,
    },
    '🏥 医疗': {
        '医疗': 3, '疫苗': 3, '肿瘤': 3, '手术': 3, '医保': 3,
        '药品监管': 3, '健康管理': 2, '中药': 2, '健康中国': 2,
    },
    '🚀 科技': {
        '人工智能': 3, 'AI': 3, '机器人': 3, '无人机': 3,
        '算力': 3, '科创': 2, '数字': 2, '数据': 2, '智能': 2,
        '科技': 2, '创新': 1, '生产线': 1,
    },
    '🧱 材料': {
        '新材料': 4, '稀土': 3, '钢铁': 3, '化工': 3,
        '矿产': 3, '重工': 2, '造船': 2,
    },
    '🎖️ 军事': {
        '火箭炮': 4, '导弹': 4, '航母': 4, '战机': 4, '军演': 4,
        '军区': 3, '军事': 3, '军队': 3, '海军': 3, '国防': 3,
        '官兵': 2, '训练': 2,
    },
}


def score_all_categories(title):
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        s = sum(w for kw, w in keywords.items() if kw in title)
        if s > 0:
            scores[cat] = s
    return scores


def llm_classify_batch(articles, batch_size=5):
    import os
    from openai import OpenAI
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        return {}

    cat_names = list(CATEGORY_KEYWORDS.keys())
    results = {}

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        prompt = "将以下新闻标题归入最贴切的栏目（只能选一个）。\n"
        prompt += "栏目：" + "、".join(cat_names) + "\n\n"
        prompt += "输出格式（每行一条）：序号|栏目名\n\n"
        for j, a in enumerate(batch):
            prompt += f"{j+1}. {a['title']}\n"

        try:
            client = OpenAI(base_url="https://api.minimax.chat/v1", api_key=api_key)
            resp = client.chat.completions.create(
                model="minimax-m2.7",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=200, timeout=30,
            )
            text = resp.choices[0].message.content.strip()
            for line in text.split("\n"):
                parts = line.strip().split("|")
                if len(parts) == 2:
                    try:
                        idx = int(parts[0].strip()) - 1
                        cat = parts[1].strip()
                        if 0 <= idx < len(batch) and cat in CATEGORY_KEYWORDS:
                            results[batch[idx]['title']] = cat
                    except ValueError:
                        pass
        except Exception as e:
            print(f"  ⚠ LLM分类失败: {e}")

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


def run(today, dry_run):
    today_str = today.strftime("%Y-%m-%d")
    input_path = BASE_DIR / today_str / "0新闻_粗筛.md"

    print(f"═══ Step 4: 分类筛选 ═══")
    print(f"日期: {today_str}")
    print(f"数据: {input_path}\n")

    articles = parse_0(input_path, today)
    if not articles:
        print("❌ 0新闻_粗筛.md 为空或无通过条目")
        return

    total = len(articles)
    articles = [a for a in articles if is_quality_news(a["title"])]
    quality_removed = total - len(articles)

    # 涉华过滤：关键词 → 来源检测 → LLM回退
    china_pass = []
    china_llm = []
    for a in articles:
        if is_china_related(a["title"]):
            china_pass.append(a)
        elif is_china_source(a["url"]):
            china_llm.append(a)
    # LLM 确认来源是中国但关键词未命中的
    llm_confirmed = []
    for a in china_llm:
        if llm_is_china_related(a["title"]):
            llm_confirmed.append(a)
    china_removed = len(articles) - len(china_pass) - len(llm_confirmed)
    articles = china_pass + llm_confirmed
    quality_removed += china_removed
    print(f"原始: {total}条  质量过滤: 移除{quality_removed}条  → {len(articles)}条\n")

    col_order = [
        '🔬 世界性科研突破', '🌾 农业', '🤝 扶贫', '⚡ 能源',
        '🏥 医疗', '🚀 科技', '🧱 材料', '🎖️ 军事',
    ]
    classified = {col: [] for col in col_order}

    # Phase 1: 关键词评分 → 分离高置信度 / 低置信度
    high_confidence = {}
    low_confidence = []

    for a in articles:
        scores = score_all_categories(a['title'])
        if scores:
            sorted_cats = sorted(scores.items(), key=lambda x: -x[1])
            best_cat, best_score = sorted_cats[0]
            second_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
            if best_score >= 3 and (best_score - second_score) >= 2:
                high_confidence[a['title']] = best_cat
            else:
                low_confidence.append(a)
        else:
            low_confidence.append(a)

    # Phase 2: LLM 批量裁决低置信度
    llm_results = {}
    if low_confidence:
        print(f"  关键词高置信度: {len(high_confidence)}条, LLM裁决: {len(low_confidence)}条")
        llm_results = llm_classify_batch(low_confidence)

    # Phase 3: 合并结果，归入栏目
    for a in articles:
        cat = high_confidence.get(a['title'])
        if not cat:
            cat = llm_results.get(a['title'])
        if not cat and score_all_categories(a['title']):
            scores = score_all_categories(a['title'])
            cat = max(scores, key=scores.get)
        if cat and cat in classified:
            a['category'] = cat
            a['priority'] = priority_score(a['title'], cat)
            classified[cat].append(a)

    for col in classified:
        classified[col].sort(key=lambda x: -x.get('priority', 0))

    for col in col_order:
        if classified[col]:
            top = classified[col][0]
            print(f"  {col}: {len(classified[col])}条 [最高={top.get('priority',0)}] {top['title'][:40]}")
        else:
            print(f"  {col}: 0条")

    selected = []
    used_urls = set()

    for col in col_order:
        pool = [a for a in classified[col] if a['url'] not in used_urls]
        if pool:
            pick = pool[0]
            pick['column'] = col
            selected.append(pick)
            used_urls.add(pick['url'])

    remaining = []
    for col in col_order:
        for a in classified[col]:
            if a['url'] not in used_urls:
                remaining.append(a)
    remaining.sort(key=lambda x: -x.get('priority', 0))

    while len(selected) < 10 and remaining:
        pick = remaining.pop(0)
        if pick['url'] not in used_urls:
            pick['column'] = pick.get('category', '🚀 科技')
            selected.append(pick)
            used_urls.add(pick['url'])

    print(f"\n精选: {len(selected)}条")
    for a in selected:
        ps = a.get('priority', 0)
        print(f"  [{ps}分] {a.get('column', '?')} | {a['title'][:50]}")

    lines = [f"# {today_str} 精选新闻（按栏目分类）\n"]
    for col in col_order:
        col_selected = [a for a in selected if a.get('column') == col]
        lines.append(f"\n## {col}\n")
        if col_selected:
            for a in col_selected:
                src = detect_source(a['url'])
                lines.append(f"### [{src}] {a['title']}")
                lines.append(f"URL：{a['url']}")
                lines.append('')
        else:
            lines.append('（当日无真实报道，栏目留空）\n')

    output_path = BASE_DIR / today_str / "1新闻_链接.md"

    if dry_run:
        print(f"\n═══ 预览: {output_path} ═══")
        print("\n".join(lines)[:2000])
    else:
        output_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n✅ 已写入: {output_path}")


def main():
    today, dry_run = parse_args()
    run(today, dry_run)


if __name__ == "__main__":
    main()
