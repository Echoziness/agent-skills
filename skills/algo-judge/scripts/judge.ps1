<#
.SYNOPSIS
  OJ 评测脚本 - 模拟 Online Judge 评测流程

.DESCRIPTION
  编译/运行用户代码，逐组与标准输出比对，报告 AC/WA/TLE/RE。
  支持语言：C, C++, Python, Java, Go, Rust, JavaScript

.PARAMETER ProblemDir
  题目目录（包含 testdata/ 和 user/ 子目录）

.PARAMETER UserCode
  用户代码文件路径（相对或绝对）

.PARAMETER TimeoutSec
  每组测试超时秒数，默认 5

.EXAMPLE
  ./judge.ps1 -ProblemDir "AI_Workspace/algo/two-sum" -UserCode "AI_Workspace/algo/two-sum/user/solution.cpp"
  ./judge.ps1 "AI_Workspace/algo/two-sum" "AI_Workspace/algo/two-sum/user/sol.py"
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$ProblemDir = ".",
    [Parameter(Position = 1)][string]$UserCode = "",
    [int]$TimeoutSec = 5
)

$ErrorActionPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Status {
    param([string]$Label, [string]$Text, [string]$Color = "White")
    Write-Host "[" -NoNewline
    Write-Host $Label -ForegroundColor $Color -NoNewline
    Write-Host "] $Text"
}

function Compare-Output {
    param([string]$ActualFile, [string]$ExpectedFile)

    $actualLines = (Get-Content $ActualFile -ErrorAction SilentlyContinue)
    $expectedLines = (Get-Content $ExpectedFile -ErrorAction SilentlyContinue)

    if ($null -eq $actualLines) { $actualLines = @() }
    if ($null -eq $expectedLines) { $expectedLines = @() }
    if ($actualLines -isnot [array]) { $actualLines = @($actualLines) }
    if ($expectedLines -isnot [array]) { $expectedLines = @($expectedLines) }

    # 去除每行首尾空白，过滤空行（保留结构：不跳过空行，只trim）
    $actualTrimmed = $actualLines | ForEach-Object { $_.Trim() }
    $expectedTrimmed = $expectedLines | ForEach-Object { $_.Trim() }

    if ($actualTrimmed.Count -ne $expectedTrimmed.Count) {
        return @{
            Match   = $false
            Detail  = "行数不同：实际 $($actualTrimmed.Count) 行，期望 $($expectedTrimmed.Count) 行"
            DiffLine = -1
            ActualDiff = ""
            ExpectedDiff = ""
        }
    }

    for ($i = 0; $i -lt $actualTrimmed.Count; $i++) {
        if ($actualTrimmed[$i] -ne $expectedTrimmed[$i]) {
            return @{
                Match   = $false
                Detail  = "第 $($i + 1) 行不一致"
                DiffLine = ($i + 1)
                ActualDiff   = $actualTrimmed[$i]
                ExpectedDiff = $expectedTrimmed[$i]
            }
        }
    }

    return @{ Match = $true }
}

# ── 解析路径 ──
$ProblemDir = Resolve-Path $ProblemDir -ErrorAction SilentlyContinue
if (-not $ProblemDir) {
    Write-Host "错误：题目目录不存在" -ForegroundColor Red
    exit 1
}

# 自动发现用户代码
if (-not $UserCode) {
    $userFiles = Get-ChildItem "$ProblemDir\user\*" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -match '\.(c|cpp|py|java|go|rs|js)$' }
    if ($userFiles.Count -eq 0) {
        Write-Host "错误：user/ 目录下没有可识别的代码文件" -ForegroundColor Red
        exit 1
    }
    if ($userFiles.Count -gt 1) {
        Write-Host "user/ 目录下有多个代码文件，请指定 -UserCode 参数：" -ForegroundColor Yellow
        $userFiles | ForEach-Object { Write-Host "  $($_.Name)" }
        exit 1
    }
    $UserCode = $userFiles[0].FullName
}
else {
    $UserCode = (Resolve-Path $UserCode -ErrorAction SilentlyContinue).Path
    if (-not $UserCode) {
        Write-Host "错误：用户代码文件不存在: $UserCode" -ForegroundColor Red
        exit 1
    }
}

$ext = [System.IO.Path]::GetExtension($UserCode).ToLower()
$workDir = "$ProblemDir\.judge_tmp"
$userDir = "$ProblemDir\user"
$testDir = "$ProblemDir\testdata"

# 检查测试数据
if (-not (Test-Path $testDir)) {
    Write-Host "错误：testdata/ 目录不存在" -ForegroundColor Red
    exit 1
}
$inputFiles = @(Get-ChildItem "$testDir\input_*.txt" -ErrorAction SilentlyContinue | Sort-Object Name)
if ($inputFiles.Count -eq 0) {
    Write-Host "错误：testdata/ 下没有 input_*.txt 文件" -ForegroundColor Red
    exit 1
}

New-Item $workDir -ItemType Directory -Force | Out-Null

# ── 编译 ──
$exePath = ""
$compileOk = $false

Write-Host ""
Write-Host "═══════════════════════════════════════" -ForegroundColor DarkGray
Write-Host "  OJ Judge - $(Split-Path $ProblemDir -Leaf)" -ForegroundColor Cyan
Write-Host "  语言: $ext  |  测试点: $($inputFiles.Count)  |  超时: ${TimeoutSec}s" -ForegroundColor DarkGray
Write-Host "═══════════════════════════════════════" -ForegroundColor DarkGray
Write-Host ""
Write-Host "编译中..." -NoNewline

