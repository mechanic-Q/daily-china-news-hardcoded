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
    import os, time
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
        return answer == "是"
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


def classify(title):
    h = title
    if any(k in h for k in ['扶贫', '脱贫', '对口帮扶', '消费扶贫', '驻村书记', '精准扶贫', '易地搬迁']):
        return '🤝 扶贫'
    if any(k in h for k in ['肿瘤', '手术', '疫苗', '医保', '药品监管', '健康中国', '治病', '中药',
                            '脂肪肝', '肝病', '冠心病', '生物标志物', '健康管理', '医疗']):
        return '🏥 医疗'
    if any(k in h for k in ['武器', '军演', '国防', '反恐', '海军', '航母', '战机', '军队',
                            '军营', '官兵', '军事']):
        return '🎖️ 军事'
    if any(k in h for k in ['石油', '原油', '油价', '核能', '光伏', '风电', '氢能', '人造太阳',
                            '核电', '能源', '电力', '电力装机', '燃料']):
        return '⚡ 能源'
    if any(k in h for k in ['玉米', '春播', '农机', '种业', '耕地', '畜牧', '春耕', '育秧',
                            '小麦', '治沙', '农业', '农村', '粮食', '农产品', '农田']):
        return '🌾 农业'
    if any(k in h for k in ['钢铁', '化工', '稀土', '矿产', '新材料', '重工', '造船']):
        return '🧱 材料'
    if any(k in h for k in ['机器人', 'AI', '人工智能', '无人机', '专利', '智能', '科技',
                            '中关村', '科创', '数字', '数据', '算力', '创新', '生产线']):
        return '🚀 科技'
    if any(k in h for k in ['重编程', 'p53', '诺贝尔', '干细胞', 'iPS', '化学小分子', '考古',
                            '发现', '基因', '宇宙', '航天', '火箭', '卫星', '探测', '世界首次',
                            '嫦娥', '天宫', '量子', '火星', '月球']):
        return '🔬 世界性科研突破'
    if '自主创新' in h or '攻坚克难' in h:
        return '🚀 科技'
    return None


def priority_score(title):
    score = 0
    if '首条' in title or '首次' in title or '第一批' in title or '第一' in title:
        score += 3
    if '自主创新' in title or '攻坚克难' in title:
        score += 2
    if '我国' in title or '国产' in title:
        score += 1
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

    for a in articles:
        cat = classify(a['title'])
        if cat and cat in classified:
            a['priority'] = priority_score(a['title'])
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
            pick['column'] = classify(pick['title'])
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
