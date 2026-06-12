from pathlib import Path

import streamlit as st

from roommate_match_chat import (
    CANDIDATES_FILE,
    MAX_MATCHING_QUESTIONS,
    PHASE_MATCHING,
    ChatState,
    ask_next_question,
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
    st.sidebar.caption("API 없이 동작합니다")
    if st.session_state.get("candidate_count"):
        st.sidebar.metric("후보 풀", f"{st.session_state.candidate_count:,}명")

    phase_labels = {
        UI_FORM: "1단계 · 본인 정보 (폼)",
        UI_CHAT: "2단계 · 룸메이트 선호 (채팅)",
        UI_DONE: "완료",
    }
    st.sidebar.markdown(f"**현재:** {phase_labels.get(st.session_state.ui_phase, '-')}")

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
            st.subheader("상위 매칭 후보")
            st.dataframe(st.session_state.match_table, use_container_width=True)
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
    st.caption("폼으로 본인 정보 입력 → 채팅으로 룸메이트 선호 입력 (API 불필요)")

    if st.session_state.ui_phase == UI_FORM:
        render_profile_form()
    elif st.session_state.ui_phase in (UI_CHAT, UI_DONE):
        st.subheader("2단계 · 룸메이트 선호")
        render_chat()


if __name__ == "__main__":
    main()
