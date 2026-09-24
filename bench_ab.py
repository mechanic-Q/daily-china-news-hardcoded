#!/usr/bin/env python3
"""
bench_ab.py — 双后端冻结输入 A/B（issue #57）

用 2026-09-23 的冻结输入（0新闻_粗筛.md + 2新闻_已审核.md），对 llm.yaml 中
qwen-local（8899 IQ3_XS 旧栈）与 kvmem（27182 IQ2_S）两个 provider 各跑一遍
step4 + step7，记录 wall time，对比前 10 选择与栏目分配一致率。

生产安全设计：
- step4/step7 通过 DAILY_OUTPUT_DIR 指向沙箱目录，1新闻_链接.md / 3新闻_概述.md
  等主输出零污染（daily/common.py 原生支持）。
- news_archive.py 的 BASE_DIR 硬编码不认 DAILY_OUTPUT_DIR，step4 会 upsert 生产
  归档 articles/{YYYY-MM}.jsonl —— 跑前备份该文件，跑后原子恢复，是唯一需要还原
  的写入面；跑前不存在的分片结束后删除。llm.yaml 顶层 provider 行临时切换、
  finally 原子还原。SIGTERM 转 KeyboardInterrupt 保证恢复链执行；pid 锁拒绝与
  run_all.sh / 其他实例并发。
- archive_enrich 以 include_images=False 调用（step4 内置），且其正文/图片字段
  upsert 时保留旧值，沙箱跑动不删生产数据；jsonl 恢复后归档回到跑前状态。

用法:
    python3 bench_ab.py --date 2026-09-23 --providers kvmem,qwen-local
    python3 bench_ab.py --date 2026-09-23 --providers kvmem --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).parent
sys.path.insert(0, str(REPO))

DAILY_BASE = Path("/mnt/e/每日新中国")

STEP4_OUTPUT = "1新闻_链接.md"
STEP7_OUTPUT = "3新闻_概述.md"


def archive_jsonl_path(date_str: str) -> Path:
    """与 news_archive.month_path 同规则：按日期月份定位生产归档分片。"""
    return DAILY_BASE / "archive" / "articles" / f"{date_str[:7]}.jsonl"


STEP_TIMEOUT_S = 1800  # 单步 wall 上限：后端 hang 死时保底，避免 llm.yaml 长期处于切换态


def atomic_write_text(path: Path, text: str) -> None:
    """临时文件 + os.replace 原子写，防 kill/断电落在 truncate 窗口损坏生产文件。"""
    tmp = path.with_name(path.name + ".bench_ab.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def restore_archive(backup: Path, target: Path) -> None:
    """原子恢复生产归档分片。"""
    tmp = target.with_name(target.name + ".bench_ab.tmp")
    shutil.copy2(backup, tmp)
    os.replace(tmp, target)


def _sigterm_to_keyboardinterrupt(signum, frame):
    raise KeyboardInterrupt  # 让 SIGTERM 也走 finally 恢复链


def acquire_lock(date_str: str) -> Path:
    """pid 锁：与 run_all.sh / 另一实例并发时拒绝启动（llm.yaml 会被临时改写）。"""
    lock = Path(tempfile.gettempdir()) / f"daily_bench_ab.{date_str}.lock"
    if lock.exists():
        try:
            other = int(lock.read_text().strip())
            os.kill(other, 0)
            raise RuntimeError(f"另一实例疑似在跑 (pid={other})，锁: {lock}")
        except (ValueError, ProcessLookupError):
            pass  # 残留死锁，覆盖
    lock.write_text(str(os.getpid()), encoding="utf-8")
    return lock


def release_lock(lock: Path) -> None:
    lock.unlink(missing_ok=True)


def parse_args():
    ap = argparse.ArgumentParser(description="双后端冻结输入 A/B")
    ap.add_argument("--date", required=True, help="冻结输入日期 YYYY-MM-DD")
    ap.add_argument("--providers", default="kvmem,qwen-local",
                    help="逗号分隔的 provider 名（须在 llm.yaml providers 中定义）")
    ap.add_argument("--out-dir", default=None, help="结果目录（默认 /tmp/daily_bench_ab/<ts>）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只做前置检查与沙箱准备，不跑 step4/step7、不写 llm.yaml")
    return ap.parse_args()


# ────────────────────────── llm.yaml provider 切换 ──────────────────────────

def switch_provider(yaml_text: str, provider: str) -> str:
    """把 llm.yaml 顶层 provider: <name> 改为指定值（仅顶层那一行）。"""
    pattern = re.compile(r"(?m)^provider:\s*\S+\s*$")
    matches = pattern.findall(yaml_text)
    if len(matches) != 1:
        raise ValueError(f"llm.yaml 顶层 provider 行应有且仅有 1 处，实际 {len(matches)}")
    return pattern.sub(f"provider: {provider}", yaml_text, count=1)


# ────────────────────────── 输出文件解析 ──────────────────────────

H3_RE = re.compile(r"^###\s+\[(.+?)\]\s+(.+)$", re.M)


def parse_selection(md_text: str) -> list[dict]:
    """解析 1新闻_链接.md → [(source, title)]，保持文件顺序（即前 10 选择序）。"""
    out = []
    for m in H3_RE.finditer(md_text):
        out.append({"src": m.group(1).strip(), "title": m.group(2).strip()})
    return out


def agreement_report(sel_a: list[dict], sel_b: list[dict]) -> dict:
    """前 10 选择 + 栏目分配一致率。

    一致 = 同一条目（标题归一化后相等）出现在两边的同一位置（序号相同）。
    栏目信息在 1新闻_链接.md 里只体现为 section 分组，条目按栏目顺序排列，
    因此"同一位置"同时约束了选择与栏目归属；栏目名本身从 section 标题解析，
    供报告展示。
    """
    def norm(t: str) -> str:
        return re.sub(r"\s+", "", t)

    a_map = {norm(x["title"]): i for i, x in enumerate(sel_a)}
    b_map = {norm(x["title"]): i for i, x in enumerate(sel_b)}
    common = set(a_map) & set(b_map)
    same_pos = sum(1 for k in common if a_map[k] == b_map[k])
    union = len(set(a_map) | set(b_map))
    return {
        "count_a": len(sel_a),
        "count_b": len(sel_b),
        "common": len(common),
        "same_position": same_pos,
        "jaccard": round(len(common) / union, 3) if union else 1.0,
        "position_agreement": round(same_pos / len(common), 2) if common else 0.0,
        "only_a": [x["title"] for x in sel_a if norm(x["title"]) not in b_map],
        "only_b": [x["title"] for x in sel_b if norm(x["title"]) not in a_map],
    }


def parse_summaries(md_text: str) -> list[dict]:
    """解析 3新闻_概述.md → [{src, title, summary}]（按出现顺序）。"""
    out = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^###\s+\[(.+?)\]\s+(.+)$", lines[i])
        if m:
            src, title = m.group(1).strip(), m.group(2).strip()
            summary_lines = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith("###") and not lines[j].startswith("## "):
                if lines[j].strip():
                    summary_lines.append(lines[j].strip())
                j += 1
            out.append({"src": src, "title": title, "summary": "".join(summary_lines)})
            i = j
        else:
            i += 1
    return out


# ────────────────────────── A/B 编排 ──────────────────────────

def check_backend(port: int) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def prepare_sandbox(sandbox: Path, date_str: str) -> None:
    """把冻结输入拷入沙箱目录结构。"""
    src_dir = DAILY_BASE / date_str
    for name in ("0新闻_粗筛.md", "2新闻_已审核.md"):
        src = src_dir / name
        if not src.exists():
            raise FileNotFoundError(f"冻结输入缺失: {src}")
    (sandbox / date_str).mkdir(parents=True, exist_ok=True)
    for name in ("0新闻_粗筛.md", "2新闻_已审核.md"):
        shutil.copy2(src_dir / name, sandbox / date_str / name)


def run_leg(provider: str, date_str: str, sandbox: Path, leg_dir: Path) -> dict:
    """对一个 provider 跑 step4+step7（沙箱输出），返回计时与产物快照路径。"""
    env = dict(os.environ)
    env["DAILY_OUTPUT_DIR"] = str(sandbox)

    yaml_path = REPO / "llm.yaml"
    original = yaml_path.read_text(encoding="utf-8")
    try:
        atomic_write_text(yaml_path, switch_provider(original, provider))
        results = {}
        for step, outfile in (("step4.py", STEP4_OUTPUT), ("step7.py", STEP7_OUTPUT)):
            print(f"  ▶ python3 {step} --date {date_str}  (provider={provider})", flush=True)
            t0 = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, str(REPO / step), "--date", date_str],
                cwd=REPO, env=env, capture_output=True, text=True,
                timeout=STEP_TIMEOUT_S,
            )
            wall = time.perf_counter() - t0
            log_path = leg_dir / f"{step}.log"
            log_path.write_text(proc.stdout + "\n===== STDERR =====\n" + proc.stderr,
                                encoding="utf-8")
            results[step] = {"wall_s": round(wall, 1), "returncode": proc.returncode}
            print(f"    exit={proc.returncode} wall={wall:.1f}s → {log_path.name}", flush=True)
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout)[-800:]
                raise RuntimeError(f"{step} 失败 (exit={proc.returncode}):\n{tail}")
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"{step} 超时 (>={STEP_TIMEOUT_S}s)，判定后端异常: {e}") from e
    finally:
        atomic_write_text(yaml_path, original)  # 恢复原始 provider

    out1 = sandbox / date_str / STEP4_OUTPUT
    out3 = sandbox / date_str / STEP7_OUTPUT
    if out1.exists():
        shutil.copy2(out1, leg_dir / STEP4_OUTPUT)
    if out3.exists():
        shutil.copy2(out3, leg_dir / STEP7_OUTPUT)
    return results


def main():
    args = parse_args()
    date_str = args.date
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else Path(tempfile.gettempdir()) / "daily_bench_ab" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    # 前置检查
    ports = {"kvmem": 27182, "qwen-local": 8899}
    for p in providers:
        if p not in ports:
            print(f"⚠ provider {p} 无已知端口，跳过后端健康检查")

    if args.dry_run:
        sandbox = out_dir / "sandbox"
        prepare_sandbox(sandbox, date_str)
        print(f"[dry-run] 沙箱就绪: {sandbox}")
        print(f"[dry-run] 结果目录: {out_dir}")
        return

    sandbox = out_dir / "sandbox"
    prepare_sandbox(sandbox, date_str)
    print(f"沙箱: {sandbox}")
    print(f"结果: {out_dir}\n")

    lock = acquire_lock(date_str)
    import signal
    signal.signal(signal.SIGTERM, _sigterm_to_keyboardinterrupt)

    # 备份生产归档 jsonl（唯一污染点）；不存在也要在结束后清理新建的分片
    archive_jsonl = archive_jsonl_path(date_str)
    backup = None
    if archive_jsonl.exists():
        backup = out_dir / f"{date_str[:7]}.jsonl.bak"
        shutil.copy2(archive_jsonl, backup)
        print(f"已备份生产归档: {archive_jsonl} → {backup}")
    else:
        print(f"⚠ 生产归档分片不存在: {archive_jsonl}（跑动中会新建，结束后删除）")

    leg_results = {}
    try:
        for provider in providers:
            port = ports.get(provider)
            if port and not check_backend(port):
                raise RuntimeError(
                    f"provider {provider} 的后端 127.0.0.1:{port} 未在线"
                    f"（kvmem: bash start-llm.sh kvmem / qwen-local: bash start-llm.sh）")
            print(f"\n═══ Leg: {provider} ═══")
            leg_dir = out_dir / provider
            leg_dir.mkdir(parents=True, exist_ok=True)
            leg_results[provider] = run_leg(provider, date_str, sandbox, leg_dir)

            # 跑完一个 leg 立即恢复归档，再跑下一个（归档不参与 leg 间对比）
            if backup:
                restore_archive(backup, archive_jsonl)
            # 清掉本 leg 产物，下一个 leg 从纯冻结输入开始
            for name in (STEP4_OUTPUT, STEP7_OUTPUT):
                (sandbox / date_str / name).unlink(missing_ok=True)
    finally:
        # 恢复生产归档 + 清理 llm.yaml（run_leg 的 finally 已恢复 provider 行）
        if backup:
            restore_archive(backup, archive_jsonl)
            print(f"\n已恢复生产归档 ← {backup}")
        elif archive_jsonl.exists():
            archive_jsonl.unlink()
            print(f"\n已删除实验新建的归档分片: {archive_jsonl}")
        try:
            cur = (REPO / "llm.yaml").read_text(encoding="utf-8")
            (out_dir / "llm.yaml.after.json").write_text(
                json.dumps({"provider_line": next(
                    (l for l in cur.splitlines() if l.startswith("provider:")), "?")},
                    ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass  # 状态快照失败不吞原始异常
        finally:
            release_lock(lock)

    # 一致率报告（第一个 provider 为基准 A）；失败时也尽力写 partial summary
    summary = {"date": date_str, "providers": providers, "legs": {}}
    a_name = providers[0]
    a_sel_path = out_dir / a_name / STEP4_OUTPUT
    a_sel = parse_selection(a_sel_path.read_text("utf-8")) if a_sel_path.exists() else []
    for provider in providers:
        sel_path = out_dir / provider / STEP4_OUTPUT
        sum_path = out_dir / provider / STEP7_OUTPUT
        entry = {"step_timing": leg_results.get(provider, {"error": "leg 未完成"})}
        if sel_path.exists():
            sel = parse_selection(sel_path.read_text("utf-8"))
            entry["selection"] = sel
            entry["agreement_vs_first"] = agreement_report(a_sel, sel) if provider != a_name else None
        if sum_path.exists():
            entry["summaries"] = parse_summaries(sum_path.read_text("utf-8"))
        summary["legs"][provider] = entry

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ A/B 完成: {out_dir / 'summary.json'}")

    for provider in providers:
        e = summary["legs"][provider]
        s4, s7 = e["step_timing"]["step4.py"], e["step_timing"]["step7.py"]
        print(f"  {provider}: step4 {s4['wall_s']}s + step7 {s7['wall_s']}s "
              f"= {s4['wall_s'] + s7['wall_s']}s")
        ag = e.get("agreement_vs_first")
        if ag:
            print(f"    与 {a_name} 一致率: 共同 {ag['common']} 条, "
                  f"同位置 {ag['same_position']} 条 ({ag['position_agreement']:.0%}), "
                  f"Jaccard {ag['jaccard']}")


if __name__ == "__main__":
    main()
