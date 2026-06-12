import os
import random
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List

import pandas as pd


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
# 3. 질문·답변 (API 없음)
# ==========================

MAX_MATCHING_QUESTIONS = 6
PHASE_PROFILE = "profile"
PHASE_MATCHING = "matching"

# 1단계: 본인 정보 (우선 수집)
PROFILE_FIELD_ORDER: List[str] = [
    "Gender",
    "Age",
    "Smoking",
    "Cleaning_Habit",
    "Eating_in_Room",
    "Noise_Sensitivity",
]

# 2단계: 룸메이트 매칭용 추가 질문 (선호·필터·중요도)
MATCHING_FIELD_ORDER: List[str] = [
    "filter_Gender",
    "filter_Smoking",
    "filter_Age",
    "weight_smoking",
    "weight_cleaning",
    "weight_noise",
]

PROFILE_FIELD_QUESTIONS: Dict[str, str] = {
    "Gender": "성별을 알려주세요. (남성 / 여성)",
    "Age": "나이는 어떻게 되시나요? (숫자)",
    "Smoking": "흡연을 하시나요? (비흡연 / 흡연)",
    "Cleaning_Habit": "청소는 얼마나 자주 하시나요? (매일 / 주2~3회 / 주1회 / 거의안함)",
    "Eating_in_Room": "방 안 음식은? (불가 / 간식 / 배달)",
    "Noise_Sensitivity": "소음 민감도? (1~5)",
}

MATCHING_FIELD_QUESTIONS: Dict[str, str] = {
    "filter_Gender": "선호하는 룸메이트 **성별**은? (남성 / 여성 / 상관없음)",
    "filter_Smoking": "룸메이트 **흡연 여부** 선호는? (비흡연만 / 흡연도 괜찮음 / 상관없음)",
    "filter_Age": "희망 룸메이트 **나이대**는? (예: `20~25`, `23`)",
    "weight_smoking": "룸메이트 **흡연 여부**가 얼마나 중요하신가요? (`1`~`5`)",
    "weight_cleaning": "룸메이트 **청소 습관**이 얼마나 중요하신가요? (`1`~`5`)",
    "weight_noise": "룸메이트와의 **소음·생활 패턴**이 얼마나 중요하신가요? (`1`~`5`)",
}

PROFILE_FORM_LABELS = {
    "Gender": "성별",
    "Age": "나이",
    "Smoking": "흡연",
    "Cleaning_Habit": "청소 습관",
    "Eating_in_Room": "방 안 음식",
    "Noise_Sensitivity": "소음 민감도",
}


@dataclass
class ChatState:
    messages: list = field(default_factory=list)
    structured: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "profile": {},
        "weights": {},
        "filters": {},
    })
    phase: str = PHASE_MATCHING
    asked_fields: List[str] = field(default_factory=list)
    questions_asked: int = 0
    finished: bool = False


def scale_importance(value: int) -> float:
    value = max(1, min(5, value))
    return round(0.5 + (value - 1) * 0.625, 2)


def set_profile_from_form(
    structured: Dict[str, Dict[str, Any]],
    *,
    gender: str,
    age: int,
    smoking: int,
    cleaning_habit: int,
    eating_in_room: int,
    noise_sensitivity: int,
) -> None:
    structured["profile"] = {
        "Gender": gender,
        "Age": int(age),
        "Smoking": int(smoking),
        "Cleaning_Habit": int(cleaning_habit),
        "Eating_in_Room": int(eating_in_room),
        "Noise_Sensitivity": int(noise_sensitivity),
        "Sleep_Duration": 7.0,
        "Daily_Steps": 5000,
    }


def get_pending_field(chat_state: ChatState) -> Optional[str]:
    for field_id in reversed(chat_state.asked_fields):
        if not _field_is_filled(chat_state.structured, field_id):
            return field_id
    return None


