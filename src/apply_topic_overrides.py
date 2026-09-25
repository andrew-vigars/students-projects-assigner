"""
Optional step, run at the end of process-data (Stage 1), AFTER prefs.csv
and topics.csv/topics_lookup.csv already exist.

Implements the rule stated on the Forms: "if we like your suggested topic,
we'll assign it as your first choice." For each approved custom-topic
student, this:
  1. Assigns their suggested topic a new sequential TopicNNN id (continuing
     the existing numbering, not a separate namespace).
  2. Appends it to topics.csv and topics_lookup.csv.
  3. In prefs.csv, sets rank1 = the new custom topic and shifts their real
     choices down a slot (old rank1->rank2, rank2->rank3, rank3->rank4,
     rank4->rank5, dropping the old rank5). This is safe to drop: a
     guaranteed-win rank1 (nobody else can rank a brand-new topic) means
     the lottery locks them in immediately - they never reach the
     optimizer, so rank2-5 are never actually consulted for them.

The effect is a genuine re-run: since the custom topic is uncontested, the
student's ORIGINAL rank1 topic (which they may have won via lottery)
authentically reopens and flows back through the real lottery/optimizer in
finalize-assignment, rather than being patched by hand - so whoever lost
that original lottery gets a fair shot at it.

Entirely optional and skipped cleanly if data_files/raw/topic_overrides.csv
doesn't exist - years without custom topics are unaffected.

Input:
  data_files/raw/topic_overrides.csv, columns: utorid, custom_topic_name
    utorid must match exactly what's in prefs.csv's "student" column -
    for a student who submitted using a student number instead of a
    UTORid (see flagged_utorids.csv), use that number here too.

Output (modified in place):
  data_files/processed/prefs.csv
  data_files/processed/topics.csv
  data_files/processed/topics_lookup.csv
Output (new):
  data_files/processed/topic_overrides_applied.csv - audit trail: utorid,
  the new custom topic id/name, and which topic they had as rank1 before
  (now reopened).
"""
import os
import re

import pandas as pd

from paths import ensure_dir

# ==================== CONFIG ====================
OVERRIDES_CSV = "data_files/raw/topic_overrides.csv"
PREFS_CSV = "data_files/processed/prefs.csv"
TOPICS_CSV = "data_files/processed/topics.csv"
TOPICS_LOOKUP_CSV = "data_files/processed/topics_lookup.csv"
OUT_AUDIT_CSV = "data_files/processed/topic_overrides_applied.csv"
# =================================================


def main():
    if not os.path.exists(OVERRIDES_CSV):
        print(f"No {OVERRIDES_CSV} found - skipping (no custom topic overrides to apply).")
        return

    overrides = pd.read_csv(OVERRIDES_CSV, dtype=str)
    overrides["utorid"] = overrides["utorid"].astype(str).str.strip()
    overrides["custom_topic_name"] = overrides["custom_topic_name"].astype(str).str.strip()

    dupes = overrides.loc[overrides["utorid"].duplicated(keep=False), "utorid"].unique().tolist()
    if dupes:
        print(f"WARNING: duplicate utorid(s) in {OVERRIDES_CSV}, keeping first occurrence: {dupes}")
        overrides = overrides.drop_duplicates(subset=["utorid"], keep="first")

    topics_lookup = pd.read_csv(TOPICS_LOOKUP_CSV, dtype=str)
    existing_names_lower = set(topics_lookup["topic_name"].str.strip().str.lower())
    existing_codes = [int(m.group(1)) for t in topics_lookup["topic_id"] if (m := re.fullmatch(r"Topic(\d+)", t))]
    next_code = max(existing_codes, default=0) + 1

    prefs = pd.read_csv(PREFS_CSV, dtype=str).fillna("")
    rank_cols = sorted(
        [c for c in prefs.columns if c.lower().startswith("rank")],
        key=lambda c: int("".join(ch for ch in c if ch.isdigit()) or 0),
    )
    prefs_idx = {s: i for i, s in enumerate(prefs["student"])}

    new_topic_rows = []
    audit_rows = []

    for _, row in overrides.iterrows():
        utorid = row["utorid"]
        custom_name = row["custom_topic_name"]

        if utorid not in prefs_idx:
            print(f"WARNING: utorid {utorid!r} not found in {PREFS_CSV}'s student column - skipping override "
                  f"(check it matches exactly, including a student-number id if that's what they submitted with).")
            continue

        if custom_name.lower() in existing_names_lower:
            print(f"NOTE: {custom_name!r} (for {utorid}) looks like it may already be on the master topic list "
                  f"- double check this is really a new topic before trusting this override.")

        new_topic_id = f"Topic{next_code:03d}"
        next_code += 1

        idx = prefs_idx[utorid]
        old_values = [prefs.at[idx, c] for c in rank_cols]
        old_rank1 = old_values[0]

        prefs.at[idx, rank_cols[0]] = new_topic_id
        for col, val in zip(rank_cols[1:], old_values[:-1]):
            prefs.at[idx, col] = val

        new_topic_rows.append({"topic_id": new_topic_id, "topic_name": custom_name})
        audit_rows.append({
            "utorid": utorid,
            "custom_topic_id": new_topic_id,
            "custom_topic_name": custom_name,
            "reopened_topic_id": old_rank1,
        })

    if not new_topic_rows:
        print("No overrides applied.")
        return

    ensure_dir(TOPICS_CSV)
    with open(TOPICS_CSV, "a", newline="") as f:
        for r in new_topic_rows:
            f.write(r["topic_id"] + "\n")

    ensure_dir(TOPICS_LOOKUP_CSV)
    pd.DataFrame(new_topic_rows).to_csv(TOPICS_LOOKUP_CSV, mode="a", header=False, index=False)

    ensure_dir(PREFS_CSV)
    prefs.to_csv(PREFS_CSV, index=False)

    ensure_dir(OUT_AUDIT_CSV)
    pd.DataFrame(audit_rows).to_csv(OUT_AUDIT_CSV, index=False)

    print(f"Applied {len(new_topic_rows)} custom topic override(s):")
    for r in audit_rows:
        print(f"  {r['utorid']}: rank1 -> {r['custom_topic_id']} ({r['custom_topic_name']}), "
              f"reopens {r['reopened_topic_id']}")
    print(f"\nUpdated {PREFS_CSV}, {TOPICS_CSV}, {TOPICS_LOOKUP_CSV}")
    print(f"Audit trail written to {OUT_AUDIT_CSV}")


if __name__ == "__main__":
    main()
