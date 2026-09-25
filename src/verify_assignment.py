# pip install pandas openpyxl
"""
STAGE 3 (optional but recommended): final reconciliation check.

Run this AFTER finalize-assignment. It independently re-derives, straight
from the two raw source files, what the final output SHOULD contain, and
diffs that against what's actually in data_files/final/ - so a bug
anywhere earlier in the pipeline (a dropped row, a mangled name, a
corrupted topic id) gets caught here rather than silently shipped.

Does NOT modify anything - read-only, prints a report and exits non-zero
if it finds a discrepancy worth looking at.

Checks:
  1. Every student in the raw Forms export (latest submission per UTORid)
     appears exactly once in the final assignment - nothing dropped, nothing
     duplicated, nothing extra.
  2. Each student's name in the final output matches their name in the raw
     export - names weren't dropped or corrupted along the way.
  3. Every topic_id assigned in the final output exists in the master topics
     workbook, and its name matches the master list exactly - catches a
     corrupted/stale topics_lookup.csv or a manually-typo'd custom topic.
  4. No topic_id was assigned to more than one student.

A name/topic MISMATCH is reported but not necessarily wrong - e.g. a
custom topic you hand-assigned from suggestions_review_annotated.csv will
legitimately not exist in the master workbook. Read the report; it's a
prompt for a human look, not an automatic pass/fail on its own.
"""
import re
import sys

import pandas as pd

# ==================== CONFIG ====================
PREFS_XLSX = "data_files/raw/prefs.xlsx"
TOPICS_XLSX = r"C:\Users\aviga\OneDrive - University of Toronto\CIV 220 - 2026 TA\Mini-Project\CIV220 Fall 2026 Mini Project Topics (Sign-up sheet).xlsx"
TOPICS_SHEET_NAME = "Sign-up-sheet"
TOPICS_HEADER_ROW = 2  # 0-indexed -> row 3 in Excel

COL_UTORID = "Your UTORid:"
COL_NAME = "Your name:"

ASSIGNMENT_READABLE_CSV = "data_files/final/assignment_readable.csv"
# =================================================


def clean(s):
    return str(s).replace("\xa0", " ").strip()


def load_expected_students():
    raw = pd.read_excel(PREFS_XLSX, sheet_name=0)
    raw.columns = [clean(c) if isinstance(c, str) else c for c in raw.columns]
    raw[COL_UTORID] = raw[COL_UTORID].astype(str).str.strip()
    raw[COL_NAME] = raw[COL_NAME].astype(str).str.strip()
    # same "keep latest resubmission" rule as convert_prefs.py
    raw = raw.sort_values("Completion time").drop_duplicates(subset=[COL_UTORID], keep="last")
    return dict(zip(raw[COL_UTORID], raw[COL_NAME]))


def load_master_topics():
    df = pd.read_excel(TOPICS_XLSX, sheet_name=TOPICS_SHEET_NAME, header=TOPICS_HEADER_ROW)
    df.columns = [str(c).strip() for c in df.columns]
    df["CODE"] = pd.to_numeric(df["CODE"], errors="coerce")
    df = df.dropna(subset=["CODE"])
    df["CODE"] = df["CODE"].astype(int)
    df["topic_id"] = df["CODE"].apply(lambda c: f"Topic{c:03d}")
    df["topic_name"] = df["TOPIC NAME"].astype(str).str.strip()
    return dict(zip(df["topic_id"], df["topic_name"]))


def main():
    problems = []

    expected_students = load_expected_students()
    master_topics = load_master_topics()

    final = pd.read_csv(ASSIGNMENT_READABLE_CSV, dtype=str)
    final["utorid"] = final["utorid"].astype(str).str.strip()

    # --- 1. student set: missing / extra / duplicated ---
    expected_ids = set(expected_students)
    final_ids_list = final["utorid"].tolist()
    final_ids = set(final_ids_list)

    missing = expected_ids - final_ids
    extra = final_ids - expected_ids
    dupes = sorted({s for s in final_ids_list if final_ids_list.count(s) > 1})

    if missing:
        problems.append(f"{len(missing)} student(s) in the raw export are MISSING from the final assignment: {sorted(missing)}")
    if extra:
        problems.append(f"{len(extra)} student(s) in the final assignment do not appear in the raw export: {sorted(extra)}")
    if dupes:
        problems.append(f"{len(dupes)} student(s) appear more than once in the final assignment: {dupes}")

    # --- 2. name integrity ---
    name_mismatches = []
    for _, row in final.iterrows():
        utorid = row["utorid"]
        if utorid not in expected_students:
            continue
        expected_name = clean(expected_students[utorid])
        final_name = clean(row["name"]) if pd.notna(row["name"]) else ""
        if not final_name:
            name_mismatches.append(f"  {utorid}: name is BLANK in final output (expected {expected_name!r})")
        elif final_name != expected_name:
            name_mismatches.append(f"  {utorid}: final name {final_name!r} != raw export name {expected_name!r}")
    if name_mismatches:
        problems.append(f"{len(name_mismatches)} student name mismatch(es):\n" + "\n".join(name_mismatches))

    # --- 3. topic id/name integrity ---
    topic_mismatches = []
    for _, row in final.iterrows():
        topic_id = row["topic_id"]
        final_topic_name = clean(row["topic_name"]) if pd.notna(row["topic_name"]) else ""
        if topic_id not in master_topics:
            topic_mismatches.append(f"  {row['utorid']}: topic_id {topic_id} not found in master topics workbook (custom/suggested topic?)")
            continue
        master_name = clean(master_topics[topic_id])
        if final_topic_name != master_name:
            topic_mismatches.append(f"  {row['utorid']}: {topic_id} name {final_topic_name!r} != master list name {master_name!r}")
    if topic_mismatches:
        problems.append(f"{len(topic_mismatches)} topic mismatch(es) (not necessarily wrong - check for intentional custom topics):\n" + "\n".join(topic_mismatches))

    # --- 4. no topic assigned twice ---
    topic_ids_list = final["topic_id"].tolist()
    dup_topics = sorted({t for t in topic_ids_list if topic_ids_list.count(t) > 1})
    if dup_topics:
        problems.append(f"{len(dup_topics)} topic(s) assigned to more than one student: {dup_topics}")

    print(f"Checked {len(final)} students in {ASSIGNMENT_READABLE_CSV} against:")
    print(f"  {len(expected_students)} unique students in {PREFS_XLSX}")
    print(f"  {len(master_topics)} topics in the master workbook")
    print()

    if not problems:
        print("PASS - no discrepancies found.")
        return

    print(f"{len(problems)} issue(s) found:\n")
    for p in problems:
        print(f"- {p}\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
