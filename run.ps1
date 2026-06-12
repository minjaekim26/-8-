$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "패키지 확인 중..." -ForegroundColor Cyan
python -m pip install -r requirements.txt -q

Write-Host "웹 앱 실행: http://localhost:8501" -ForegroundColor Green
python -m streamlit run app.py
