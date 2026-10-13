# run_all.ps1 — PowerShell 薄入口：把参数原样转发给 run_all.sh，逻辑单一真源仍是 bash
# 用法: .\run_all.ps1 --date 2026-10-13 --dry-run     或  .\run_all.ps1 （默认今天）
# 防御两个实测坑（2026-10-13）:
#   1) PowerShell 独立 PATH 下 `bash` 常解析到 System32 的 WSL bash —— 它不容忍 CRLF，
#      且 taskkill/nohup/netstat 等 Windows 工具语义全缺失，必须强制选 Git 的 MSYS bash；
#   2) *.sh 由 .gitattributes 锁定 eol=lf —— MSYS bash 虽容忍 CRLF，其他 bash 不容忍。
$ErrorActionPreference = "Stop"

# 候选顺序: Git 已知安装位优先（确定性命中，不惊动 WSL），再收 PATH 上非 WSL 的 bash
# 注意必须保持数组语义: 单元素时管道输出退化为标量, 字符串 += 数组会拼成坏路径
$known = @(
    "$env:ProgramFiles\Git\bin\bash.exe",
    "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
    "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe"
) | Where-Object { $_ -and (Test-Path $_) }
$fromPath = @(Get-Command bash.exe -All -ErrorAction SilentlyContinue |
    Where-Object { $_.Source -notmatch '\\System32\\|\\WindowsApps\\' } |
    Select-Object -ExpandProperty Source)
$candidates = @($known) + $fromPath

# uname 甄别: Git/MSYS bash 返回 MINGW*/MSYS*，WSL bash 返回 Linux
$bash = $null
foreach ($c in $candidates) {
    $u = & $c -c 'uname -s' 2>$null
    if ($u -match '^(MINGW|MSYS|CYGWIN)') { $bash = $c; break }
}
if (-not $bash) {
    Write-Error "未找到 Git for Windows 的 bash.exe（PATH 上的 bash 是 WSL，已按设计排除）；请确认 Git 安装位置"
    exit 1
}
if ($env:RUN_ALL_DEBUG) { Write-Host "  [shim] bash=$bash" }

# 先切到脚本所在目录: run_all.sh 用 dirname $0 定位 venv/start-llm.sh，相对路径最稳
Push-Location $PSScriptRoot
try {
    & $bash ./run_all.sh @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
