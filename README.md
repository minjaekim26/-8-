# 룸메이트 매칭 (Roommate Match)

수면·생활 습관 데이터를 기반으로 **나와 잘 맞는 룸메이트 후보**를 추천하는 프로젝트입니다.  
**외부 AI API 없이** 동작하며, 웹(Streamlit)과 터미널 두 가지 방식으로 사용할 수 있습니다.

- 저장소: https://github.com/minjaekim26/-8-
- 후보 풀: **5,000명** (`roommate_candidates.csv`)
- 추천 결과: 조건에 맞는 상위 **5명** + 요약 설명

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 본인 정보 입력 | 웹: 폼 / 터미널: 채팅 (규칙 파싱) |
| 룸메이트 선호 입력 | 성별·흡연·나이대 필터 + 중요도(가중치) |
| 가중치 매칭 | 흡연, 청소, 음식, 소음, 나이, 수면, 활동량 반영 |
| 대량 후보 풀 | 5,000명 합성 프로필에서 검색 |
| API 불필요 | Gemini/OpenAI 키 설정 없음 |

---

## 사용 흐름

### 웹 (`app.py`)

```
1단계 [폼]  본인 정보 입력
    ↓
2단계 [채팅]  룸메이트 선호·중요도 (최대 6문항)
    ↓
결과  상위 5명 표 + 매칭 요약
```

### 터미널 (`roommate_match_chat.py`)

```
1단계 [채팅]  본인 정보 6문항
    ↓
2단계 [채팅]  룸메이트 선호 6문항
    ↓
결과  터미널에 후보 리스트 출력
```

---

## 프로젝트 구조

```
-8-/
├── app.py                          # Streamlit 웹 앱 (메인)
├── roommate_match_chat.py          # 매칭 엔진, 채팅 로직, 데이터 로딩
├── generate_candidates.py          # 후보 5,000명 CSV 생성 스크립트
├── roommate_candidates.csv         # 확장 후보 데이터 (앱이 우선 사용)
├── Sleep_health_and_lifestyle_dataset.csv  # 원본 시드 데이터 (374명)
├── requirements.txt
├── run.ps1 / run.bat               # Windows 실행 스크립트
├── .streamlit/config.toml          # Streamlit 테마
├── sleep-health-and-lifestyle.ipynb  # 데이터 분석 노트북
└── README.md
```

---

## 설치 및 실행

### 사전 요구사항

- Python 3.10 이상 권장
- `pip`

### 1) 저장소 클론

```powershell
git clone https://github.com/minjaekim26/-8-.git
cd -8-
```

### 2) 패키지 설치

```powershell
pip install -r requirements.txt
```

의존성: `pandas`, `streamlit`

### 3) 웹 실행

```powershell
python -m streamlit run app.py
```

브라우저에서 **http://localhost:8501** 접속

> `streamlit` 명령이 인식되지 않으면 반드시 `python -m streamlit` 사용  
> 또는 `.\run.ps1` / `run.bat` 더블클릭

### 4) 터미널 실행

```powershell
python roommate_match_chat.py
```

실행 시 `후보 풀: 5000명 로드` 메시지가 표시됩니다.

---

## 1단계 · 본인 정보 (웹 폼)

| 항목 | 입력 방식 | 값 예시 |
|------|-----------|---------|
| 성별 | 선택 | 남성 / 여성 |
| 나이 | 숫자 | 23 |
| 흡연 | 선택 | 비흡연 / 흡연 |
| 청소 습관 | 선택 | 매일 / 주 2~3회 / 주 1회 / 거의 안 함 |
| 방 안 음식 | 선택 | 불가 / 간식·음료 / 배달·식사까지 |
| 소음 민감도 | 슬라이더 | 1(둔감) ~ 5(예민) |

폼 제출 후 **2단계 채팅**으로 자동 이동합니다.

---

## 2단계 · 룸메이트 선호 (채팅)

질문은 **최대 6개**, 같은 항목은 반복하지 않습니다.  
아래 형식에 맞게 짧게 답하면 인식됩니다.

| 순서 | 질문 주제 | 답변 예시 |
|------|-----------|-----------|
| 1 | 선호 성별 | `남성` / `여성` / `상관없음` |
| 2 | 흡연 선호 | `비흡연만` / `흡연도 괜찮음` / `상관없음` |
| 3 | 나이대 | `20~25` 또는 `23` |
| 4 | 흡연 중요도 | `1` ~ `5` |
| 5 | 청소 중요도 | `1` ~ `5` |
| 6 | 소음·생활패턴 중요도 | `1` ~ `5` |

인식 실패 시 ⚠️ 안내 메시지가 나오며, 같은 질문을 다시 답하면 됩니다.

---

## 매칭 방식 (요약)

