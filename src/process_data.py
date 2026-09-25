"""
STAGE 1 of 2: raw -> processed.

Run this after placing this year's raw Microsoft Forms export at
data_files/raw/prefs.xlsx (and pointing TOPICS_XLSX in convert_prefs.py /
convert_topics.py at the topics master workbook). Converts both to the
processed CSVs assigner.py needs, resolves what it can automatically, and
STOPS - it does not run the assignment algorithm. Review data_files/processed/
before running `finalize-assignment`.

Usage (after `pip install .`):
    process-data

or directly (no install needed):
    python scripts/process_data.py
"""
import sys

import convert_topics
import convert_prefs
import resolve_unmatched_choices
import find_duplicate_submissions


def main():
    try:
        print("\n==== [1/4] Converting topics master list ====")
        convert_topics.main()

        print("\n==== [2/4] Converting raw preferences export ====")
        convert_prefs.main()

        print("\n==== [3/4] Resolving choices matched by name instead of number ====")
        resolve_unmatched_choices.main()

        print("\n==== [4/4] Checking for duplicate/resubmitted responses ====")
        find_duplicate_submissions.main()
    except PermissionError as e:
        print(f"\nERROR: could not write {e.filename!r} - it's likely open in Excel or another program.")
        print("Close it and re-run `process-data`.")
        sys.exit(1)

    print("\n==== STAGE 1 COMPLETE - review before continuing ====")
    print("Check data_files/processed/ :")
    print("  prefs.csv                          student preferences, ready for assignment")
    print("  topics.csv / topics_lookup.csv     topic master list")
    print("  unmatched_choices_remaining.csv    only if present - unresolved choices, needs a manual fix")
    print("  flagged_utorids.csv                numeric-looking UTORid entries, informational only")
    print("  suggestions_review.csv             write-in topic suggestions, handled manually (never by script)")
    print("  duplicate_submissions.csv          resubmitted responses, already resolved (latest kept)")
    print("\nWhen prefs.csv and topics.csv look right, run `finalize-assignment`.")


if __name__ == "__main__":
    main()
