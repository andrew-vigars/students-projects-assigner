# pip install pandas openpyxl
"""
One-off converter: turns the master topics sign-up sheet (xlsx) into the
plain single-column TOPICS_CSV format assigner.py expects (no header,
one 'TopicNNN' id per row).

Does NOT touch assigner.py or any of its inputs/outputs.

Outputs (both gitignored by default via the repo's blanket .gitignore rule):
  - topics.csv          : plain list of TopicNNN ids -> feed this to assigner.py's TOPICS_CSV
  - topics_lookup.csv    : topic_id,topic_name reference map, so assignment.csv's
                            "TopicNNN" ids can be translated back to human-readable
                            names when pasting results into the "Final" sheet.
"""
import pandas as pd

from paths import ensure_dir

# ==================== CONFIG ====================
TOPICS_XLSX = r"C:\Users\aviga\OneDrive - University of Toronto\CIV 220 - 2026 TA\Mini-Project\CIV220 Fall 2026 Mini Project Topics (Sign-up sheet).xlsx"
SHEET_NAME = "Sign-up-sheet"   # master topics list lives here (NOT the "Final" sheet)
HEADER_ROW = 2                 # 0-indexed -> row 3 in Excel, where CODE / TOPIC NAME / ... live
OUT_TOPICS_CSV = "data_files/processed/topics.csv"
OUT_LOOKUP_CSV = "data_files/processed/topics_lookup.csv"
# =================================================


def main():
    df = pd.read_excel(TOPICS_XLSX, sheet_name=SHEET_NAME, header=HEADER_ROW)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"CODE", "TOPIC NAME"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Expected columns {required} in sheet '{SHEET_NAME}', missing: {missing}")

    # Only exclude topics explicitly marked unavailable; keep everything else
    # (all 315 are currently 'Yes', but this keeps the script correct if that changes)
    if "Available?" in df.columns:
        before = len(df)
        df = df[df["Available?"].astype(str).str.strip().str.lower() != "no"]
        dropped = before - len(df)
        if dropped:
            print(f"Excluded {dropped} topic(s) marked unavailable.")

    df["CODE"] = pd.to_numeric(df["CODE"], errors="coerce")
    bad_codes = df[df["CODE"].isna()]
    if len(bad_codes):
        print(f"WARNING: {len(bad_codes)} row(s) have a non-numeric CODE and will be skipped.")
        df = df.dropna(subset=["CODE"])
    df["CODE"] = df["CODE"].astype(int)

    dup_codes = df[df["CODE"].duplicated(keep=False)]
    if len(dup_codes):
        print(f"WARNING: duplicate CODE values found: {sorted(dup_codes['CODE'].unique().tolist())}")

    df["topic_id"] = df["CODE"].apply(lambda c: f"Topic{c:03d}")
    df["topic_name"] = df["TOPIC NAME"].astype(str).str.strip()

    # plain single-column CSV, no header, no index -> what assigner.py's TOPICS_CSV loader expects
    ensure_dir(OUT_TOPICS_CSV)
    df[["topic_id"]].to_csv(OUT_TOPICS_CSV, header=False, index=False)

    # human-readable lookup, for translating assignment.csv's TopicNNN ids back to names
    ensure_dir(OUT_LOOKUP_CSV)
    df[["topic_id", "topic_name"]].to_csv(OUT_LOOKUP_CSV, index=False)

    print(f"Wrote {len(df)} topics to {OUT_TOPICS_CSV}")
    print(f"Wrote lookup table to {OUT_LOOKUP_CSV}")


if __name__ == "__main__":
    main()
