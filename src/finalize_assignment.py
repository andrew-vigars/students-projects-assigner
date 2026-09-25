"""
STAGE 2 of 2: processed -> final.

Run this after `process-data` and after you've reviewed data_files/processed/
(prefs.csv, topics.csv) and are satisfied they're correct. Runs the
assignment algorithm (assigner.py, unmodified) and builds a human-readable
version of the result.

Usage (after `pip install .`):
    finalize-assignment

or directly (no install needed):
    python scripts/finalize_assignment.py
"""
import sys

import assigner
import annotate_assignment


def main():
    try:
        print("\n==== [1/2] Running assignment algorithm ====")
        assigner.main()

        print("\n==== [2/2] Building human-readable assignment ====")
        annotate_assignment.main()
    except PermissionError as e:
        print(f"\nERROR: could not write {e.filename!r} - it's likely open in Excel or another program.")
        print("Close it and re-run `finalize-assignment`.")
        sys.exit(1)

    print("\n==== STAGE 2 COMPLETE ====")
    print("See data_files/final/ :")
    print("  assignment.csv            raw algorithm output")
    print("  assignment_summary.csv    aggregate stats")
    print("  assignment_readable.csv   name + topic name, ready to paste into the Final sheet")


if __name__ == "__main__":
    main()
