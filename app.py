from pathlib import Path

import streamlit as st

from kci_research import (
    KCI_CITATION,
    KCI_FINDING_SUMMARY,
    get_kci_factor_display_df,
    get_profile_happiness_level,
    get_weights_chart_df,
)
from roommate_match_chat import (
    CANDIDATES_FILE,
    MAX_MATCHING_QUESTIONS,
    PHASE_MATCHING,
    ChatState,
    ask_next_question,
    build_user_profile,
    build_weights,
    ensure_candidate_pool,
    format_profile_summary,
    has_enough_info,
    is_matching_complete,
    load_dataset,
    parse_answer_rule,
    run_matching_results,
    set_profile_from_form,
    start_matching_phase,
)

DATA_DIR = Path(__file__).parent
UI_FORM = "form"
UI_CHAT = "chat"
UI_DONE = "done"


def init_session() -> None:
    defaults = {
        "ui_phase": UI_FORM,
        "chat_state": ChatState(),
        "messages": [],
        "finished": False,
        "bootstrapped": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "df" not in st.session_state:
        csv_path = ensure_candidate_pool(base_dir=str(DATA_DIR))
        st.session_state.df = load_dataset(csv_path)
        st.session_state.candidate_count = len(st.session_state.df)


def reset_all() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def begin_matching_chat() -> None:
    state: ChatState = st.session_state.chat_state
    start_matching_phase(state)
    st.session_state.ui_phase = UI_CHAT
    st.session_state.messages = [
        (
            "assistant",
            format_profile_summary(state)
            + "\n\n---\n"
            "**2단계: 룸메이트 선호**\n"
            "채팅으로 원하는 조건과 중요도를 알려주세요.",
        )
    ]
    first = ask_next_question(state)
    if first:
        st.session_state.messages.append(
            ("assistant", f"_매칭 선호 · 1/{MAX_MATCHING_QUESTIONS}_\n\n{first}")
        )
    st.session_state.bootstrapped = True


def finish_matching(*, used_defaults: bool = False) -> None:
    state: ChatState = st.session_state.chat_state
    with st.spinner("매칭 결과를 계산하는 중..."):
        matches, explanation, notice = run_matching_results(
            state,
            st.session_state.df,
            used_defaults=used_defaults,
        )
    if notice:
        st.session_state.messages.append(("assistant", f"ℹ️ {notice}"))
    st.session_state.messages.append(("assistant", explanation))
    st.session_state.match_table = matches
    st.session_state.applied_weights = build_weights(state.structured)
    st.session_state.user_happiness = build_user_profile(state.structured)["Happiness_Level"]
    st.session_state.finished = True
    st.session_state.ui_phase = UI_DONE
    state.finished = True


def process_chat_turn(user_text: str) -> None:
    state: ChatState = st.session_state.chat_state
    st.session_state.messages.append(("user", user_text))

    ok, hint = parse_answer_rule(state, user_text)
    if not ok:
        st.session_state.messages.append(("assistant", f"⚠️ {hint}"))
        return

    if has_enough_info(state):
        finish_matching()
        return

    if state.questions_asked >= MAX_MATCHING_QUESTIONS:
        finish_matching(used_defaults=True)
        return

    next_q = ask_next_question(state)
    if next_q is None:
        finish_matching(used_defaults=not is_matching_complete(state.structured))
        return

    st.session_state.messages.append(
        (
            "assistant",
            f"_매칭 선호 · {state.questions_asked}/{MAX_MATCHING_QUESTIONS}_\n\n{next_q}",
        )
    )


def render_kci_research_panel(state: ChatState, *, expanded: bool = False) -> None:
    """KCI 논문 반영 내용·가중치를 메인 영역에 표시."""
    with st.expander("📚 KCI 논문 기반 매칭 로직", expanded=expanded):
        st.markdown(f"**핵심 발견:** {KCI_FINDING_SUMMARY}")
        st.caption(KCI_CITATION)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**논문 4요인 vs 프로젝트 매핑**")
            factors = get_kci_factor_display_df(str(DATA_DIR))
            if not factors.empty:
                st.dataframe(factors, use_container_width=True, hide_index=True)
            else:
                st.info("kci_research_data.csv 를 찾을 수 없습니다.")

        with col2:
            st.markdown("**현재 적용 가중치**")
            weights_df = get_weights_chart_df(state.structured, str(DATA_DIR))
            st.bar_chart(weights_df.set_index("항목")["가중치"], horizontal=True)
            st.caption(
                "「룸메이트 행복」이 논문에서 유일한 유의 예측 변수(β=0.41)이므로 "
                "가장 높은 가중치를 부여합니다. 채팅에서 중요도를 입력하면 해당 항목이 조정됩니다."
            )

        if state.structured.get("profile"):
            happiness = get_profile_happiness_level(state.structured["profile"])
            st.metric(
                "본인 행복 수준 (추정, 1~7)",
                f"{happiness}",
                help="수면 시간·수면의 질·스트레스 기본값으로 추정. 후보는 CSV의 Happiness_Level 사용.",
            )


def render_kci_results_panel(state: ChatState) -> None:
    """매칭 완료 후 논문 반영·점수 로직 상세."""
    st.subheader("📊 논문 반영 · 점수 로직")
    st.markdown(KCI_FINDING_SUMMARY)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("본인 행복 수준", f"{st.session_state.get('user_happiness', '-')} / 7")
    with c2:
        top_w = st.session_state.get("applied_weights", {})
        st.metric("최고 가중치 항목", "룸메이트 행복", f"{top_w.get('happiness', '-')}점")
    with c3:
        st.metric("후보 풀", f"{st.session_state.get('candidate_count', 0):,}명")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**적용된 매칭 가중치**")
        weights_df = get_weights_chart_df(state.structured, str(DATA_DIR))
        st.bar_chart(weights_df.set_index("항목")["가중치"], horizontal=True)
        st.dataframe(weights_df, use_container_width=True, hide_index=True)

    with col_b:
        st.markdown("**점수 계산 방식**")
        st.markdown(
            """
| 항목 | 비교 방식 |
|------|-----------|
| **룸메이트 행복** | Happiness_Level 차이 (KCI 최고 가중치) |
| 흡연 | 일치 시 가산, 불일치 시 큰 감점 |
| 청소·음식·소음 | 습관 차이에 따라 가산/감점 |
| 나이·수면·활동량 | 차이가 클수록 감점 |

- 후보 **Happiness_Level**: 수면의 질·스트레스·수면시간으로 1~7 계산
- 본인 **Happiness_Level**: 폼 입력 후 기본 수면값으로 추정
            """
        )

    st.markdown("**논문 요인 데이터**")
    st.dataframe(
        get_kci_factor_display_df(str(DATA_DIR)),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(KCI_CITATION)


def render_profile_form() -> None:
    st.subheader("1단계 · 본인 정보")
    st.caption("기본 정보는 폼으로 입력합니다. (API 불필요)")

    with st.form("profile_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            gender_label = st.selectbox("성별", ["남성", "여성"])
            age = st.number_input("나이", min_value=18, max_value=60, value=23)
            smoking_label = st.selectbox("흡연", ["비흡연", "흡연"])
        with col2:
            cleaning_label = st.selectbox(
                "청소 습관",
                ["매일", "주 2~3회", "주 1회", "거의 안 함"],
            )
            eating_label = st.selectbox(
                "방 안 음식",
                ["불가", "간식·음료", "배달·식사까지"],
            )
            noise = st.slider("소음 민감도 (1=둔감 ~ 5=예민)", 1, 5, 3)

        submitted = st.form_submit_button("다음 단계로 (룸메이트 선호 채팅)", type="primary")

    if not submitted:
        return

    gender_map = {"남성": "Male", "여성": "Female"}
    smoking_map = {"비흡연": 0, "흡연": 1}
    cleaning_map = {"매일": 0, "주 2~3회": 1, "주 1회": 2, "거의 안 함": 3}
    eating_map = {"불가": 0, "간식·음료": 1, "배달·식사까지": 2}

    state: ChatState = st.session_state.chat_state
    set_profile_from_form(
        state.structured,
        gender=gender_map[gender_label],
        age=int(age),
        smoking=smoking_map[smoking_label],
        cleaning_habit=cleaning_map[cleaning_label],
        eating_in_room=eating_map[eating_label],
        noise_sensitivity=int(noise),
    )
    state.phase = PHASE_MATCHING
    begin_matching_chat()
    st.rerun()


def render_sidebar(state: ChatState) -> None:
    st.sidebar.header("룸메이트 매칭")
    st.sidebar.caption("API 없이 동작 · KCI 논문 가중치 반영")

    if st.session_state.get("candidate_count"):
        st.sidebar.metric("후보 풀", f"{st.session_state.candidate_count:,}명")

    phase_labels = {
        UI_FORM: "1단계 · 본인 정보 (폼)",
        UI_CHAT: "2단계 · 룸메이트 선호 (채팅)",
        UI_DONE: "완료",
    }
    st.sidebar.markdown(f"**현재:** {phase_labels.get(st.session_state.ui_phase, '-')}")

    with st.sidebar.expander("📚 KCI 논문 요약", expanded=st.session_state.ui_phase == UI_DONE):
        st.markdown(KCI_FINDING_SUMMARY)
        if state.structured.get("profile"):
            h = get_profile_happiness_level(state.structured["profile"])
            st.metric("행복 수준 (추정)", f"{h} / 7")
        wdf = get_weights_chart_df(state.structured, str(DATA_DIR))
        st.bar_chart(wdf.set_index("항목")["가중치"], horizontal=True)

    if st.session_state.ui_phase == UI_CHAT:
        st.sidebar.progress(
            min(state.questions_asked / MAX_MATCHING_QUESTIONS, 1.0),
            text=f"매칭 질문 {state.questions_asked}/{MAX_MATCHING_QUESTIONS}",
        )

    if state.structured["profile"]:
        st.sidebar.subheader("본인 정보")
        st.sidebar.json(state.structured["profile"])

    if state.structured["filters"] or state.structured["weights"]:
        st.sidebar.subheader("매칭 선호")
        if state.structured["filters"]:
            st.sidebar.json(state.structured["filters"])
        if state.structured["weights"]:
            st.sidebar.json(state.structured["weights"])

    if st.sidebar.button("처음부터 다시", use_container_width=True):
        reset_all()


def render_chat() -> None:
    for role, content in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(content)

    if st.session_state.finished:
        if "match_table" in st.session_state:
            tab_matches, tab_kci = st.tabs(["상위 매칭 후보", "논문 반영 · 점수 로직"])
            with tab_matches:
                st.dataframe(st.session_state.match_table, use_container_width=True)
            with tab_kci:
                render_kci_results_panel(st.session_state.chat_state)
        return

    if prompt := st.chat_input("룸메이트 선호를 입력하세요..."):
        process_chat_turn(prompt)
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="룸메이트 매칭", page_icon="🏠", layout="wide")

    base_csv = DATA_DIR / "Sleep_health_and_lifestyle_dataset.csv"
    if not base_csv.exists() and not (DATA_DIR / CANDIDATES_FILE).exists():
        st.error("데이터 파일이 없습니다. Sleep_health_and_lifestyle_dataset.csv 가 필요합니다.")
        st.stop()

    init_session()
    state: ChatState = st.session_state.chat_state
    render_sidebar(state)

    st.title("🏠 룸메이트 매칭")
    st.caption(
        "폼으로 본인 정보 입력 → 채팅으로 룸메이트 선호 입력 · "
        "KCI 논문(신지은 et al., 2017) 기반 가중치 적용"
    )

    render_kci_research_panel(
        state,
        expanded=st.session_state.ui_phase in (UI_FORM, UI_DONE),
    )

    if st.session_state.ui_phase == UI_FORM:
        render_profile_form()
    elif st.session_state.ui_phase in (UI_CHAT, UI_DONE):
        st.subheader("2단계 · 룸메이트 선호")
        render_chat()


if __name__ == "__main__":
    main()
