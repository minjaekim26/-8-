# Pull Request 기록 (minjaekim → main)

## PR 정보

| 항목 | 내용 |
|------|------|
| **PR 번호** | [#1](https://github.com/minjaekim26/-8-/pull/1) |
| **제목 (권장)** | 룸메이트 매칭 시스템 및 KCI 논문 반영 (김민재) |
| **브랜치** | `minjaekim` → `main` |
| **작성자** | 김민재 (minjaekim26) |
| **상태** | Open |

---

## Summary

- 생활 습관 기반 **룸메이트 매칭 시스템** 구현 (Streamlit 웹 + 터미널 채팅)
- Kaggle 수면·건강 데이터 기반 **5,000명 합성 후보** (`roommate_candidates.csv`)
- **KCI 논문**(신지은 et al., 2017) 반영: 룸메이트 행복 수준(`Happiness_Level`) 및 논문 기반 가중치 적용
- API 없이 규칙 기반 채팅 파싱으로 동작

## 주요 변경 파일

| 파일 | 설명 |
|------|------|
| `app.py` | Streamlit 웹 UI, KCI 논문 패널·가중치 차트 |
| `roommate_match_chat.py` | 매칭 엔진, 채팅 파싱, 데이터 로딩 |
| `kci_research.py` | KCI 논문 상수·UI 헬퍼 |
| `kci_research_data.csv` | 논문 4요인 수치·회귀계수 |
| `roommate_candidates.csv` | 5,000명 후보 (Happiness_Level 포함) |
| `generate_candidates.py` | 후보 데이터 생성 스크립트 |
| `PROJECT_FILES.txt` | 파일 설명·발표 대본 |

## Test plan

- [ ] `pip install -r requirements.txt`
- [ ] `python -m streamlit run app.py` → 1단계 폼 입력 후 2단계 채팅 진행
- [ ] 매칭 결과 표에 `Happiness_Level` 및 상위 5명 표시 확인
- [ ] 사이드바·「KCI 논문 기반 매칭 로직」패널에서 가중치 차트 확인
- [ ] `python roommate_match_chat.py` 터미널 모드 동작 확인

## 참고

- 실행 영상: https://youtu.be/VZ1622BGEZo
- 논문 출처: 신지은, 김정기, 서은국 (2017). 기숙사 만족도에 대한 예측 오류: 행복한 룸메이트의 과소평가된 가치.

---

> GitHub PR 본문에 위 Summary·Test plan 을 복사해 넣으면 제출용 기록으로 사용할 수 있습니다.
