# 룸메이트 매칭

성향 기반 룸메이트 매칭 챗봇 (Gemini API)

## 로컬 실행 (웹)

Windows에서 `streamlit` 명령이 안 될 수 있습니다. **`python -m streamlit`** 을 사용하세요.

### API 키 발급

1. https://aistudio.google.com/apikey 접속
2. **Create API key** → `AIza...` 로 시작하는 키 복사
3. 아래 방법 중 하나로 설정 (채팅에 키를 올리지 마세요)

### 방법 1: 웹 화면에서 입력 (가장 쉬움)

```powershell
cd C:\Users\selen\Projects\-8-
python -m streamlit run app.py
```

브라우저 **왼쪽 사이드바** → `GEMINI_API_KEY` 입력 → **키 저장 및 연결**

### 방법 2: .env 파일

프로젝트 폴더에 `.env` 파일 생성:

```
GEMINI_API_KEY=AIza여기에실제키
```

### 방법 3: 실행 스크립트

```powershell
cd C:\Users\selen\Projects\-8-
$env:GEMINI_API_KEY = "AIza여기에실제키"
.\run.ps1
```

### 방법 2: 직접 실행

```powershell
cd C:\Users\selen\Projects\-8-
pip install -r requirements.txt
$env:GEMINI_API_KEY = "your-api-key"
python -m streamlit run app.py
```

브라우저에서 **http://localhost:8501** 로 접속합니다.

### 자주 나는 오류

| 증상 | 해결 |
|------|------|
| `streamlit`을 찾을 수 없음 | `streamlit run` 대신 `python -m streamlit run app.py` |
| `GEMINI_API_KEY` 없음 | 환경 변수 또는 `.env` 파일에 키 설정 |
| 포트 사용 중 | `python -m streamlit run app.py --server.port 8502` |

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
