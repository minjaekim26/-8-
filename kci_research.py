"""KCI 논문 데이터·UI 표시용 (roommate_match_chat 과 분리)."""

import os
from typing import Any, Dict, Optional

import pandas as pd

KCI_RESEARCH_FILE = "kci_research_data.csv"

KCI_CITATION = (
    "신지은, 김정기, 서은국 (2017). 기숙사 만족도에 대한 예측 오류: "
    "행복한 룸메이트의 과소평가된 가치. "
    "한국심리학회지: 사회 및 성격, 31(2), 21-38."
)

KCI_FINDING_SUMMARY = (
    "학생들은 「룸메이트 행복」을 덜 중요하다고 예측했지만, "
    "실제 기숙사 만족도를 가장 잘 예측한 요인은 룸메이트 행복(β=0.41, p<.001)이었습니다."
)

WEIGHT_DISPLAY_LABELS: Dict[str, str] = {
    "happiness": "룸메이트 행복 (KCI)",
    "smoking": "흡연",
    "cleaning": "청소",
    "eating": "방 안 음식",
    "noise": "소음·생활 패턴",
    "age": "나이 차이",
    "sleep_duration": "수면 시간",
    "daily_steps": "활동량",
}


def estimate_happiness_level(
    sleep_duration: float = 7.0,
    quality: float = 6.5,
    stress: float = 5.0,
) -> float:
    raw = (quality / 10) * 7 - (stress - 5) * 0.3 + (sleep_duration - 7) * 0.2
    return round(max(1.0, min(7.0, raw)), 1)


def load_kci_research_table(base_dir: Optional[str] = None) -> pd.DataFrame:
    root = base_dir or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, KCI_RESEARCH_FILE)
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def get_kci_factor_display_df(base_dir: Optional[str] = None) -> pd.DataFrame:
    kci = load_kci_research_table(base_dir)
    if kci.empty:
        return kci
    display = kci[
        [
            "factor_name_ko",
            "study1_predicted_mean",
            "regression_beta",
            "regression_p",
            "significant",
            "project_mapping",
        ]
    ].copy()
    display.columns = [
        "요인",
        "예측 중요도(신입생)",
        "회귀 β",
        "p값",
        "유의",
        "프로젝트 매핑",
    ]
    display["p값"] = display["p값"].apply(
        lambda p: "< .001" if isinstance(p, str) and str(p).startswith("0.001") else p
    )
    return display


def get_profile_happiness_level(profile: Dict[str, Any]) -> float:
    sleep_dur = profile.get("Sleep_Duration", 7.0)
    quality = profile.get("Quality of Sleep", profile.get("Quality_of_Sleep", 6.5))
    stress = profile.get("Stress Level", profile.get("Stress_Level", 5))
    return profile.get(
        "Happiness_Level",
        estimate_happiness_level(sleep_dur, quality, stress),
    )


def get_weights_chart_df(
    structured: Optional[Dict[str, Dict[str, Any]]] = None,
    base_dir: Optional[str] = None,
) -> pd.DataFrame:
    from roommate_match_chat import build_weights, load_kci_research_weights

    if structured:
        weights = build_weights(structured)
    else:
        weights = load_kci_research_weights(base_dir)
    rows = [
        {"항목": WEIGHT_DISPLAY_LABELS.get(key, key), "가중치": value}
        for key, value in weights.items()
    ]
    return pd.DataFrame(rows).sort_values("가중치", ascending=False)
