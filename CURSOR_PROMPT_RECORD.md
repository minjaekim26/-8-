# Cursor AI 프롬프트 기록 (PR #2)

- **도구:** Cursor IDE Agent (AI 코딩 어시스턴트)
- **프로젝트:** 룸메이트 매칭 시스템 (`minjaekim26/-8-`)
- **브랜치:** `minjaekim`
- **관련 PR:** [#2](https://github.com/minjaekim26/-8-/pull/2)

> 아래는 개발 과정에서 Cursor AI에게 입력한 사용자 프롬프트와 주요 결과 요약입니다.

---

## 1. 저장소·배포

| # | 사용자 프롬프트 | 주요 결과 |
|---|----------------|-----------|
| 1 | GitHub에서 가져와 / `https://github.com/minjaekim26/-8-.git` 여기서 가져와 | 로컬에 저장소 클론·동기화 |
| 2 | 깃에 새로 푸싱해서 새로고침해줘 | 원격 저장소에 푸시 |
| 3 | 저장된내용 깃에 푸싱해줘 기존에 있던거 덮고 | 변경사항 force push 반영 |
| 4 | 일단 웹사이트 만들어진거 깃에 푸싱해줘 | Streamlit 앱 GitHub 업로드 |
| 5 | 깃에 덮어씌운거지? | 푸시 완료 확인 |
| 6 | 깃에 업데이트 해주고 PROJECT_FILES.txt에도 설명 업데이트 해줘 | KCI 연동 커밋·문서 갱신 |
| 7 | 올려줘 | KCI UI 변경 GitHub 푸시 |

---

## 2. API·채팅 구조 변경

| # | 사용자 프롬프트 | 주요 결과 |
|---|----------------|-----------|
| 8 | OpenAI API → Gemini API로 바꿔줘 | `roommate_match_chat.py` Gemini 연동 |
| 9 | (Gemini API 키 제공) 넣고 실행시켜줘 | API 키 설정·실행 (이후 API 제거) |
| 10 | 터미널에 뜬 오류 뭐야 | 429 quota 등 오류 설명 |
| 11 | 질문 사이에 시간을 두면 되나 / 얼마나? | Rate limit 대응 안내 |
| 12 | 질문 언제까지 해야 결과가 나오는지 | 매칭 완료 조건 설명 |
| 13 | 질문 잘 안 겹치게, 10개 이상 안 하도록 | `MAX_MATCHING_QUESTIONS = 6` 등 |
| 14 | 내 정보 우선 입력 → 추가 질문으로 매칭 | 2단계 구조(프로필→선호) |
| 15 | API 안 쓰고 구현하고 싶은데 | API 의존성 제거 가능 안내 |
| 16 | 폼으로 기본정보 + 채팅으로 추가 방향성 | `app.py` 폼+채팅 UI |
| 17 | 채팅도 API 없이 | `parse_answer_rule()` 규칙 기반 파싱 |

---

## 3. 웹·실행·문서

| # | 사용자 프롬프트 | 주요 결과 |
|---|----------------|-----------|
| 18 | 웹사이트로 만들어줘 | `app.py` Streamlit 웹앱 |
| 19 | 로컬에서 실행이 안되는데 | `python -m streamlit run app.py`, `run.ps1` |
| 20 | API key invalid 오류 | 키 UI 추가 → 이후 API 전면 제거 |
| 21 | 내 깃에 있는 파일 실행시켜줘 | 로컬 Streamlit 실행 |
| 22 | 후보 데이터 많이 만들어서 적용 | 5,000명 `roommate_candidates.csv` |
| 23 | README 더 구체적으로 업데이트 | `README.md` 확장 |
| 24 | 터미널에서 실행시키는 과정 | 실행 방법 안내 |
| 25 | 각 파일 설명 텍스트 파일로 정리 | `PROJECT_FILES.txt` 추가 |
| 26 | 발표 대본 예시 써줘 | `PROJECT_FILES.txt` [9] 발표 대본 |

---

## 4. KCI 논문 반영

| # | 사용자 프롬프트 | 주요 결과 |
|---|----------------|-----------|
| 27 | `KCI_FI002229041.pdf`에서 데이터 추출해 프로젝트에 적용 | `kci_research_data.csv`, `KCI_FI002229041_추출.txt`, `Happiness_Level`, 가중치 반영 |
| 28 | 논문 반영 로직을 UI에서도 볼 수 있게 | KCI 패널·가중치 차트·결과 탭 (`app.py`, `kci_research.py`) |

---

## 5. 오류 수정

| # | 사용자 프롬프트 | 주요 결과 |
|---|----------------|-----------|
| 29 | `ImportError: cannot import name 'KCI_CITATION'` | `kci_research.py` 모듈 분리 |
| 30 | `NameError: MAX_MATCHING_QUESTIONS is not defined` | `app.py` import 누락 수정 |

---

## 6. 브랜치·PR

| # | 사용자 프롬프트 | 주요 결과 |
|---|----------------|-----------|
| 31 | 내가 만든 것들 minjaekim 브랜치에 추가할 수 있나 | `minjaekim` 브랜치에 푸시·머지 |
| 32 | 내 브랜치에 올라간 거지 그럼? | `origin/minjaekim` 확인 |
| 33 | PR 기록도 남겨야 해 | `PR_RECORD.md` 작성 |
| 34 | PR이 없는데? | PR #1 머지됨 확인 → **PR #2** 생성 |
| 35 | Merge pull request 하면 main으로 올라가는 거야? | PR 머지 → `main` 반영 설명 |
| 36 | PR2에 너랑 한 프롬프트 기록도 남겨줘 | 이 파일 (`CURSOR_PROMPT_RECORD.md`) |

---

## 최종 산출물 요약

```
app.py                    ← Streamlit 웹 (폼 + 채팅 + KCI UI)
roommate_match_chat.py    ← 매칭 엔진·채팅 파싱
kci_research.py           ← KCI 논문 UI/상수
kci_research_data.csv     ← 논문 수치 데이터
roommate_candidates.csv   ← 5,000명 후보
PROJECT_FILES.txt         ← 파일 설명·발표 대본
PR_RECORD.md              ← PR 기록
CURSOR_PROMPT_RECORD.md   ← Cursor AI 프롬프트 기록 (본 문서)
```

---

*작성: Cursor AI Agent와의 대화 기록 정리 (2026-06)*
