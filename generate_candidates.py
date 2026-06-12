"""대량 룸메이트 후보 CSV 생성 스크립트."""

from pathlib import Path

from roommate_match_chat import (
    BASE_DATASET_FILE,
    CANDIDATES_FILE,
    DEFAULT_CANDIDATE_COUNT,
    generate_roommate_candidates,
)

ROOT = Path(__file__).parent


def main() -> None:
    base = ROOT / BASE_DATASET_FILE
    out = ROOT / CANDIDATES_FILE
    if not base.exists():
        raise SystemExit(f"원본 데이터가 없습니다: {base}")

    df = generate_roommate_candidates(
        str(base),
        str(out),
        count=DEFAULT_CANDIDATE_COUNT,
    )
    print(f"생성 완료: {len(df)}명 → {out}")


if __name__ == "__main__":
    main()