1. **필터**: 선호 성별, 흡연, 나이대에 맞는 후보만 남김
2. **점수 계산**: 아래 항목을 가중치와 비교해 점수화
   - 흡연 여부, 청소 습관, 방 안 음식
   - 소음 민감도, 나이 차이, 수면 시간, 일일 걸음 수
3. **정렬**: 점수 높은 순으로 상위 5명 추천
4. **설명**: API 없이 규칙 기반 요약 문장 생성

---

## 후보 데이터

| 파일 | 설명 |
|------|------|
| `Sleep_health_and_lifestyle_dataset.csv` | Kaggle 기반 원본 (374명) |
| `roommate_candidates.csv` | 합성 확장 후보 (**5,000명**, 기본 사용) |

앱은 `roommate_candidates.csv`가 있으면 **자동으로 우선 로드**합니다.  
파일이 없으면 원본 CSV를 바탕으로 5,000명을 생성합니다.

### 후보 데이터 다시 만들기

```powershell
python generate_candidates.py
```

인원 수 변경: `roommate_match_chat.py` 상단의 `DEFAULT_CANDIDATE_COUNT` 수정 후 위 명령 실행.

---

## Streamlit Cloud 배포

1. https://share.streamlit.io 접속 → GitHub 로그인
2. **New app**
   - Repository: `minjaekim26/-8-`
   - Branch: `main`
   - Main file path: `app.py`
3. **Deploy**

- API 키(Secrets) **불필요**
- `roommate_candidates.csv`는 저장소에 포함되어 있어 별도 업로드 없이 동작
- `main` 브랜치에 push 시 자동 재배포

---

## 자주 묻는 문제

| 증상 | 해결 |
|------|------|
| `streamlit`을 찾을 수 없음 | `python -m streamlit run app.py` 사용 |
| 포트 8501 사용 중 | `python -m streamlit run app.py --server.port 8502` |
| 채팅 답변이 인식 안 됨 | 표에 있는 키워드 형식으로 짧게 답하기 |
| 후보가 너무 적게 나옴 | 필터(성별·흡연·나이)를 완화하거나 `상관없음` 선택 |
| 데이터 파일 없음 | `Sleep_health_and_lifestyle_dataset.csv` 또는 `roommate_candidates.csv` 확인 |

---

## 데이터·노트북

- `sleep-health-and-lifestyle.ipynb`: 수면·건강 데이터 EDA 및 전처리 예시
- 룸메이트 관련 컬럼(`Smoking`, `Cleaning_Habit` 등)은 원본에 없어 **합성 생성**됨

---

## 라이선스 / 데이터 출처

- 원본 데이터: Sleep Health and Lifestyle Dataset (Kaggle 등 공개 데이터 기반)
- 본 프로젝트의 확장 후보(`roommate_candidates.csv`)는 원본 분포를 참고한 **합성 데이터**입니다.

---

## 개발 메모

- 웹 UI: Streamlit (`app.py`)
- 매칭 로직: `roommate_match_chat.py`
- 외부 LLM API 미사용 (과거 Gemini 연동 코드는 제거됨)
- Windows 환경 기준으로 `run.ps1` 제공

---  
## 이론적 배경
- 1. Similarity-Attraction Theory

Similarity-Attraction Theory는 개인이 자신과 유사한 가치관, 태도, 성향을 가진 사람에게 더 높은 호감과 만족감을 느낀다고 설명하는 이론이다.

Byrne(1971)는 유사성이 인간관계 형성과 관계 만족도에 중요한 영향을 미친다고 제시하였다.

본 프로젝트는 해당 이론을 바탕으로 흡연 여부, 청소 습관, 음식 섭취 습관, 소음 민감도 등의 생활 습관 유사도를 계산하여 매칭 점수에 반영하였다.

참고문헌:
Byrne, D. (1971). The Attraction Paradigm. New York: Academic Press.

- 2. Sleep Quality and Well-Being

선행연구에서는 수면의 질과 수면 시간이 삶의 만족도, 정서적 안정, 주관적 안녕감과 밀접한 관련이 있는 것으로 보고된다.

본 프로젝트는 수면 시간(Sleep Duration), 수면의 질(Quality of Sleep), 스트레스 수준(Stress Level)을 활용하여 Happiness_Level을 계산하였다.

- 3. KCI 논문 적용

신지은 · 김정기 · 서은국 (2017)

「기숙사 만족도에 대한 예측 오류: 행복한 룸메이트의 과소평가된 가치」

해당 연구에서는 룸메이트 행복 수준이 기숙사 만족도를 가장 잘 예측하는 변수(β=0.41)로 나타났다.

본 프로젝트는 이를 반영하여 Happiness_Level에 가장 높은 가중치를 부여하였다.

