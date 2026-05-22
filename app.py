import os
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

load_dotenv(Path(__file__).parent / ".env")

from roommate_match_chat import (
    MAX_QUESTIONS,
    PHASE_MATCHING,
    PHASE_PROFILE,
    ChatState,
    ask_next_question,
    call_llm_parse_answer,
    format_profile_summary,
    get_gemini_client,
    has_enough_info,
    load_dataset,
    maybe_advance_phase,
    run_matching_results,
)

CSV_PATH = Path(__file__).parent / "Sleep_health_and_lifestyle_dataset.csv"


def init_session() -> None:
    if "chat_state" not in st.session_state:
        st.session_state.chat_state = ChatState()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "finished" not in st.session_state:
        st.session_state.finished = False
    if "df" not in st.session_state:
        st.session_state.df = load_dataset(str(CSV_PATH))
    if "client" not in st.session_state:
        st.session_state.client = get_gemini_client()
    if "bootstrapped" not in st.session_state:
        st.session_state.bootstrapped = False


def bootstrap_chat() -> None:
    if st.session_state.bootstrapped:
        return
    st.session_state.messages.append(
        (
            "assistant",
            "안녕하세요! **룸메이트 매칭 도우미**입니다.\n\n"
            "1️⃣ 먼저 **본인 정보**를 받고  \n"
            "2️⃣ 이어서 **룸메이트 선호**를 물어본 뒤  \n"
            "가장 잘 맞는 후보를 추천해 드립니다.\n\n"
            "---\n"
            "**1단계: 본인 정보 입력**",
        )
    )
    first = ask_next_question(st.session_state.chat_state)
    if first:
        st.session_state.messages.append(("assistant", first))
    st.session_state.bootstrapped = True


def append_phase_transition() -> None:
    summary = format_profile_summary(st.session_state.chat_state)
    st.session_state.messages.append(
        (
            "assistant",
            summary
            + "\n\n---\n**2단계: 룸메이트 매칭 선호 입력**\n"
            "이제 원하시는 룸메이트 조건과 중요도를 알려주세요.",
        )
    )
    next_q = ask_next_question(st.session_state.chat_state)
    if next_q:
        st.session_state.messages.append(("assistant", next_q))


def finish_matching(*, used_defaults: bool = False) -> None:
    state = st.session_state.chat_state
    with st.spinner("매칭 결과를 계산하는 중..."):
        matches, explanation, notice = run_matching_results(
            st.session_state.client,
            state,
            st.session_state.df,
            used_defaults=used_defaults,
        )
    if notice:
        st.session_state.messages.append(("assistant", f"ℹ️ {notice}"))
    st.session_state.messages.append(
        ("assistant", f"### 매칭 결과 설명\n\n{explanation}")
    )
    st.session_state.match_table = matches
    st.session_state.finished = True
    state.finished = True


def process_turn(user_text: str) -> None:
    state: ChatState = st.session_state.chat_state
    client = st.session_state.client

    st.session_state.messages.append(("user", user_text))

    with st.spinner("답변을 분석하는 중..."):
        call_llm_parse_answer(client, state, user_text)

    if maybe_advance_phase(state):
        append_phase_transition()
        if has_enough_info(state):
            finish_matching()
            return

    if has_enough_info(state):
        finish_matching()
        return

    if state.questions_asked >= MAX_QUESTIONS:
        finish_matching(used_defaults=True)
        return

    next_q = ask_next_question(state)
    if next_q is None:
        if state.phase == PHASE_PROFILE:
            maybe_advance_phase(state)
            append_phase_transition()
            next_q = ask_next_question(state)
        if next_q is None:
            finish_matching(used_defaults=not has_enough_info(state))
            return

    phase_label = "본인 정보" if state.phase == PHASE_PROFILE else "매칭 선호"
    st.session_state.messages.append(
        (
            "assistant",
            f"_{phase_label} · {state.questions_asked}/{MAX_QUESTIONS}_\n\n{next_q}",
        )
    )


def render_sidebar(state: ChatState) -> None:
    st.sidebar.header("진행 상황")
    phase_name = "1단계 · 본인 정보" if state.phase == PHASE_PROFILE else "2단계 · 매칭 선호"
    st.sidebar.markdown(f"**현재:** {phase_name}")
    st.sidebar.progress(
        min(state.questions_asked / MAX_QUESTIONS, 1.0),
        text=f"질문 {state.questions_asked} / {MAX_QUESTIONS}",
    )

    if state.structured["profile"]:
        st.sidebar.subheader("입력된 본인 정보")
        st.sidebar.json(state.structured["profile"])

    if state.phase == PHASE_MATCHING and (
        state.structured["filters"] or state.structured["weights"]
    ):
        st.sidebar.subheader("매칭 선호")
        if state.structured["filters"]:
            st.sidebar.caption("필터")
            st.sidebar.json(state.structured["filters"])
        if state.structured["weights"]:
            st.sidebar.caption("중요도")
            st.sidebar.json(state.structured["weights"])

    if st.sidebar.button("대화 초기화", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="룸메이트 매칭",
        page_icon="🏠",
        layout="wide",
    )

    if not CSV_PATH.exists():
        st.error(f"데이터 파일이 없습니다: {CSV_PATH.name}")
        st.stop()

    try:
        init_session()
    except RuntimeError as exc:
        st.error(str(exc))
        st.info(
            "로컬: `$env:GEMINI_API_KEY = '키'`  \n"
            "Streamlit Cloud: Secrets에 `GEMINI_API_KEY` 추가"
        )
        st.stop()

    state: ChatState = st.session_state.chat_state
    render_sidebar(state)

    st.title("🏠 룸메이트 매칭")
    st.caption("본인 정보 우선 입력 → 추가 질문으로 최적 룸메이트 추천")

    bootstrap_chat()

    for role, content in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(content)

    if st.session_state.finished:
        if "match_table" in st.session_state:
            st.subheader("상위 매칭 후보")
            st.dataframe(st.session_state.match_table, use_container_width=True)
        return

    if prompt := st.chat_input("메시지를 입력하세요..."):
        process_turn(prompt)
        st.rerun()


if __name__ == "__main__":
    main()
