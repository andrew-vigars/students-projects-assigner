"""
STAGE 4 (optional, run AFTER finalize-assignment, BEFORE export-assignment):
randomly assigns a remaining topic to students who never submitted the
preferences form at all.

Does NOT re-run process-data, finalize-assignment, or touch anything they
produced (data_files/processed/prefs.csv, data_files/final/assignment.csv,
data_files/final/assignment_readable.csv are all read-only inputs here).

Compares the class roster against the existing final assignment to find
students with no submission, then randomly assigns each of them one of the
topics nobody ended up with, and writes a NEW combined file - the original
assignment_readable.csv is left untouched.

Some students submitted preferences using their student NUMBER instead of
their UTORid (see data_files/processed/flagged_utorids.csv) - they already
have a real assignment, just filed under the wrong identifier, so matching
"missing" by UTORid alone would wrongly treat them as no-shows and assign
them a SECOND, conflicting topic. This script excludes anyone whose name
matches a flagged_utorids.csv entry, to avoid that double-assignment.

Beyond that KNOWN numeric case, a student can also just typo/truncate their
UTORid or name in the form (e.g. "Rami"/"Hussayn" submitted instead of
"Rami Hussayn"/"hussaynr") - nothing flags that automatically. For every
roster student not otherwise excluded, this script also checks for a
close UTORid match (fuzzy string similarity) AND a shared name word against
every already-assigned student. A hit is NOT auto-excluded (too easy to
false-positive on two different students with similar UTORids) - instead
it's held out of random assignment and written to
possible_duplicate_identities.csv for a human to confirm or dismiss.

Output (gitignored, not written over the original):
  - data_files/final/assignment_readable_full.csv
    Same columns as assignment_readable.csv, plus a "source" column:
    "preference" for the original 127 (or however many), "no_signup" for
    students randomly assigned here because they never filled out the form.
  - data_files/final/possible_duplicate_identities.csv
    Only written if something needs a manual look - roster students who
    look like they MIGHT already have an assignment under a typo'd/partial
    identity. Held out of random assignment until you resolve them (see
    "What to do next" printed at the end of a run that finds any).
"""
import difflib
import os
import sys

import numpy as np
import pandas as pd

from paths import ensure_dir

# ==================== CONFIG ====================
CLASS_LIST_CSV = "data_files/raw/class_list.csv"
ASSIGNMENT_READABLE_CSV = "data_files/final/assignment_readable.csv"
TOPICS_LOOKUP_CSV = "data_files/processed/topics_lookup.csv"
FLAGGED_UTORIDS_CSV = "data_files/processed/flagged_utorids.csv"  # students who submitted using a student number instead of UTORid
OUT_CSV = "data_files/final/assignment_readable_full.csv"
OUT_POSSIBLE_DUPES_CSV = "data_files/final/possible_duplicate_identities.csv"

SEED = 2026  # separate from assigner.py's SEED=2025 - this is a distinct random draw
PENALTY_UNLISTED = 1000  # mirrors assigner.py's PENALTY_UNLISTED - these students listed nothing
UTORID_SIMILARITY_THRESHOLD = 0.80  # difflib ratio; catches e.g. "hussayn" vs "hussaynr"
# =================================================


