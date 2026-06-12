# 룸메이트 매칭

성향 기반 룸메이트 매칭 (API 없음, 후보 5,000명)

- **1단계:** 폼으로 본인 정보 입력
- **2단계:** 채팅으로 룸메이트 선호·중요도 입력 (규칙 기반 파싱)
- **결과:** 상위 5명 추천 + 요약 설명

## 로컬 실행 (웹)

```powershell
cd C:\Users\selen\Projects\-8-
pip install -r requirements.txt
python -m streamlit run app.py
```

브라우저: **http://localhost:8501**

`streamlit` 명령이 안 되면 `python -m streamlit` 을 사용하세요.  
또는 `.\run.ps1` 실행.

**API 키 설정 불필요**

## Streamlit Cloud 배포

1. https://share.streamlit.io → GitHub `minjaekim26/-8-`
2. Main file: `app.py`
3. Deploy (Secrets 없이 동작)

## 후보 데이터 재생성

```powershell
python generate_candidates.py
```

`roommate_candidates.csv` (기본 5,000명)를 만듭니다. 앱은 이 파일을 우선 사용합니다.

## 터미널 버전

```powershell
python roommate_match_chat.py
```

터미널은 본인 정보도 채팅(규칙 파싱)으로 받습니다.

## 채팅 답변 예시 (2단계)

| 질문 | 답변 예 |
|------|---------|
| 성별 선호 | `남성` / `여성` / `상관없음` |
| 흡연 선호 | `비흡연만` / `흡연도 괜찮음` / `상관없음` |
| 나이대 | `20~25` 또는 `23` |
| 중요도 | `3` (1~5) |
