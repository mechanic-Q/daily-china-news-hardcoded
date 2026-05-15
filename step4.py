#!/usr/bin/env python3
"""
Step 4: 栏目分类筛选 — 从 0新闻_粗筛.md 生成 1新闻_链接.md
读取 step1_3.py 的输出，按 8 栏目分类 → 涉华过滤 → 质量过滤 → 优先级排序 → 精选输出

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

# ── 非新闻排除列表 ───────────────────────────────────────
EXCLUDE_TITLES = [
    '春雨落', '百谷生', '谷雨', '舞蹈诗剧', '三月三', '时装周',
    'DELVAUX', '世界超级摩托车', '节气', '立夏', '立春', '立冬',
    '冬至', '夏至', '春分', '秋分', '惊蛰', '芒种', '白露',
    '寒露', '霜降', '小满',
]


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
    """解析 0新闻_粗筛.md，提取通过验证的条目"""
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
        ok = m.group(4) == '✅'
        if ok and date == today_str:
            articles.append({"date": date, "title": title, "url": url})

    return articles


def is_quality_news(title):
    """新闻质量过滤：排除非新闻内容"""
    for kw in EXCLUDE_TITLES:
        if kw in title:
            return False
    return True


# ── 涉华判断 ────────────────────────────────────────────
def is_china_related(title, url):
    h = title
    u = url

    foreign_no_china = [('俄', '俄罗斯'), ('美', '美国'), ('法', '法国'), ('德', '德国'),
                       ('日', '日本'), ('英', '英国'), ('韩', '韩国'), ('印', '印度'),
                       ('巴', '巴西'), ('澳', '澳大利亚'), ('越', '越南'), ('伊', '伊朗'),
                       ('乌', '乌克兰'), ('以', '以色列'), ('叙', '叙利亚')]
    for prefix, country in foreign_no_china:
        if (prefix in h or country in h):
            if '中国' not in h and '我国' not in h and '中俄' not in h and '中美' not in h and '中日' not in h and '中欧' not in h and '中英' not in h and '中法' not in h and '中巴' not in h:
                if any(k in h for k in [prefix, country]):
                    return False

    china_kw = ['中国', '我国', '国内', '习近平', '李强', '国务院', '全国',
                '中欧', '中美', '中俄', '中日', '中韩', '解放军', '外交部',
                '商务部', '国产', '航天', '嫦娥', '天宫', '中关村', '北京',
                '上海', '广州', '深圳', '浙江', '江苏', '广东', '四川',
                '成都', '武汉', '杭州', '南京', '新疆', '西藏', '香港',
                '澳门', '台湾', '央企', '国企', '中国市场', '海峡两岸']
    for kw in china_kw:
        if kw in h:
            return True

    ref_src = 'cankaoxiaoxi' in u or 'ckxxapp' in u
    cas_src = 'cas.cn' in u
    cctv_src = 'cctv.com' in u or 'people.com.cn' in u or 'xinhuanet' in u or 'news.cn' in u

    if ref_src:
        ref_kw = ['中国', '习近平', '港媒', '中欧', '中美', '中俄',
                  '普京谈中俄', '美媒文章：美国面对', '中国发出警告']
        for kw in ref_kw:
            if kw in h:
                return True
        return False
    if cas_src:
        return True
    if 'cnnpn.cn' in u:
        cnnc_kw = ['中国', '我国', '中核', '中广核', '国家电投', '华龙',
                   '玲龙', '国和一号', '海南', '昌江', '太平岭', '三澳',
                   '霞浦', '陆丰', '红沿河', '宁德', '三门', '海阳', '秦山',
                   '大亚湾', '岭澳', '田湾', '防城港', '阳江', '台山',
                   '石岛湾', '漳州', '惠州', '徐大堡', '广元', '嘉峪关',
                   '自主创新', '攻坚克难']
        for kw in cnnc_kw:
            if kw in h:
                return True
        return False
    if cctv_src or 'news.cn' in u or 'xinhuanet' in u or 'cctv.com' in u or 'people.com.cn' in u:
        return True
    return True


# ── 8栏目分类 ────────────────────────────────────────────
def classify(title):
    h = title
    if any(k in h for k in ['扶贫', '脱贫', '乡村振兴', '驻村书记', '对口帮扶', '消费扶贫', '新就业形态']):
        return '🤝 扶贫'
    if any(k in h for k in ['肿瘤', '手术', '疫苗', '医保', '药品监管', '健康中国', '治病', '中药', '脂肪肝',
                            '肝病', '冠心病', '生物标志物', '健康管理', '医疗']):
        return '🏥 医疗'
    if any(k in h for k in ['武器', '海峡', '伊朗', '俄罗斯', '核武', '军演', '军事', '国防', '反恐',
                            '海军', '航母', '战机', '军队', '军营', '官兵', '军']):
        return '🎖️ 军事'
    if any(k in h for k in ['石油', '原油', '油价', '核能', '光伏', '燃料', '电力装机', '电网', '风电',
                            '氢能', '人造太阳', '核电', '能源', '电力', '加油', '深水油气']):
        return '⚡ 能源'
    if any(k in h for k in ['玉米', '春播', '农机', '种业', '沙地', '耕地', '畜牧', '春耕', '育秧', '小麦',
                            '阳台种菜', '治沙', '农业', '农村', '粮食', '农产品', '农田']):
        return '🌾 农业'
    if any(k in h for k in ['钢铁', '化工', '稀土', '矿产', '颜料', '国际标准', '新材料', '造船', '重工']):
        return '🧱 材料'
    if any(k in h for k in ['机器人', 'AI', '人工智能', '无人机', '技术', '商标侵权', '专利', '智能',
                            '科技', '中关村', '科创', '数字', '数据', '算力', '创新', '生产线']):
        return '🚀 科技'
    if any(k in h for k in ['重编程', 'p53', '诺贝尔', '干细胞', 'iPS', '化学小分子', '世界首次', '考古',
                            '发现', '基因', '宇宙', '航天', '火箭', '卫星', '探测']):
        return '🔬 科研'
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
    """主流程"""
    today_str = today.strftime("%Y-%m-%d")
    input_path = BASE_DIR / today_str / "0新闻_粗筛.md"

    print(f"═══ Step 4: 分类筛选 ═══")
    print(f"日期: {today_str}")
    print(f"数据: {input_path}\n")

    # ① 读取并过滤
    articles = parse_0(input_path, today)
    if not articles:
        print("❌ 0新闻_粗筛.md 为空或无通过条目")
        return

    total = len(articles)
    articles = [a for a in articles if is_quality_news(a["title"])]
    quality_removed = total - len(articles)
    print(f"原始: {total}条  质量过滤: 移除{quality_removed}条  → {len(articles)}条\n")

    # ② 分类 + 涉华 + 评分
    classified = {col: [] for col in
                  ['🔬 科研', '🌾 农业', '🤝 扶贫', '⚡ 能源',
                   '🏥 医疗', '🚀 科技', '🧱 材料', '🎖️ 军事']}

    foreign_removed = 0
    for a in articles:
        if not is_china_related(a['title'], a['url']):
            foreign_removed += 1
            continue
        cat = classify(a['title'])
        if cat and cat in classified:
            a['priority'] = priority_score(a['title'])
            classified[cat].append(a)

    print(f"涉华过滤: 移除{foreign_removed}条\n")

    # ③ 栏目内排序
    col_order = ['🔬 科研', '🌾 农业', '🤝 扶贫', '⚡ 能源',
                 '🏥 医疗', '🚀 科技', '🧱 材料', '🎖️ 军事']

    for col in classified:
        classified[col].sort(key=lambda x: -x.get('priority', 0))

    # 打印统计
    for col in col_order:
        if classified[col]:
            top = classified[col][0]
            print(f"  {col}: {len(classified[col])}条 [最高={top.get('priority',0)}] {top['title'][:40]}")
        else:
            print(f"  {col}: 0条")

    # ④ 精选：每栏目取最高分
    selected = []
    used_urls = set()

    for col in col_order:
        pool = [a for a in classified[col] if a['url'] not in used_urls]
        if pool:
            pick = pool[0]
            pick['column'] = col
            selected.append(pick)
            used_urls.add(pick['url'])

    # 补满（全局按优先级）
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

    # ⑤ 写入 1新闻_链接.md
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
    content = "\n".join(lines)

    if dry_run:
        print(f"\n═══ 预览: {output_path} ═══")
        print(content[:2000])
    else:
        output_path.write_text(content, encoding="utf-8")
        print(f"\n✅ 已写入: {output_path}")


def main():
    today, dry_run = parse_args()
    run(today, dry_run)


if __name__ == "__main__":
    main()
