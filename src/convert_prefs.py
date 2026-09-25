# pip install pandas openpyxl
"""
One-off converter: turns the raw Microsoft Forms export (xlsx) into the
wide-format prefs.csv assigner.py expects (student,rank1..rank5).

Does NOT touch assigner.py or any of its inputs/outputs.

Choice values in the raw export look like "21_Bike Share Services" (some
have stray whitespace, inconsistent topic names for the same id, or are
pure free text with no numeric id at all - typically off-list write-ins).
This script matches on the LEADING NUMERIC ID ONLY (ignoring the name text
after the underscore), and cross-checks it against the master topic list
in convert_topics.py's TOPICS_XLSX/SHEET_NAME so a typo'd/renamed topic
name never causes a silent mismatch.

Anything that can't be confidently mapped is left OUT of prefs.csv and
logged to unmatched_choices.csv for manual review, rather than guessed.

Outputs (all gitignored by default via the repo's blanket .gitignore rule):
  - prefs.csv               : student,rank1..rank5 -> feed this to assigner.py's PREFS_CSV
  - utorid_name_map.csv      : utorid,name reference map (assigner.py never sees names)
  - unmatched_choices.csv    : rows where a ranked choice couldn't be matched to a topic id
  - suggestions_review.csv   : the free-text "new topic idea" responses, for manual
                                similarity-checking before you hand-assign a custom topic
  - flagged_utorids.csv      : rows where the "UTORid" field looks like a student number
                                instead of a UTORid string, for manual sanity-checking
"""
import re
import pandas as pd

from paths import ensure_dir

# ==================== CONFIG ====================
PREFS_XLSX = "data_files/raw/prefs.xlsx"
TOPICS_XLSX = r"C:\Users\aviga\OneDrive - University of Toronto\CIV 220 - 2026 TA\Mini-Project\CIV220 Fall 2026 Mini Project Topics (Sign-up sheet).xlsx"
TOPICS_SHEET_NAME = "Sign-up-sheet"
TOPICS_HEADER_ROW = 2  # 0-indexed -> row 3 in Excel

COL_UTORID = "Your UTORid:"
COL_NAME = "Your name:"
CHOICE_COLS = ["1st Choice", "2nd Choice", "3rd\xa0Choice", "4th\xa0Choice", "5th\xa0Choice"]
COL_SUGGESTION = "Got a topic to suggest that isn't on the list? Let us know below:"

OUT_PREFS_CSV = "data_files/processed/prefs.csv"
OUT_NAME_MAP_CSV = "data_files/processed/utorid_name_map.csv"
OUT_UNMATCHED_CSV = "data_files/processed/unmatched_choices.csv"
OUT_SUGGESTIONS_CSV = "data_files/processed/suggestions_review.csv"
OUT_FLAGGED_UTORID_CSV = "data_files/processed/flagged_utorids.csv"
# =================================================


def load_valid_codes():
    df = pd.read_excel(TOPICS_XLSX, sheet_name=TOPICS_SHEET_NAME, header=TOPICS_HEADER_ROW)
    df.columns = [str(c).strip() for c in df.columns]
    codes = pd.to_numeric(df["CODE"], errors="coerce").dropna().astype(int)
    return set(codes.tolist())


def parse_choice(raw_value, valid_codes):
    """Returns (topic_id_or_None, reason_if_unmatched_or_None).

    Matches a LEADING run of digits, regardless of what separates it from
    the topic name after it (underscore, space, "_ ", " _", missing
    separator, etc.) - e.g. "21_Bike Share", "268 _ timber buildings",
    "268timber buildings" all resolve to the same numeric id. Only the
    number is trusted; the name text is ignored entirely.
    """
    if pd.isna(raw_value):
        return None, None  # simply not filled in - not an error
    text = str(raw_value).replace("\xa0", " ").strip()
    if not text:
        return None, None

    m = re.match(r"^\s*(\d+)", text)
    if not m:
        return None, f"no leading numeric id: {text!r}"

    code = int(m.group(1))
    if code not in valid_codes:
        return None, f"id {code} not found in master topic list: {text!r}"

    return f"Topic{code:03d}", None


