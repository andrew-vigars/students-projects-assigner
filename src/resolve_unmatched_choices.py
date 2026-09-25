# pip install pandas
"""
Intermediate stage, run AFTER convert_prefs.py.

convert_prefs.py matches choices by leading numeric id only. Some students
typed just the topic NAME (no id prefix), so those ranks were left blank
in prefs.csv and logged to unmatched_choices.csv. This script resolves
those by matching against topics_lookup.csv's topic_name column:

  1. Exact match (case-insensitive, leading "_"/whitespace stripped) - automatic.
  2. A short, human-reviewed ALIAS_MAP for near-misses (typos, shortened
     names, encoding glitches) - only applied for pairs explicitly listed
     below, never guessed/fuzzy-matched automatically.

Anything still unresolved after both passes is left blank in prefs.csv and
written to unmatched_choices_remaining.csv - these are the genuine off-list
write-ins that should be cross-checked against suggestions_review.csv and
handled manually.

Does NOT touch assigner.py, convert_prefs.py, or convert_topics.py.
"""
import pandas as pd

from paths import ensure_dir

# ==================== CONFIG ====================
PREFS_CSV = "data_files/processed/prefs.csv"
UNMATCHED_CSV = "data_files/processed/unmatched_choices.csv"
TOPICS_LOOKUP_CSV = "data_files/processed/topics_lookup.csv"
OUT_PREFS_CSV = "data_files/processed/prefs.csv"  # overwritten in place
OUT_REMAINING_CSV = "data_files/processed/unmatched_choices_remaining.csv"

# Human-confirmed near-misses: raw Forms text (as it appears in
# unmatched_choices.csv's raw_value) -> exact topic_name in topics_lookup.csv.
# Add to this list as you confirm more matches; nothing here is guessed.
ALIAS_MAP = {
    "FIFA World Cup": "2026 FIFA World Cup",
    "The Raptors": "The Raptors (Sports Team)",
    "Queen’s park": "Queen's Park",   # smart-quote apostrophe in raw export
    "China town": "Chinatown",
    "Yorkdale": "Yorkdale Shopping Centre",
    "_Ginko Tree": "Gingko Tree",
    "Honey Bee": "Honey Bees",
}
# =================================================


def clean_name(s):
    return str(s).strip().lstrip("_").strip().lower()


def main():
    prefs = pd.read_csv(PREFS_CSV, dtype=str).fillna("")
    unmatched = pd.read_csv(UNMATCHED_CSV, dtype=str)
    lookup = pd.read_csv(TOPICS_LOOKUP_CSV, dtype=str)

    name_to_id = {clean_name(n): i for i, n in zip(lookup["topic_id"], lookup["topic_name"])}
    alias_to_id = {}
    unresolved_aliases = []
    for raw, canonical_name in ALIAS_MAP.items():
        key = clean_name(canonical_name)
        if key not in name_to_id:
            unresolved_aliases.append(canonical_name)
            continue
        alias_to_id[clean_name(raw)] = name_to_id[key]
    if unresolved_aliases:
        raise ValueError(f"ALIAS_MAP canonical name(s) not found in {TOPICS_LOOKUP_CSV}: {unresolved_aliases}")

    prefs_idx = {s: i for i, s in enumerate(prefs["student"])}

    resolved_count = 0
    still_unmatched = []

    for _, row in unmatched.iterrows():
        utorid = row["utorid"]
        rank_col = row["rank_column"]
        raw_value = row["raw_value"]

        if utorid not in prefs_idx:
            still_unmatched.append(row)
            continue

        key = clean_name(raw_value)
        topic_id = name_to_id.get(key) or alias_to_id.get(key)

        if topic_id:
            prefs.at[prefs_idx[utorid], rank_col] = topic_id
            resolved_count += 1
        else:
            still_unmatched.append(row)

    ensure_dir(OUT_PREFS_CSV)
    prefs.to_csv(OUT_PREFS_CSV, index=False)
    print(f"Resolved {resolved_count} / {len(unmatched)} previously-unmatched choices.")
    print(f"Updated {OUT_PREFS_CSV} in place.")

    if still_unmatched:
        ensure_dir(OUT_REMAINING_CSV)
        pd.DataFrame(still_unmatched).to_csv(OUT_REMAINING_CSV, index=False)
        print(f"{len(still_unmatched)} choice(s) still unresolved - see {OUT_REMAINING_CSV}")
        print("Cross-check these against suggestions_review.csv for manual handling.")
    else:
        print("Nothing left unresolved.")


if __name__ == "__main__":
    main()