switch ($ext) {
    ".c" {
        $exePath = "$workDir\solution.exe"
        $out = & gcc $UserCode -o $exePath -O2 -lm 2>&1
        if ($LASTEXITCODE -eq 0) { $compileOk = $true }
        else { Write-Host " 失败" -ForegroundColor Red; Write-Host $out }
    }
    ".cpp" {
        $exePath = "$workDir\solution.exe"
        $out = & g++ $UserCode -o $exePath -O2 -lm 2>&1
        if ($LASTEXITCODE -eq 0) { $compileOk = $true }
        else { Write-Host " 失败" -ForegroundColor Red; Write-Host $out }
    }
    ".py" {
        $exePath = $UserCode
        $compileOk = $true
    }
    ".java" {
        Copy-Item $UserCode "$workDir\" -Force
        $javaFile = Split-Path $UserCode -Leaf
        $out = & javac "$workDir\$javaFile" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $exePath = $javaFile -replace '\.java$', ''
            $compileOk = $true
        }
        else { Write-Host " 失败" -ForegroundColor Red; Write-Host $out }
    }
    ".go" {
        $exePath = "$workDir\solution.exe"
        $out = & go build -o $exePath $UserCode 2>&1
        if ($LASTEXITCODE -eq 0) { $compileOk = $true }
        else { Write-Host " 失败" -ForegroundColor Red; Write-Host $out }
    }
    ".rs" {
        $exePath = "$workDir\solution.exe"
        $out = & rustc $UserCode -o $exePath 2>&1
        if ($LASTEXITCODE -eq 0) { $compileOk = $true }
        else { Write-Host " 失败" -ForegroundColor Red; Write-Host $out }
    }
    ".js" {
        $exePath = $UserCode
        $compileOk = $true
    }
    default {
        Write-Host " 失败" -ForegroundColor Red
        Write-Host "不支持的语言: $ext" -ForegroundColor Red
    }
}

if (-not $compileOk) {
    Write-Host ""
    Write-Status "CE" "编译错误" "Red"
    Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host " 成功" -ForegroundColor Green
Write-Host ""

# ── 逐组评测 ──
$acCount = 0
$totalCount = $inputFiles.Count
$results = @()

foreach ($inp in $inputFiles) {
    $idx = if ($inp.Name -match 'input_(\d+)') { $Matches[1] } else { "?" }
    $outFile = "$testDir\output_$idx.txt"
    $userOut = "$workDir\output_$idx.txt"

    if (-not (Test-Path $outFile)) {
        Write-Status "ERR" "测试点 $idx：缺少 output_$idx.txt" "Yellow"
        $results += "ERR"
        continue
    }

    # 运行用户程序
    $timedOut = $false
    $proc = $null

    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.WorkingDirectory = $ProblemDir
        $psi.RedirectStandardInput = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true

        switch ($ext) {
            ".py" {
                $psi.FileName = "python"
                $psi.Arguments = $exePath
            }
            ".java" {
                $psi.FileName = "java"
                $psi.Arguments = "-cp `"$workDir`" $exePath"
            }
            ".js" {
                $psi.FileName = "node"
                $psi.Arguments = $exePath
            }
            default {
                $psi.FileName = $exePath
            }
        }

        $proc = [System.Diagnostics.Process]::Start($psi)

        # 写入 stdin
        $inputContent = [System.IO.File]::ReadAllText($inp.FullName)
        $proc.StandardInput.Write($inputContent)
        $proc.StandardInput.Close()

        # 读 stdout 到文件
        $stdout = $proc.StandardOutput.ReadToEnd()
        [System.IO.File]::WriteAllText($userOut, $stdout)

        $exited = $proc.WaitForExit($TimeoutSec * 1000)

        if (-not $exited) {
            $proc.Kill()
            $timedOut = $true
        }
    }
    catch {
        Write-Status "RE" "测试点 $idx：运行异常 - $_" "Red"
        $results += "RE"
        continue
    }

    if ($timedOut) {
        Write-Status "TLE" "测试点 $idx" "Yellow"
        $results += "TLE"
        continue
    }

    if ($proc.ExitCode -ne 0) {
        Write-Status "RE" "测试点 $idx（退出码 $($proc.ExitCode)）" "Red"
        $results += "RE"
        continue
    }

    # 比对输出
    $cmp = Compare-Output $userOut $outFile

    if ($cmp.Match) {
        Write-Status "AC" "测试点 $idx" "Green"
        $acCount++
        $results += "AC"
    }
    else {
        Write-Status "WA" "测试点 $idx - $($cmp.Detail)" "Red"
        if ($cmp.DiffLine -gt 0) {
            Write-Host "    期望: $($cmp.ExpectedDiff)" -ForegroundColor DarkYellow
            Write-Host "    实际: $($cmp.ActualDiff)" -ForegroundColor DarkYellow
        }
        elseif ($cmp.Detail) {
            Write-Host "    $($cmp.Detail)" -ForegroundColor DarkYellow
        }
        $results += "WA"
    }
}

# ── 汇总 ──
Write-Host ""
Write-Host "───────────────────────────────────────" -ForegroundColor DarkGray
$summaryColor = if ($acCount -eq $totalCount) { "Green" } elseif ($acCount -eq 0) { "Red" } else { "Yellow" }
Write-Host "  结果：$acCount / $totalCount 通过" -ForegroundColor $summaryColor
Write-Host "───────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# 清理临时文件
Remove-Item $workDir -Recurse -Force -ErrorAction SilentlyContinue

if ($acCount -eq $totalCount) { exit 0 } else { exit 1 }