def main():
    valid_codes = load_valid_codes()
    print(f"Loaded {len(valid_codes)} valid topic codes from master list.")

    raw = pd.read_excel(PREFS_XLSX, sheet_name=0)
    raw.columns = [str(c).replace("\xa0", " ").strip() if isinstance(c, str) else c for c in raw.columns]
    # normalize the CHOICE_COLS names too (source list has \xa0 variants)
    norm_choice_cols = [c.replace("\xa0", " ") for c in CHOICE_COLS]

    missing_cols = {COL_UTORID, COL_NAME, COL_SUGGESTION} | set(norm_choice_cols)
    missing_cols -= set(raw.columns)
    if missing_cols:
        raise ValueError(f"Expected columns not found in {PREFS_XLSX}: {missing_cols}")

    raw[COL_UTORID] = raw[COL_UTORID].astype(str).str.strip()
    raw[COL_NAME] = raw[COL_NAME].astype(str).str.strip()

    if raw[COL_UTORID].duplicated().any():
        dupes = raw.loc[raw[COL_UTORID].duplicated(keep=False), COL_UTORID].unique().tolist()
        before = len(raw)
        # keep the latest submission per UTORid (resubmissions are assumed to be corrections)
        raw = raw.sort_values("Completion time").drop_duplicates(subset=[COL_UTORID], keep="last")
        raw = raw.sort_index()
        print(f"NOTE: {len(dupes)} UTORid(s) had multiple submissions, kept latest by Completion time: {dupes}")
        print(f"Dropped {before - len(raw)} earlier duplicate submission(s).")

    prefs_rows = []
    unmatched_rows = []
    flagged_utorid_rows = []
    suggestion_rows = []

    for _, row in raw.iterrows():
        utorid = row[COL_UTORID]
        name = row[COL_NAME]

        if utorid.replace(" ", "").isdigit():
            # catches "1012464325" and also "100 915 9205" (a student number typed with spaces)
            flagged_utorid_rows.append({"utorid_field": utorid, "name": name})

        rank_values = {}
        for rank_num, col in enumerate(norm_choice_cols, start=1):
            topic_id, reason = parse_choice(row[col], valid_codes)
            rank_values[f"rank{rank_num}"] = topic_id or ""
            if reason:
                unmatched_rows.append({
                    "utorid": utorid,
                    "name": name,
                    "rank_column": f"rank{rank_num}",
                    "raw_value": row[col],
                    "reason": reason,
                })

        prefs_rows.append({"student": utorid, **rank_values})

        suggestion = row[COL_SUGGESTION]
        if pd.notna(suggestion) and str(suggestion).strip():
            suggestion_rows.append({
                "utorid": utorid,
                "name": name,
                "suggestion": str(suggestion).strip(),
            })

    ensure_dir(OUT_PREFS_CSV)
    pd.DataFrame(prefs_rows).to_csv(OUT_PREFS_CSV, index=False)
    print(f"Wrote {len(prefs_rows)} students to {OUT_PREFS_CSV}")

    ensure_dir(OUT_NAME_MAP_CSV)
    raw[[COL_UTORID, COL_NAME]].rename(
        columns={COL_UTORID: "utorid", COL_NAME: "name"}
    ).to_csv(OUT_NAME_MAP_CSV, index=False)
    print(f"Wrote name lookup to {OUT_NAME_MAP_CSV}")

    if unmatched_rows:
        ensure_dir(OUT_UNMATCHED_CSV)
        pd.DataFrame(unmatched_rows).to_csv(OUT_UNMATCHED_CSV, index=False)
        print(f"WARNING: {len(unmatched_rows)} choice(s) could not be matched - see {OUT_UNMATCHED_CSV}")
    else:
        print("All ranked choices matched cleanly - no unmatched_choices.csv written.")

    if flagged_utorid_rows:
        ensure_dir(OUT_FLAGGED_UTORID_CSV)
        pd.DataFrame(flagged_utorid_rows).to_csv(OUT_FLAGGED_UTORID_CSV, index=False)
        print(f"WARNING: {len(flagged_utorid_rows)} row(s) have a numeric-only UTORid field - see {OUT_FLAGGED_UTORID_CSV}")

    if suggestion_rows:
        ensure_dir(OUT_SUGGESTIONS_CSV)
        pd.DataFrame(suggestion_rows).to_csv(OUT_SUGGESTIONS_CSV, index=False)
        print(f"Wrote {len(suggestion_rows)} topic suggestion(s) to {OUT_SUGGESTIONS_CSV} for manual review")


if __name__ == "__main__":
    main()
