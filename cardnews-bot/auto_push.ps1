# 매일 자동으로 GitHub에 올리는 스크립트
# 윈도우 작업 스케줄러가 매일 밤 실행합니다. 직접 실행해도 됩니다.
# 기록은 같은 폴더의 auto_push.log 에 남습니다 (GitHub에는 올라가지 않음).

Set-Location -LiteralPath $PSScriptRoot
$git = "C:\Program Files\Git\cmd\git.exe"
$log = Join-Path $PSScriptRoot "auto_push.log"
$now = Get-Date -Format "yyyy-MM-dd HH:mm"
$today = Get-Date -Format "yyyy-MM-dd"

function Write-Log($msg) {
    Add-Content -LiteralPath $log -Value "[$now] $msg" -Encoding UTF8
}

& $git add -A 2>$null
& $git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    # 새 변경은 없지만, 전에 올리기에 실패한 커밋이 남아 있으면 다시 올립니다
    $ahead = & $git rev-list --count "@{u}..HEAD" 2>$null
    if (-not $ahead -or [int]$ahead -eq 0) {
        Write-Log "바뀐 내용이 없어서 올리지 않았어요."
        exit 0
    }
    $count = "지난번에 못 올린"
} else {
    $count = (& $git diff --cached --name-only | Measure-Object -Line).Lines
    & $git commit -q -m "$today 자동 업로드 (파일 $count 개)" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Log "커밋 실패"
        exit 1
    }
}

$out = & $git push -q 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "올리기 실패: $out"
    exit 1
}
Write-Log "파일 $count 개를 GitHub에 올렸어요."
