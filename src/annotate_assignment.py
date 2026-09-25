# pip install pandas
"""
Post-processing step, run AFTER assigner.py.

assigner.py's assignment.csv only has "student" (UTORid) and "topic_id"
(TopicNNN) - fine for the algorithm, not fine for pasting into the "Final"
sheet, which wants an actual name and topic name. This joins in:
  - the student's real name, via utorid_name_map.csv (from convert_prefs.py)
  - the topic's real name, via topics_lookup.csv (from convert_topics.py)

Does NOT modify assigner.py or assignment.csv itself.

Output (gitignored by default via the repo's blanket .gitignore rule):
  - assignment_readable.csv : name, utorid, topic_id, topic_name, rank_assigned,
                               cost, won_lottery, assigned_unranked
"""
import pandas as pd

from paths import ensure_dir

ASSIGNMENT_CSV = "data_files/final/assignment.csv"
NAME_MAP_CSV = "data_files/processed/utorid_name_map.csv"
TOPICS_LOOKUP_CSV = "data_files/processed/topics_lookup.csv"
OUT_CSV = "data_files/final/assignment_readable.csv"


def main():
    assignment = pd.read_csv(ASSIGNMENT_CSV, dtype={"student": str})
    name_map = pd.read_csv(NAME_MAP_CSV, dtype={"utorid": str})
    topics_lookup = pd.read_csv(TOPICS_LOOKUP_CSV, dtype=str)

    merged = assignment.merge(
        name_map, left_on="student", right_on="utorid", how="left"
    ).merge(
        topics_lookup, on="topic_id", how="left"
    )

    missing_name = merged["name"].isna().sum()
    missing_topic = merged["topic_name"].isna().sum()
    if missing_name:
        print(f"WARNING: {missing_name} student(s) had no match in {NAME_MAP_CSV}.")
    if missing_topic:
        print(f"WARNING: {missing_topic} topic(s) had no match in {TOPICS_LOOKUP_CSV}.")

    out = merged[[
        "name", "student", "topic_id", "topic_name",
        "rank_assigned", "cost", "won_lottery", "assigned_unranked",
    ]].rename(columns={"student": "utorid"}).sort_values("name")

    ensure_dir(OUT_CSV)
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(out)} rows to {OUT_CSV}")


if __name__ == "__main__":
    main()
