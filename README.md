# 룸메이트 매칭

성향 기반 룸메이트 매칭 챗봇 (Gemini API)

## 로컬 실행 (웹)

```powershell
pip install -r requirements.txt
$env:GEMINI_API_KEY = "your-api-key"
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

## Streamlit Cloud 배포 (GitHub 연동)

1. https://share.streamlit.io 에서 GitHub 로그인
2. Repository: `minjaekim26/-8-`, Branch: `main`, Main file: `app.py`
3. **Secrets**에 추가:

```toml
GEMINI_API_KEY = "your-api-key"
```

4. Deploy

`main` 브랜치에 푸시할 때마다 자동으로 다시 배포됩니다.

## 터미널 버전

```powershell
python roommate_match_chat.py
```
