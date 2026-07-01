#!/usr/bin/env python3
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from daily.common import BASE_DIR
STEPS = ["step1_3.py", "step4.py", "step6.py", "step7.py", "step8.py"]

def parse_args():
    dry = "--dry-run" in sys.argv
    date_str = None
    output_dir = None
    i = 0
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
            i += 2
            continue
        if a == "--dry-run":
            dry = True
            i += 1
            continue
        if a == "--output-dir" and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
            continue
        i += 1
    if date_str:
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"错误: 日期格式无效: {date_str}")
            sys.exit(1)
    else:
        dt = datetime.date.today()
    date_str = dt.strftime("%Y-%m-%d")
    default_dir = BASE_DIR / date_str / "perf"
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = default_dir
    return dt, date_str, dry, out_path


def tail_text(text, max_chars=200):
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return "...\n" + text[-max_chars:]


def build_md_report(report):
    lines = [f"# 性能报告 — {report['date']}\n"]
    lines.append(f"- dry_run: {report['dry_run']}")
    lines.append(f"- 总耗时: {report['total_duration_s']:.1f}s\n")
    lines.append("## 步骤耗时\n")
    lines.append("| step | duration_s | exit_code |")
    lines.append("|------|-----------|-----------|")
    for s in report["steps"]:
        lines.append(f"| {s['name']} | {s['duration_s']:.1f} | {s['exit_code']} |")
    lines.append("")
    lines.append("## 最慢步骤\n")
    for rank, step_name in enumerate(report["slowest"], 1):
        lines.append(f"{rank}. {step_name}")
    return "\n".join(lines)


def run_profiler(today, date_str, dry_run, output_dir):
    started_at = datetime.datetime.utcnow().isoformat() + "Z"
    steps_data = []
    total_start = time.perf_counter()

    for step_name in STEPS:
        step_start = time.perf_counter()
        step_started = datetime.datetime.utcnow().isoformat() + "Z"
        cmd = ["python3", step_name, "--date", date_str]
        if dry_run:
            cmd.append("--dry-run")

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            exit_code = proc.returncode
            stdout_tail = tail_text(proc.stdout)
            stderr_tail = tail_text(proc.stderr)
        except subprocess.TimeoutExpired:
            exit_code = -1
            stdout_tail = ""
            stderr_tail = "TIMEOUT"
        except Exception as e:
            exit_code = -2
            stdout_tail = ""
            stderr_tail = str(e)

        step_end = time.perf_counter()
        step_ended = datetime.datetime.utcnow().isoformat() + "Z"
        duration = step_end - step_start

        steps_data.append({
            "name": step_name,
            "command": cmd,
            "started_at": step_started,
            "ended_at": step_ended,
            "duration_s": round(duration, 3),
            "exit_code": exit_code,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        })

        if exit_code != 0:
            break

    total_end = time.perf_counter()
    ended_at = datetime.datetime.utcnow().isoformat() + "Z"
    total_duration = total_end - total_start

    by_duration = sorted(steps_data, key=lambda x: -x["duration_s"])
    slowest = [s["name"] for s in by_duration]
    if not slowest:
        slowest = [""]

    report = {
        "date": date_str,
        "dry_run": dry_run,
        "started_at": started_at,
        "ended_at": ended_at,
        "total_duration_s": round(total_duration, 3),
        "steps": steps_data,
        "slowest": slowest,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{date_str}-profile.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = output_dir / f"{date_str}-profile.md"
    md_path.write_text(build_md_report(report), encoding="utf-8")

    print(f"\n✅ 报告已写入: {json_path}")
    print(f"✅ 报告已写入: {md_path}")
    last_failed = next((s for s in steps_data if s["exit_code"] != 0), None)
    sys.exit(last_failed["exit_code"] if last_failed else 0)


def main():
    dt, date_str, dry_run, output_dir = parse_args()
    print(f"═══ Phase 12 性能量化 ═══")
    print(f"日期: {date_str}  dry_run: {dry_run}")
    print(f"输出: {output_dir}\n")
    run_profiler(dt, date_str, dry_run, output_dir)


if __name__ == "__main__":
    main()
