import os
import json
import random
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List

import pandas as pd
from google import genai
from google.genai import types  # pip install google-genai


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
# 3. LLM 연동 (Gemini API)
# ==========================

MAX_QUESTIONS = 10

# 수집 순서(앞에서부터 하나씩만 질문)
FIELD_ORDER: List[str] = [
    "Gender",
    "Age",
    "Smoking",
    "Cleaning_Habit",
    "Eating_in_Room",
    "Noise_Sensitivity",
    "weight_smoking",
    "weight_cleaning",
]

FIELD_QUESTIONS: Dict[str, str] = {
    "Gender": "먼저 본인의 성별을 알려주실 수 있을까요? (남성/여성)",
    "Age": "나이는 어떻게 되시나요?",
    "Smoking": "흡연을 하시나요? (비흡연 / 흡연)",
    "Cleaning_Habit": "평소 청소는 얼마나 자주 하시나요? (매일 / 주 2~3회 / 주 1회 / 거의 안 함)",
    "Eating_in_Room": "방 안에서 음식을 드시는 편인가요? (불가 / 간식·음료 / 배달·식사까지)",
    "Noise_Sensitivity": "소음에 대한 민감도는 어느 정도인가요? (1=둔감 ~ 5=매우 예민)",
    "weight_smoking": "룸메이트의 흡연 여부가 얼마나 중요하신가요? (1=별로 안 중요 ~ 5=매우 중요)",
    "weight_cleaning": "룸메이트의 청소 습관이 얼마나 중요하신가요? (1=별로 안 중요 ~ 5=매우 중요)",
}


@dataclass
class ChatState:
    messages: list = field(default_factory=list)
    structured: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "profile": {},
        "weights": {},
        "filters": {},
    })
    asked_fields: List[str] = field(default_factory=list)
    questions_asked: int = 0
    finished: bool = False


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("환경변수 GEMINI_API_KEY를 설정해주세요.")
    return genai.Client(api_key=api_key)


def gemini_generate(
    client: genai.Client,
    *,
    system_prompt: str,
    user_prompt: str,
    model_name: str = DEFAULT_GEMINI_MODEL,
    json_response: bool = False,
) -> str:
    config_kwargs: Dict[str, Any] = {"system_instruction": system_prompt}
    if json_response:
        config_kwargs["response_mime_type"] = "application/json"

    response = client.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return (response.text or "").strip()


def call_llm_parse_answer(
    client: genai.Client,
    chat_state: ChatState,
    user_text: str,
    model_name: str = DEFAULT_GEMINI_MODEL,
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

    json_text = gemini_generate(
        client,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_name=model_name,
        json_response=True,
    )
    try:
        new_data = json.loads(json_text)
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 무시
        return

    # 병합
    for section in ["profile", "weights", "filters"]:
        if section in new_data and isinstance(new_data[section], dict):
            chat_state.structured[section].update(new_data[section])


def _field_is_filled(structured: Dict[str, Dict[str, Any]], field_id: str) -> bool:
    prof = structured["profile"]
    weights = structured["weights"]

    if field_id == "weight_smoking":
        return "smoking" in weights
    if field_id == "weight_cleaning":
        return "cleaning" in weights
    return field_id in prof


def get_first_missing_field(structured: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """아직 채워지지 않은 필수 항목 중 우선순위가 가장 높은 항목."""
    for field_id in FIELD_ORDER:
        if not _field_is_filled(structured, field_id):
            return field_id
    return None


def get_next_field_to_ask(chat_state: ChatState) -> Optional[str]:
    """아직 없고, 아직 묻지 않은 항목 중 우선순위가 가장 높은 항목."""
    for field_id in FIELD_ORDER:
        if field_id in chat_state.asked_fields:
            continue
        if not _field_is_filled(chat_state.structured, field_id):
            return field_id
    return None


def get_template_question(field_id: str) -> str:
    return FIELD_QUESTIONS[field_id]


def ask_next_question(chat_state: ChatState) -> Optional[str]:
    """질문 1개 출력. 반환값은 질문 텍스트(없으면 None)."""
    if chat_state.questions_asked >= MAX_QUESTIONS:
        return None

    field_id = get_next_field_to_ask(chat_state)
    if field_id is None:
        return None

    question = get_template_question(field_id)
    chat_state.asked_fields.append(field_id)
    chat_state.questions_asked += 1
    return question


def call_llm_explain_results(
    client: genai.Client,
    chat_state: ChatState,
    matches: pd.DataFrame,
    model_name: str = DEFAULT_GEMINI_MODEL,
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

    return gemini_generate(
        client,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_name=model_name,
    )


# ==========================
# 4. 대화 루프 (터미널용)
# ==========================

def has_enough_info(structured: Dict[str, Dict[str, Any]]) -> bool:
    return get_first_missing_field(structured) is None


def apply_defaults(structured: Dict[str, Dict[str, Any]]) -> None:
    """질문 상한에 도달했을 때 빠진 값을 기본값으로 채움."""
    prof = structured["profile"]
    weights = structured["weights"]

    profile_defaults = {
        "Gender": "Male",
        "Age": 25,
        "Smoking": 0,
        "Cleaning_Habit": 1,
        "Eating_in_Room": 1,
        "Noise_Sensitivity": 3,
        "Sleep_Duration": 7.0,
        "Daily_Steps": 5000,
    }
    weight_defaults = {
        "smoking": 2.0,
        "cleaning": 2.0,
        "eating": 1.5,
        "noise": 2.0,
        "age": 1.5,
        "sleep_duration": 1.5,
        "daily_steps": 1.0,
    }

    for key, value in profile_defaults.items():
        prof.setdefault(key, value)
    for key, value in weight_defaults.items():
        weights.setdefault(key, value)


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


def run_matching_and_print(
    client: genai.Client,
    state: ChatState,
    df: pd.DataFrame,
    *,
    used_defaults: bool = False,
) -> None:
    if used_defaults:
        apply_defaults(state.structured)
        print(
            f"\n(안내) 질문은 최대 {MAX_QUESTIONS}개까지만 진행합니다. "
            "아직 입력되지 않은 항목은 기본값으로 채워 매칭했습니다.\n"
        )

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


def chat_loop(df: pd.DataFrame) -> None:
    client = get_gemini_client()
    state = ChatState()

    print("안녕하세요! 성향 기반 룸메이트 매칭 도우미입니다.")
    print(
        f"최대 {MAX_QUESTIONS}가지 질문만 드리고, 겹치지 않게 필요한 정보만 물어볼게요.\n"
    )

    first_question = ask_next_question(state)
    if first_question:
        print("AI:", first_question)
    else:
        run_matching_and_print(client, state, df)
        state.finished = True
        return

    while not state.finished:
        try:
            user_text = input("YOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n대화를 종료합니다.")
            break

        if not user_text:
            continue

        call_llm_parse_answer(client, state, user_text)

        if has_enough_info(state.structured):
            run_matching_and_print(client, state, df)
            state.finished = True
            break

        if state.questions_asked >= MAX_QUESTIONS:
            run_matching_and_print(client, state, df, used_defaults=True)
            state.finished = True
            break

        next_question = ask_next_question(state)
        if next_question is None:
            run_matching_and_print(
                client, state, df, used_defaults=not has_enough_info(state.structured)
            )
            state.finished = True
            break

        print(f"\nAI ({state.questions_asked}/{MAX_QUESTIONS}):", next_question)


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