def parse_answer_rule(chat_state: ChatState, user_text: str) -> Tuple[bool, str]:
    """규칙 기반 답변 파싱. (성공 여부, 안내 메시지)"""
    field_id = get_pending_field(chat_state)
    if field_id is None:
        return False, "지금은 받을 질문이 없습니다."

    text = user_text.strip()
    lowered = text.lower()
    structured = chat_state.structured
    profile = structured["profile"]
    filters = structured["filters"]
    weights = structured["weights"]

    if field_id == "Gender":
        if any(k in lowered for k in ("남", "male")):
            profile["Gender"] = "Male"
            return True, ""
        if any(k in lowered for k in ("여", "female")):
            profile["Gender"] = "Female"
            return True, ""
        return False, "남성 / 여성 중 하나로 답해주세요."

    if field_id == "Age":
        nums = [int(n) for n in re.findall(r"\d+", text)]
        if nums:
            profile["Age"] = nums[0]
            return True, ""
        return False, "나이를 숫자로 입력해주세요. (예: 23)"

    if field_id == "Smoking":
        if any(k in lowered for k in ("비흡연", "안 피", "안피", "안해", "금연", "아니")):
            profile["Smoking"] = 0
            return True, ""
        if any(k in lowered for k in ("흡연", "피움", "해요", "한다")):
            profile["Smoking"] = 1
            return True, ""
        return False, "비흡연 / 흡연 중 하나로 답해주세요."

    if field_id == "Cleaning_Habit":
        if "매일" in lowered:
            profile["Cleaning_Habit"] = 0
            return True, ""
        if "2" in lowered or "3" in lowered or "이삼" in lowered:
            profile["Cleaning_Habit"] = 1
            return True, ""
        if "주1" in lowered or "한번" in lowered or "1회" in lowered:
            profile["Cleaning_Habit"] = 2
            return True, ""
        if any(k in lowered for k in ("거의", "안 함", "안함", "안해")):
            profile["Cleaning_Habit"] = 3
            return True, ""
        return False, "매일 / 주2~3회 / 주1회 / 거의안함 중 하나로 답해주세요."

    if field_id == "Eating_in_Room":
        if any(k in lowered for k in ("불가", "안 먹", "안먹")):
            profile["Eating_in_Room"] = 0
            return True, ""
        if any(k in lowered for k in ("간식", "음료", "음료")):
            profile["Eating_in_Room"] = 1
            return True, ""
        if any(k in lowered for k in ("배달", "식사")):
            profile["Eating_in_Room"] = 2
            return True, ""
        return False, "불가 / 간식 / 배달 중 하나로 답해주세요."

    if field_id == "Noise_Sensitivity":
        noise_match = re.search(r"[1-5]", text)
        if noise_match:
            profile["Noise_Sensitivity"] = int(noise_match.group())
            return True, ""
        return False, "1~5 사이 숫자로 입력해주세요."

    if field_id == "filter_Gender":
        if any(k in lowered for k in ("남", "male")):
            filters["Gender"] = "Male"
            return True, ""
        if any(k in lowered for k in ("여", "female")):
            filters["Gender"] = "Female"
            return True, ""
        if any(k in lowered for k in ("상관", "무관", "any", "다")):
            filters["Gender"] = "Any"
            return True, ""
        return False, "남성 / 여성 / 상관없음 중 하나로 답해주세요."

    if field_id == "filter_Smoking":
        if any(k in lowered for k in ("비흡연", "안 피", "안피", "금연")):
            filters["Smoking"] = 0
            filters.pop("smoking_any", None)
            return True, ""
        if any(k in lowered for k in ("괜찮", "흡연도", "상관없")) and "비흡연만" not in lowered:
            if "상관" in lowered:
                filters.pop("Smoking", None)
                filters["smoking_any"] = True
                return True, ""
            filters["Smoking"] = 1
            filters.pop("smoking_any", None)
            return True, ""
        if any(k in lowered for k in ("상관", "무관")):
            filters.pop("Smoking", None)
            filters["smoking_any"] = True
            return True, ""
        return False, "비흡연만 / 흡연도 괜찮음 / 상관없음 중 하나로 답해주세요."

    if field_id == "filter_Age":
        nums = [int(n) for n in re.findall(r"\d+", text)]
        if len(nums) >= 2:
            filters["Age_min"] = min(nums[0], nums[1])
            filters["Age_max"] = max(nums[0], nums[1])
            return True, ""
        if len(nums) == 1:
            center = nums[0]
            filters["Age_min"] = max(18, center - 2)
            filters["Age_max"] = center + 2
            return True, ""
        return False, "나이대를 숫자로 입력해주세요. (예: 20~25 또는 23)"

    weight_match = re.search(r"[1-5]", text)
    if field_id == "weight_smoking":
        if weight_match:
            weights["smoking"] = scale_importance(int(weight_match.group()))
            return True, ""
        return False, "1~5 사이 숫자로 중요도를 입력해주세요."

    if field_id == "weight_cleaning":
        if weight_match:
            weights["cleaning"] = scale_importance(int(weight_match.group()))
            return True, ""
        return False, "1~5 사이 숫자로 중요도를 입력해주세요."

    if field_id == "weight_noise":
        if weight_match:
            weights["noise"] = scale_importance(int(weight_match.group()))
            return True, ""
        return False, "1~5 사이 숫자로 중요도를 입력해주세요."

    return False, "답변을 이해하지 못했습니다. 예시 형식대로 다시 입력해주세요."


