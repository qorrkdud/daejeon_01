# daejeon_01 포크를 매일 자동으로 GitHub에 올리는 스크립트
# 윈도우 작업 스케줄러("daejeon_01 자동 업로드")가 매일 밤 23:10에 실행합니다. 직접 실행해도 됩니다.
#
# 하는 일
#   1. 바탕 화면 cardnews-bot의 새 파일·바뀐 파일을 포크의 cardnews-bot/ 폴더로 복사 (지우지는 않음)
#   2. 내 작업 폴더의 변경만 모음 (cardnews-bot/, claude-work/, alternativestereo-sponsored-content/, CLAUDE.md)
#   3. 비밀번호·API 키·토큰·전화번호·이메일·주민번호, 50MB 넘는 파일을 검사
#      → 하나라도 걸리면 올리지 않고 auto_push.log에 이유를 남김
#   4. 문제가 없으면 커밋하고 내 포크(origin main)에 올림
# 기록은 같은 폴더의 auto_push.log 에 남습니다 (GitHub에는 올라가지 않음).

$repo = Split-Path -Parent $PSScriptRoot
$git = "C:\Program Files\Git\cmd\git.exe"
$log = Join-Path $PSScriptRoot "auto_push.log"
$source = Join-Path $env:USERPROFILE "OneDrive\바탕 화면\cardnews-bot"
$myPaths = @("cardnews-bot", "claude-work", "alternativestereo-sponsored-content", "CLAUDE.md")
$now = Get-Date -Format "yyyy-MM-dd HH:mm"
$today = Get-Date -Format "yyyy-MM-dd"

function Write-Log($msg) {
    Add-Content -LiteralPath $log -Value "[$now] $msg" -Encoding UTF8
}
function Git { & $git -c core.quotepath=false @args }

Set-Location -LiteralPath $repo

# 0. 지금 브랜치가 main이 아니면 멈춤
$branch = (Git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "main") {
    Write-Log "main 브랜치가 아니라서($branch) 올리지 않았어요."
    exit 1
}

# 1. 바탕 화면 cardnews-bot → 포크 cardnews-bot 복사
if (Test-Path -LiteralPath $source) {
    robocopy $source (Join-Path $repo "cardnews-bot") /E /XD .git __pycache__ .venv venv /XF auto_push.log *.pyc .env /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Write-Log "cardnews-bot 복사 실패 (robocopy $LASTEXITCODE). 복사 없이 계속해요."
    }
}

# 2. 내 작업 폴더의 변경만 모으기
Git add -A -- $myPaths 2>$null
Git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    $ahead = Git rev-list --count "@{u}..HEAD" 2>$null
    if (-not $ahead -or [int]$ahead -eq 0) {
        Write-Log "바뀐 내용이 없어서 올리지 않았어요."
        exit 0
    }
    $count = "지난번에 못 올린"
} else {
    # 3. 민감 정보 검사
    $problems = @()
    $files = @(Git diff --cached --name-only --diff-filter=AM)
    foreach ($f in $files) {
        if ($f -match '(^|/)(\.env|.*\.env|.*\.key|.*\.pem|.*\.p12|.*\.pfx|id_rsa.*|id_ed25519.*)$' -or $f -match '(?i)secret|credential|password') {
            $problems += "비밀 파일로 보이는 이름: $f"
        }
        $item = Get-Item -LiteralPath (Join-Path $repo $f) -ErrorAction SilentlyContinue
        if ($item -and $item.Length -gt 50MB) {
            $problems += "50MB가 넘는 파일: $f ($([math]::Round($item.Length / 1MB, 1))MB)"
        }
    }
    $pattern = 'sk-[A-Za-z0-9_-]{20,}|sk-ant-|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{30,}|xox[bp]-|-----BEGIN [A-Z ]*PRIVATE KEY|(api[_-]?key|password|passwd|secret|token)["'']?\s*[:=]\s*["''][^"'']{6,}|01[016789][-. ]?[0-9]{3,4}[-. ]?[0-9]{4}|[0-9]{6}-[1-4][0-9]{6}|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.(com|net|kr|co\.kr|org)'
    $current = ""
    foreach ($line in (Git diff --cached -U0 --no-color)) {
        if ($line -like "+++ b/*") { $current = $line.Substring(6); continue }
        if ($current -eq "claude-work/auto_push.ps1") { continue }  # 검사 규칙이 적힌 이 스크립트 자체는 건너뜀
        if ($line.StartsWith("+") -and -not $line.StartsWith("+++")) {
            $m = [regex]::Match($line, $pattern)
            if ($m.Success -and $m.Value -notmatch '@example\.com$') {
                $problems += "$current 안에 의심되는 내용: $($m.Value.Substring(0, [math]::Min(12, $m.Value.Length)))..."
            }
        }
    }
    if ($problems.Count -gt 0) {
        Git reset -q
        Write-Log "민감 정보 검사에서 걸려서 올리지 않았어요. 확인할 것:"
        $problems | Select-Object -First 20 | ForEach-Object { Write-Log "  - $_" }
        exit 1
    }

    # 4. 커밋
    $count = $files.Count + @(Git diff --cached --name-only --diff-filter=D).Count
    Git commit -q -m "$today 자동 업로드 (파일 $count 개)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Log "커밋 실패"
        exit 1
    }
}

# 5. 내 포크로 올리기 (실패하면 30초 뒤 한 번 더)
$out = Git push -q origin main 2>&1
if ($LASTEXITCODE -ne 0) {
    Start-Sleep -Seconds 30
    $out = Git push -q origin main 2>&1
}
if ($LASTEXITCODE -ne 0) {
    Write-Log "올리기 실패: $out"
    exit 1
}
Write-Log "파일 $count 개를 GitHub(qorrkdud/daejeon_01)에 올렸어요."
