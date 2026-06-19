# Pull Request 기록 (minjaekim → main)

## PR 목록

| PR | 제목 | 상태 | 링크 |
|----|------|------|------|
| **#1** | Update README.md | **Merged** (머지 완료) | https://github.com/minjaekim26/-8-/pull/1 |
| **#2** | 룸메이트 매칭 시스템 및 KCI 논문 반영 (김민재) | **Open** | https://github.com/minjaekim26/-8-/pull/2 |

> Open PR 탭에 안 보이면 **Pull requests → Closed** 또는 위 링크로 직접 접속하세요.  
> #1은 이미 main에 머지되어 **Closed** 목록에 있습니다.

---

## 작업 요약 (김민재 · minjaekim 브랜치)

- 생활 습관 기반 **룸메이트 매칭 시스템** (Streamlit 웹 + 터미널 채팅)
- Kaggle 수면·건강 데이터 기반 **5,000명 합성 후보** (`roommate_candidates.csv`)
- **KCI 논문**(신지은 et al., 2017) 반영: `Happiness_Level`, 논문 기반 가중치, UI 패널
- API 없이 규칙 기반 채팅 파싱

## 주요 파일

| 파일 | 설명 |
|------|------|
| `app.py` | Streamlit 웹 UI, KCI 논문 패널 |
| `roommate_match_chat.py` | 매칭 엔진, 채팅 파싱 |
| `kci_research.py` | KCI 논문 상수·UI 헬퍼 |
| `kci_research_data.csv` | 논문 4요인 수치 |
| `roommate_candidates.csv` | 5,000명 후보 |
| `PROJECT_FILES.txt` | 파일 설명·발표 대본 |

## Test plan

- [ ] `pip install -r requirements.txt`
- [ ] `python -m streamlit run app.py`
- [ ] 매칭 결과·KCI 가중치 패널 확인
- [ ] `python roommate_match_chat.py`

## 참고

- 실행 영상: https://youtu.be/VZ1622BGEZo
- 논문: 신지은, 김정기, 서은국 (2017). 기숙사 만족도에 대한 예측 오류.