def _field_is_filled(structured: Dict[str, Dict[str, Any]], field_id: str) -> bool:
    prof = structured["profile"]
    weights = structured["weights"]
    filters = structured["filters"]

    if field_id in PROFILE_FIELD_ORDER:
        return field_id in prof

    if field_id == "filter_Gender":
        return "Gender" in filters
    if field_id == "filter_Smoking":
        return "Smoking" in filters or filters.get("smoking_any") is True
    if field_id == "filter_Age":
        return "Age_min" in filters and "Age_max" in filters
    if field_id == "weight_smoking":
        return "smoking" in weights
    if field_id == "weight_cleaning":
        return "cleaning" in weights
    if field_id == "weight_noise":
        return "noise" in weights

    return False


def is_profile_complete(structured: Dict[str, Dict[str, Any]]) -> bool:
    return all(_field_is_filled(structured, f) for f in PROFILE_FIELD_ORDER)


def is_matching_complete(structured: Dict[str, Dict[str, Any]]) -> bool:
    return all(_field_is_filled(structured, f) for f in MATCHING_FIELD_ORDER)


def get_active_field_order(chat_state: ChatState) -> List[str]:
    if chat_state.phase == PHASE_PROFILE:
        return PROFILE_FIELD_ORDER
    return MATCHING_FIELD_ORDER


def start_matching_phase(chat_state: ChatState) -> None:
    chat_state.phase = PHASE_MATCHING
    chat_state.questions_asked = 0
    chat_state.asked_fields = []


def get_first_missing_field(chat_state: ChatState) -> Optional[str]:
    for field_id in get_active_field_order(chat_state):
        if not _field_is_filled(chat_state.structured, field_id):
            return field_id
    return None


def get_next_field_to_ask(chat_state: ChatState) -> Optional[str]:
    for field_id in get_active_field_order(chat_state):
        if field_id in chat_state.asked_fields:
            continue
        if not _field_is_filled(chat_state.structured, field_id):
            return field_id
    return None


def maybe_advance_phase(chat_state: ChatState) -> bool:
    """본인 정보가 끝나면 매칭 단계로 전환. 전환 시 True."""
    if chat_state.phase != PHASE_PROFILE:
        return False
    if not is_profile_complete(chat_state.structured):
        return False
    chat_state.phase = PHASE_MATCHING
    return True


def get_template_question(field_id: str, chat_state: ChatState) -> str:
    if field_id in PROFILE_FIELD_ORDER:
        return PROFILE_FIELD_QUESTIONS[field_id]
    return MATCHING_FIELD_QUESTIONS[field_id]


def ask_next_question(chat_state: ChatState) -> Optional[str]:
    """질문 1개 출력. 반환값은 질문 텍스트(없으면 None)."""
    max_q = (
        len(PROFILE_FIELD_ORDER)
        if chat_state.phase == PHASE_PROFILE
        else MAX_MATCHING_QUESTIONS
    )
    if chat_state.questions_asked >= max_q:
        return None

    field_id = get_next_field_to_ask(chat_state)
    if field_id is None:
        return None

    question = get_template_question(field_id, chat_state)
    chat_state.asked_fields.append(field_id)
    chat_state.questions_asked += 1
    return question


CLEANING_LABELS = {0: "매일", 1: "주 2~3회", 2: "주 1회", 3: "거의 안 함"}
EATING_LABELS = {0: "불가", 1: "간식·음료", 2: "배달·식사"}
SMOKING_LABELS = {0: "비흡연", 1: "흡연"}


def format_match_summary(state: ChatState, matches: pd.DataFrame) -> str:
    lines = ["### 매칭 결과 요약", ""]
    if matches.empty:
        return "조건에 맞는 후보를 찾지 못했습니다. 필터 조건을 완화해 보세요."

    user = state.structured["profile"]
    lines.append(
        f"입력하신 성향(흡연 {SMOKING_LABELS.get(user.get('Smoking'), '-')}, "
        f"청소 {CLEANING_LABELS.get(user.get('Cleaning_Habit'), '-')})과 "
        f"비교해 상위 후보를 추천합니다."
    )
    lines.append("")

    for _, row in matches.head(3).iterrows():
        lines.append(f"**후보 #{int(row['Person ID'])}** · 점수 {row['match_score']:.1f}")
        lines.append(
            f"- {row['Gender']}, {int(row['Age'])}세, "
            f"흡연 {SMOKING_LABELS.get(int(row['Smoking']), '-')}, "
            f"청소 {CLEANING_LABELS.get(int(row['Cleaning_Habit']), '-')}, "
            f"소음 민감도 {int(row['Noise_Sensitivity'])}"
        )
        reasons = []
        if user.get("Smoking") == row["Smoking"]:
            reasons.append("흡연 성향 일치")
        if abs(user.get("Cleaning_Habit", 1) - row["Cleaning_Habit"]) <= 1:
            reasons.append("청소 습관 유사")
        if abs(user.get("Noise_Sensitivity", 3) - row["Noise_Sensitivity"]) <= 1:
            reasons.append("소음 민감도 비슷")
        if reasons:
            lines.append(f"- 잘 맞는 점: {', '.join(reasons)}")
        lines.append("")

    return "\n".join(lines)