def main():
    roster = pd.read_csv(CLASS_LIST_CSV, dtype=str)
    roster.columns = [c.strip() for c in roster.columns]
    roster = roster[roster["Role"].astype(str).str.strip().str.lower() == "student"]
    roster["UTORid"] = roster["UTORid"].astype(str).str.strip()
    roster["Name"] = roster["Name"].astype(str).str.strip()
    roster = roster[roster["UTORid"] != ""]

    dupes = roster.loc[roster["UTORid"].duplicated(keep=False), "UTORid"].unique().tolist()
    if dupes:
        print(f"WARNING: duplicate UTORid(s) in class list, keeping first occurrence: {dupes}")
        roster = roster.drop_duplicates(subset=["UTORid"], keep="first")

    assigned = pd.read_csv(ASSIGNMENT_READABLE_CSV, dtype=str)
    assigned["utorid"] = assigned["utorid"].astype(str).str.strip()
    assigned_utorids = set(assigned["utorid"])

    try:
        flagged = pd.read_csv(FLAGGED_UTORIDS_CSV, dtype=str)
        flagged_names = [
            (str(n).strip(), str(u).strip())
            for n, u in zip(flagged["name"], flagged["utorid_field"])
            if str(n).strip()
        ]
    except FileNotFoundError:
        flagged_names = []

    def flagged_name_match(name_words):
        """Returns ('exact', utorid) | ('partial', name, utorid) | None.

        A numeric-UTORid submission's name field is sometimes truncated
        (e.g. "Hamza" instead of "Hamza Chand") - an exact string match
        against the roster's full name would miss it, so this also checks
        word-subset overlap. An EXACT full-name match is trusted and
        auto-excludes; a partial/subset-only match is NOT auto-excluded -
        it's routed to possible_duplicate_identities.csv like the fuzzy
        check below, since a common first name (e.g. two different
        "John"s) could otherwise coincidentally match.
        """
        for fname, futorid in flagged_names:
            fwords = set(fname.lower().split())
            if not fwords:
                continue
            if name_words == fwords:
                return ("exact", fname, futorid)
            if name_words <= fwords or fwords <= name_words:
                return ("partial", fname, futorid)
        return None

    roster["_name_words"] = roster["Name"].str.strip().str.lower().str.split().apply(set)
    assigned_utorids_lower = {u.lower() for u in assigned_utorids}
    not_missing_by_utorid = roster["UTORid"].isin(assigned_utorids)
    not_missing_by_utorid_ci = roster["UTORid"].str.lower().isin(assigned_utorids_lower)  # case-only difference

    flagged_matches = roster["_name_words"].apply(flagged_name_match)
    not_missing_by_flagged_name = flagged_matches.apply(lambda m: m is not None and m[0] == "exact")
    partial_flagged_name = flagged_matches.apply(lambda m: m is not None and m[0] == "partial")

    rescued = roster[~not_missing_by_utorid & not_missing_by_flagged_name]
    if len(rescued):
        print(f"NOTE: {len(rescued)} student(s) already submitted under a student-number UTORid "
              f"(see {FLAGGED_UTORIDS_CSV}) - excluded from no-show assignment: "
              f"{rescued['Name'].tolist()}")

    case_only = roster[~not_missing_by_utorid & not_missing_by_utorid_ci]
    if len(case_only):
        print(f"NOTE: {len(case_only)} student(s) matched an existing assignment except for UTORid "
              f"letter case - excluded from no-show assignment: {case_only['Name'].tolist()}")

    # partial (not exact) matches against a flagged numeric-UTORid submission - held for review below
    possible_dupes = []
    for idx, row in roster[~not_missing_by_utorid & ~not_missing_by_utorid_ci & partial_flagged_name].iterrows():
        m = flagged_matches[idx]
        possible_dupes.append({
            "roster_name": row["Name"],
            "roster_utorid": row["UTORid"],
            "closest_assigned_name": m[1],
            "closest_assigned_utorid": m[2],
            "closest_assigned_topic_id": "",
        })

    candidates = roster[
        ~not_missing_by_utorid & ~not_missing_by_flagged_name
        & ~not_missing_by_utorid_ci & ~partial_flagged_name
    ].drop(columns=["_name_words"]).copy()

    # --- broader check: fuzzy UTORid match + shared name word against every already-assigned student ---
    assigned_rows = list(assigned.itertuples(index=False))
    still_missing_idx = []
    for idx, row in candidates.iterrows():
        roster_utorid_lower = row["UTORid"].lower()
        roster_name_words = set(row["Name"].lower().split())
        hit = None
        for arow in assigned_rows:
            a_utorid = str(arow.utorid).strip().lower()
            a_name_words = set(str(arow.name).strip().lower().split())
            if not a_utorid or not a_name_words:
                continue
            utorid_ratio = difflib.SequenceMatcher(None, roster_utorid_lower, a_utorid).ratio()
            shares_name_word = bool(roster_name_words & a_name_words)
            if utorid_ratio >= UTORID_SIMILARITY_THRESHOLD and shares_name_word:
                hit = arow
                break
        if hit is not None:
            possible_dupes.append({
                "roster_name": row["Name"],
                "roster_utorid": row["UTORid"],
                "closest_assigned_name": hit.name,
                "closest_assigned_utorid": hit.utorid,
                "closest_assigned_topic_id": hit.topic_id,
            })
        else:
            still_missing_idx.append(idx)

    missing = candidates.loc[still_missing_idx].copy()

    if possible_dupes:
        ensure_dir(OUT_POSSIBLE_DUPES_CSV)
        pd.DataFrame(possible_dupes).to_csv(OUT_POSSIBLE_DUPES_CSV, index=False)
        print(f"\nWARNING: {len(possible_dupes)} roster student(s) look like they might already have an "
              f"assignment under a typo'd/partial identity - see {OUT_POSSIBLE_DUPES_CSV}")
        print("Held OUT of random assignment until you confirm. If confirmed as the same person, nothing")
        print("further to do (their existing assignment stands). If NOT the same person, remove that row")
        print(f"from {OUT_POSSIBLE_DUPES_CSV} and re-run this script so they get a random topic.\n")
    elif os.path.exists(OUT_POSSIBLE_DUPES_CSV):
        os.remove(OUT_POSSIBLE_DUPES_CSV)  # stale from a previous run - nothing to flag this time

    print(f"Class roster: {len(roster)} student(s)")
    print(f"Already assigned (from {ASSIGNMENT_READABLE_CSV}): {len(assigned)} student(s)")
    print(f"Missing (no submission, need random assignment): {len(missing)} student(s)")

    if missing.empty:
        print("Nobody missing - copying assignment_readable.csv to assignment_readable_full.csv unchanged.")
        out = assigned.copy()
        out["source"] = "preference"
        ensure_dir(OUT_CSV)
        out.to_csv(OUT_CSV, index=False)
        print(f"Wrote {len(out)} rows to {OUT_CSV}")
        return

    topics_lookup = pd.read_csv(TOPICS_LOOKUP_CSV, dtype=str)
    all_topic_ids = set(topics_lookup["topic_id"])
    used_topic_ids = set(assigned["topic_id"])
    remaining_topic_ids = sorted(all_topic_ids - used_topic_ids)

    print(f"Remaining unused topics: {len(remaining_topic_ids)}")

    if len(remaining_topic_ids) < len(missing):
        print(f"\nERROR: only {len(remaining_topic_ids)} topic(s) remain, but {len(missing)} student(s) need one.")
        print("Can't randomly assign - add more topics or resolve manually.")
        sys.exit(1)

    rng = np.random.default_rng(SEED)
    chosen = rng.choice(remaining_topic_ids, size=len(missing), replace=False)

    topic_name_map = dict(zip(topics_lookup["topic_id"], topics_lookup["topic_name"]))

    new_rows = pd.DataFrame({
        "name": missing["Name"].values,
        "utorid": missing["UTORid"].values,
        "topic_id": chosen,
        "topic_name": [topic_name_map[t] for t in chosen],
        "rank_assigned": [None] * len(missing),
        "cost": [PENALTY_UNLISTED] * len(missing),
        "won_lottery": [False] * len(missing),
        "assigned_unranked": [True] * len(missing),
        "source": ["no_signup"] * len(missing),
    })

    original = assigned.copy()
    original["source"] = "preference"

    combined = pd.concat([original, new_rows], ignore_index=True).sort_values("name")

    ensure_dir(OUT_CSV)
    combined.to_csv(OUT_CSV, index=False)
    print(f"\nRandomly assigned {len(missing)} student(s) a remaining topic (SEED={SEED}, reproducible).")
    print(f"Wrote {len(combined)} total rows to {OUT_CSV}")
    print("\nNewly assigned:")
    print(new_rows[["name", "utorid", "topic_id", "topic_name"]].to_string(index=False))


if __name__ == "__main__":
    main()
