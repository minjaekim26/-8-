import os
import json
import random
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List

import pandas as pd
from openai import OpenAI  # pip install openai


# ==========================
# 1. 데이터 로딩 + 확장 컬럼
# ==========================

def add_roommate_features(df: pd.DataFrame) -> pd.DataFrame:
    """룸메이트 성향 관련 가상 컬럼 추가"""

    num_rows = len(df)

    # 흡연 여부 (0: 비흡연, 1: 흡연)
    df["Smoking"] = [random.choices([0, 1], weights=[80, 20])[0] for _ in range(num_rows)]

    # 청소 주기 (0: 매일, 1: 주 2-3회, 2: 주 1회, 3: 거의 안 함)
    df["Cleaning_Habit"] = [random.randint(0, 3) for _ in range(num_rows)]

    # 실내 취식 허용 범위 (0: 불가, 1: 음료/간식, 2: 배달음식까지)
    df["Eating_in_Room"] = [random.randint(0, 2) for _ in range(num_rows)]

    # 소음 민감도 (1: 둔감함 ~ 5: 매우 예민함)
    df["Noise_Sensitivity"] = [random.randint(1, 5) for _ in range(num_rows)]

    return df


def load_dataset(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = add_roommate_features(df)
    return df


# ==========================
# 2. 매칭 엔진 (가중치+필터)
# ==========================

def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    result = df.copy()

    gender = filters.get("Gender", None)
    if gender and gender.lower() != "any":
        result = result[result["Gender"].str.lower() == gender.lower()]

    smoking = filters.get("Smoking", None)
    if smoking in (0, 1):
        result = result[result["Smoking"] == smoking]

    age_min = filters.get("Age_min", None)
    age_max = filters.get("Age_max", None)
    if age_min is not None:
        result = result[result["Age"] >= age_min]
    if age_max is not None:
        result = result[result["Age"] <= age_max]

    return result


def match_score_weighted(
    a: Dict[str, Any],
    b: pd.Series,
    w: Dict[str, float],
) -> float:
    """
    a: user_profile (dict)
    b: candidate row (Series)
    w: weights
    """

    score = 0.0

    # 1. 흡연 여부
    if a["Smoking"] == 0 and b["Smoking"] == 0:
        score += 2 * w["smoking"]
    elif a["Smoking"] == 1 and b["Smoking"] == 1:
        score += 1 * w["smoking"]
    else:
        score -= 3 * w["smoking"]

    # 2. 청소
    diff_clean = abs(a["Cleaning_Habit"] - b["Cleaning_Habit"])
    if diff_clean == 0:
        score += 2 * w["cleaning"]
    elif diff_clean == 1:
        score += 1 * w["cleaning"]
    elif diff_clean == 3:
        score -= 2 * w["cleaning"]

    # 3. 방에서 먹는 것
    if a["Eating_in_Room"] == b["Eating_in_Room"]:
        if a["Eating_in_Room"] == 0:
            score += 2 * w["eating"]
        else:
            score += 1 * w["eating"]
    else:
        if {a["Eating_in_Room"], b["Eating_in_Room"]} == {0, 2}:
            score -= 2 * w["eating"]

    # 4. 소음 민감도
    diff_noise = abs(a["Noise_Sensitivity"] - b["Noise_Sensitivity"])
    score += (2 - diff_noise) * w["noise"]

    # 5. 나이
    diff_age = abs(a["Age"] - b["Age"])
    if diff_age <= 5:
        pass
    elif diff_age <= 10:
        score -= 1 * w["age"]
    else:
        score -= 2 * w["age"]

    # 6. 수면 시간
    diff_sleep = abs(a["Sleep_Duration"] - b["Sleep Duration"])
    if diff_sleep > 2:
        score -= 2 * w["sleep_duration"]
    elif diff_sleep > 1:
        score -= 1 * w["sleep_duration"]

    # 7. 활동량
    diff_steps = abs(a["Daily_Steps"] - b["Daily Steps"])
    if diff_steps > 6000:
        score -= 2 * w["daily_steps"]
    elif diff_steps > 3000:
        score -= 1 * w["daily_steps"]

    return score


def find_best_matches_for_user(
    df: pd.DataFrame,
    user_profile: Dict[str, Any],
    weights: Dict[str, float],
    filters: Dict[str, Any],
    top_n: int = 5,
) -> pd.DataFrame:
    candidates = apply_filters(df, filters)

    scores: List[Tuple[int, float]] = []
    for idx, row in candidates.iterrows():
        s = match_score_weighted(user_profile, row, weights)
        scores.append((idx, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    top_idx = [idx for idx, _ in scores[:top_n]]
    result = candidates.loc[top_idx].copy()
    result["match_score"] = [s for _, s in scores[:top_n]]
    return result


# ==========================
# 3. LLM 연동 (OpenAI 예시)
# ==========================

@dataclass
class ChatState:
    messages: list = field(default_factory=list)
    structured: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "profile": {},
        "weights": {},
        "filters": {},
    })
    finished: bool = False


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("환경변수 OPENAI_API_KEY를 설정해주세요.")
    client = OpenAI(api_key=api_key)
    return client


def call_llm_parse_answer(
    client: OpenAI,
    chat_state: ChatState,
    user_text: str,
    model_name: str = "gpt-4o-mini",
) -> None:
    """
    사용자의 자유 대답을 구조화된 JSON(profile/weights/filters)에 병합
    """

    system_prompt = """
    너는 룸메이트 매칭을 돕는 비서야.
    사용자의 한국어 답변을 읽고, 아래 JSON 스키마에 맞게 구조화해서 출력해.
    출력은 반드시 JSON만, 다른 말 없이.

    스키마 예시:
    {
      "profile": {
        "Gender": "Male|Female|Other",
        "Age": 25,
        "Smoking": 0,
        "Cleaning_Habit": 1,
        "Eating_in_Room": 2,
        "Noise_Sensitivity": 4,
        "Sleep_Duration": 7.0,
        "Daily_Steps": 6000
      },
      "weights": {
        "smoking": 2.5,
        "cleaning": 3.0,
        "sleep_duration": 2.0,
        "noise": 1.5,
        "age": 1.5,
        "daily_steps": 1.0,
        "eating": 1.0
      },
      "filters": {
        "Gender": "Male|Female|Any",
        "Smoking": 0,
        "Age_min": 20,
        "Age_max": 30
      }
    }

    규칙:
    - 사용자가 말하지 않은 값은 JSON에서 생략해.
    - 숫자로 해석 가능한 건 숫자로.
    - "비흡연", "담배 안 피움" → Smoking = 0
    - "흡연", "담배 피움" → Smoking = 1
    - 청소 주기:
      - "매일" → 0
      - "주 2-3회" → 1
      - "주 1회" → 2
      - "거의 안 함" → 3
    - 방 안 음식:
      - "불가", "안 먹음" → 0
      - "간식", "간단히" → 1
      - "배달", "식사" → 2
    - 소음 민감도: 1~5 숫자
    - 중요도(가중치)는 1~5 사이 숫자를 받아서 0.5~3.0 범위로 스케일링해서 저장해도 좋아.
    """

    user_prompt = (
        "지금까지의 구조화된 정보:\n"
        f"{json.dumps(chat_state.structured, ensure_ascii=False)}\n\n"
        "사용자 최신 답변:\n"
        f"{user_text}\n\n"
        "이 답변을 반영해서 구조화된 JSON을 업데이트해줘."
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    json_text = response.choices[0].message.content.strip()
    try:
        new_data = json.loads(json_text)
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 무시
        return

    # 병합
    for section in ["profile", "weights", "filters"]:
        if section in new_data and isinstance(new_data[section], dict):
            chat_state.structured[section].update(new_data[section])


def call_llm_next_question(
    client: OpenAI,
    chat_state: ChatState,
    model_name: str = "gpt-4o-mini",
) -> str:
    """
    현재까지의 structured 정보를 보고, 자연스러운 다음 질문 생성
    """

    system_prompt = """
    너는 룸메이트 매칭을 위한 대화형 상담사야.
    지금까지 수집된 정보를 보고, 다음에 물어보면 좋을 한 가지 주제를 골라
    한국어로 자연스럽게 질문 한두 문장을 만들어줘.

    스타일:
    - 존댓말, 친절한 말투
    - 이미 사용자가 말한 내용을 간단히 공감/요약해 준 뒤
      새로운 정보를 요청하면 좋아.
    - 너무 길게 말하지 말고, 1~2문장으로.

    주의:
    - 이미 structured 데이터에 있는 값들은 되도록 반복해서 묻지 마.
    - 아직 채워지지 않은 정보 중 하나를 골라 물어봐.
    """

    user_prompt = (
        "현재까지 구조화된 정보:\n"
        f"{json.dumps(chat_state.structured, ensure_ascii=False)}\n\n"
        "우리가 최종적으로 알고 싶은 정보는:\n"
        "- profile: Gender, Age, Smoking, Cleaning_Habit, Eating_in_Room, Noise_Sensitivity, Sleep_Duration, Daily_Steps\n"
        "- weights: smoking, cleaning, sleep_duration, noise, age, daily_steps, eating\n"
        "- filters: Gender, Smoking, Age_min, Age_max\n\n"
        "아직 비어 있는 값들 중 하나를 골라, 그에 대한 자연스러운 질문을 해줘."
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    question = response.choices[0].message.content.strip()
    return question


def call_llm_explain_results(
    client: OpenAI,
    chat_state: ChatState,
    matches: pd.DataFrame,
    model_name: str = "gpt-4o-mini",
) -> str:
    """
    매칭 결과를 자연스럽게 요약/설명
    """

    system_prompt = """
    너는 룸메이트 매칭 결과를 설명해주는 상담사야.
    주어진 후보 리스트를 보고, 사용자의 성향과 어떤 점에서 잘 맞는지
    친절하게 설명해줘.

    규칙:
    - 한국어, 존댓말
    - 너무 긴 보고서 말고, 요약 + 간단한 이유를 1~3명 정도에 대해 설명
    - 각 후보는 Person ID, 나이, 성별, 흡연 여부, 청소 습관, 방 안 음식, 소음 민감도, 매칭 점수 정보를 가짐
    """

    matches_brief = matches[[
        "Person ID",
        "Gender",
        "Age",
        "Smoking",
        "Cleaning_Habit",
        "Eating_in_Room",
        "Noise_Sensitivity",
        "Sleep Duration",
        "Daily Steps",
        "match_score",
    ]]

    user_prompt = (
        "사용자 성향(구조화 데이터):\n"
        f"{json.dumps(chat_state.structured, ensure_ascii=False)}\n\n"
        "추천된 후보 리스트(상위 몇 명):\n"
        f"{matches_brief.to_json(orient='records', force_ascii=False)}\n\n"
        "이 정보를 바탕으로, 어떤 후보가 어떤 이유로 잘 맞을지 요약해서 설명해줘."
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    explanation = response.choices[0].message.content.strip()
    return explanation


# ==========================
# 4. 대화 루프 (터미널용)
# ==========================

def has_enough_info(structured: Dict[str, Dict[str, Any]]) -> bool:
    prof = structured["profile"]
    w = structured["weights"]

    needed_profile = [
        "Gender",
        "Age",
        "Smoking",
        "Cleaning_Habit",
        "Eating_in_Room",
        "Noise_Sensitivity",
    ]

    if not all(k in prof for k in needed_profile):
        return False

    needed_weights = ["smoking", "cleaning"]
    if not all(k in w for k in needed_weights):
        return False

    return True


def build_user_profile(structured: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    prof = structured["profile"]
    user_profile = {
        "Smoking": prof["Smoking"],
        "Cleaning_Habit": prof["Cleaning_Habit"],
        "Eating_in_Room": prof.get("Eating_in_Room", 1),
        "Noise_Sensitivity": prof.get("Noise_Sensitivity", 3),
        "Age": prof["Age"],
        "Sleep_Duration": prof.get("Sleep_Duration", 7.0),
        "Daily_Steps": prof.get("Daily_Steps", 5000),
    }
    return user_profile


def build_weights(structured: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    w = structured["weights"]
    default_weights = {
        "smoking": 2.0,
        "cleaning": 2.0,
        "eating": 1.5,
        "noise": 2.0,
        "age": 1.5,
        "sleep_duration": 1.5,
        "daily_steps": 1.0,
    }
    merged = default_weights.copy()
    merged.update(w)
    return merged


def build_filters(structured: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    return structured["filters"].copy()


def chat_loop(df: pd.DataFrame) -> None:
    client = get_openai_client()
    state = ChatState()

    print("안녕하세요! 성향 기반 룸메이트 매칭 도우미입니다.")
    print("편하게 본인에 대해 말씀해 주세요. 몇 가지 질문을 드리면서, 잘 맞는 사람을 찾아볼게요.\n")

    # 첫 질문
    question = call_llm_next_question(client, state)
    print("AI:", question)

    while not state.finished:
        try:
            user_text = input("YOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n대화를 종료합니다.")
            break

        if not user_text:
            continue

        # 1. 사용자 답 → 구조화
        call_llm_parse_answer(client, state, user_text)

        # 2. 정보가 충분하면 매칭
        if has_enough_info(state.structured):
            user_profile = build_user_profile(state.structured)
            weights = build_weights(state.structured)
            filters = build_filters(state.structured)

            matches = find_best_matches_for_user(
                df,
                user_profile=user_profile,
                weights=weights,
                filters=filters,
                top_n=5,
            )

            explanation = call_llm_explain_results(client, state, matches)
            print("\n=== 매칭 결과 설명 ===")
            print(explanation)
            print("\n=== 상위 후보 리스트(요약) ===")
            print(matches[[
                "Person ID",
                "Gender",
                "Age",
                "Smoking",
                "Cleaning_Habit",
                "Eating_in_Room",
                "Noise_Sensitivity",
                "Sleep Duration",
                "Daily Steps",
                "match_score",
            ]])
            state.finished = True
            break

        # 3. 아직 부족하면 다음 질문
        question = call_llm_next_question(client, state)
        print("\nAI:", question)


# ==========================
# 5. 엔트리 포인트
# ==========================

if __name__ == "__main__":
    # 이 이름이 실제 CSV 파일 이름과 같아야 합니다.
    csv_path = "Sleep_health_and_lifestyle_dataset.csv"

    if not os.path.exists(csv_path):
        print(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
        print("경로를 코드 하단의 csv_path 변수에 맞게 수정하세요.")
    else:
        df_extended = load_dataset(csv_path)
        chat_loop(df_extended)