# ==========================
# 4. 대화 루프 (터미널용)
# ==========================

def has_enough_info(chat_state: ChatState) -> bool:
    return is_profile_complete(chat_state.structured) and is_matching_complete(
        chat_state.structured
    )


def apply_defaults(chat_state: ChatState) -> None:
    """질문 상한에 도달했을 때 빠진 값을 기본값으로 채움."""
    structured = chat_state.structured
    prof = structured["profile"]
    weights = structured["weights"]
    filters = structured["filters"]

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
    filter_defaults = {
        "Gender": "Any",
        "Smoking": 0,
        "Age_min": max(18, prof.get("Age", 25) - 3),
        "Age_max": prof.get("Age", 25) + 3,
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
    for key, value in filter_defaults.items():
        filters.setdefault(key, value)
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


def format_profile_summary(state: ChatState) -> str:
    prof = state.structured["profile"]
    labels = {
        "Gender": "성별",
        "Age": "나이",
        "Smoking": "흡연",
        "Cleaning_Habit": "청소",
        "Eating_in_Room": "방 안 음식",
        "Noise_Sensitivity": "소음 민감도",
    }
    gender_txt = {"Male": "남성", "Female": "여성"}
    lines = ["### 입력하신 본인 정보"]
    for key, label in labels.items():
        val = prof.get(key, "-")
        if key == "Gender" and val in gender_txt:
            val = gender_txt[val]
        if key == "Smoking" and val in SMOKING_LABELS:
            val = SMOKING_LABELS[val]
        lines.append(f"- **{label}**: {val}")
    return "\n".join(lines)


def print_profile_summary(state: ChatState) -> None:
    print("\n" + format_profile_summary(state).replace("### ", "=== ").replace("**", "") + "\n")


MATCH_RESULT_COLUMNS = [
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
]


def run_matching_results(
    state: ChatState,
    df: pd.DataFrame,
    *,
    used_defaults: bool = False,
) -> Tuple[pd.DataFrame, str, Optional[str]]:
    notice = None
    if used_defaults:
        apply_defaults(state)
        notice = (
            "아직 입력되지 않은 매칭 선호 항목은 기본값으로 채워 매칭했습니다."
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
    explanation = format_match_summary(state, matches)
    return matches[MATCH_RESULT_COLUMNS], explanation, notice


def run_matching_and_print(
    state: ChatState,
    df: pd.DataFrame,
    *,
    used_defaults: bool = False,
) -> None:
    matches, explanation, notice = run_matching_results(
        state, df, used_defaults=used_defaults
    )
    if notice:
        print(f"\n(안내) {notice}\n")
    print("\n=== 매칭 결과 설명 ===")
    print(explanation)
    print("\n=== 상위 후보 리스트(요약) ===")
    print(matches)


def chat_loop(df: pd.DataFrame) -> None:
    state = ChatState(phase=PHASE_PROFILE)

    print("안녕하세요! 성향 기반 룸메이트 매칭 도우미입니다. (API 없음)")
    print("--- 1단계: 본인 정보 입력 ---\n")

    first_question = ask_next_question(state)
    if first_question:
        print("AI:", first_question)

    while not state.finished:
        try:
            user_text = input("YOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n대화를 종료합니다.")
            break

        if not user_text:
            continue

        ok, hint = parse_answer_rule(state, user_text)
        if not ok:
            print(f"AI: {hint}")
            continue

        if maybe_advance_phase(state):
            print_profile_summary(state)
            print("--- 2단계: 룸메이트 매칭 선호 입력 ---\n")
            start_matching_phase(state)
            q = ask_next_question(state)
            if q:
                print("AI:", q)
            continue

        if has_enough_info(state):
            run_matching_and_print(state, df)
            state.finished = True
            break

        max_q = (
            len(PROFILE_FIELD_ORDER)
            if state.phase == PHASE_PROFILE
            else MAX_MATCHING_QUESTIONS
        )
        if state.questions_asked >= max_q:
            run_matching_and_print(state, df, used_defaults=True)
            state.finished = True
            break

        next_question = ask_next_question(state)
        if next_question is None:
            if state.phase == PHASE_PROFILE and is_profile_complete(state.structured):
                maybe_advance_phase(state)
                start_matching_phase(state)
                print_profile_summary(state)
                print("--- 2단계: 룸메이트 매칭 선호 입력 ---\n")
                next_question = ask_next_question(state)

            if next_question is None:
                run_matching_and_print(
                    state, df, used_defaults=not has_enough_info(state)
                )
                state.finished = True
                break

        phase_label = "본인 정보" if state.phase == PHASE_PROFILE else "매칭 선호"
        print(f"\nAI [{phase_label}]:", next_question)


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