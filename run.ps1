$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $env:GEMINI_API_KEY -and (Test-Path ".env")) {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*GEMINI_API_KEY\s*=\s*(.+)\s*$') {
            $env:GEMINI_API_KEY = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
}

if (-not $env:GEMINI_API_KEY) {
    Write-Host "GEMINI_API_KEY가 없습니다." -ForegroundColor Red
    Write-Host "다음 중 하나를 실행하세요:"
    Write-Host '  $env:GEMINI_API_KEY = "여기에_키"'
    Write-Host "또는 프로젝트 폴더에 .env 파일 생성 (GEMINI_API_KEY=키)"
    exit 1
}

Write-Host "패키지 확인 중..." -ForegroundColor Cyan
python -m pip install -r requirements.txt -q

Write-Host "웹 앱 실행: http://localhost:8501" -ForegroundColor Green
python -m streamlit run app.py
