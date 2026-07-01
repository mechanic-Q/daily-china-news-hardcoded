#!/usr/bin/env python3
"""手动冒烟测试：对比 Phase 15A 重构前后 dry-run 输出。"""

import argparse
import subprocess
import sys
from pathlib import Path

KEY_SEGMENTS = ["═══ 预览", "═══ Step", "═══ 处理完成", "⏱ ", "✅"]


def extract_segments(text: str) -> str:
    lines = text.splitlines()
    out = []
    for line in lines:
        for seg in KEY_SEGMENTS:
            if seg in line:
                out.append(line)
                break
    return "\n".join(out)


def run_baseline(date: str, baseline_file: Path):
    result = subprocess.run(
        ["./run_all.sh", "--date", date, "--dry-run"],
        capture_output=True, text=True, timeout=300
    )
    output = result.stdout + result.stderr
    segments = extract_segments(output)
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    baseline_file.write_text(segments, encoding="utf-8")
    print(f"基线已写入: {baseline_file}")


def run_diff(date: str, baseline_file: Path):
    if not baseline_file.exists():
        print(f"基线文件不存在: {baseline_file}，请先 --baseline")
        sys.exit(1)
    baseline = baseline_file.read_text(encoding="utf-8")
    result = subprocess.run(
        ["./run_all.sh", "--date", date, "--dry-run"],
        capture_output=True, text=True, timeout=300
    )
    current = extract_segments(result.stdout + result.stderr)
    if baseline == current:
        print("✅ dry-run 输出与 baseline 一致")
        sys.exit(0)
    else:
        blines = baseline.splitlines()
        clines = current.splitlines()
        diffs = []
        for i, (a, b) in enumerate(zip(blines, clines)):
            if a != b:
                diffs.append(f"-{a}\n+{b}")
        if len(blines) != len(clines):
            diffs.append(f"行数差异: baseline {len(blines)} vs current {len(clines)}")
        print(f"❌ 发现 {len(diffs)} 处差异:")
        for d in diffs:
            print(d)
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="Phase 15A dry-run diff smoke test")
    p.add_argument("--baseline", action="store_true", help="生成基线文件")
    p.add_argument("--diff", action="store_true", help="对比基线")
    p.add_argument("--date", default="2026-06-30", help="运行日期")
    p.add_argument("--baseline-file", default=".baseline/dry-run-baseline.txt", help="基线文件路径")
    args = p.parse_args()

    baseline_path = Path(args.baseline_file)

    if args.baseline:
        run_baseline(args.date, baseline_path)
    elif args.diff:
        run_diff(args.date, baseline_path)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
