"""
STAGE 5: export the final results out of the repo.

Copies everything in data_files/final/ (assignment.csv,
assignment_summary.csv, assignment_readable.csv, and
assignment_readable_full.csv once assign-unregistered-students has been
run) into a plain "Assigned-Topics" folder one level up from the repo,
alongside the topics sign-up workbook - so the results are somewhere easy
to find/share without digging into the repo's data_files/ layout.

Does NOT touch data_files/final/ itself (copies out, doesn't move) and does
NOT touch the topics workbook or its "Final" sheet - pasting into that
sheet is still a manual step.

Never silently overwrites a file already in EXPORT_DIR:
  - if the destination file doesn't exist yet, or is byte-identical to the
    source, it's copied/left as-is
  - if the destination file exists and DIFFERS, the new version is written
    alongside it with a timestamp suffix instead (e.g.
    assignment.csv -> assignment__20260925-143012.csv), and the existing
    file is left untouched - you decide which one to keep.
"""
import filecmp
import os
import shutil
from datetime import datetime

# ==================== CONFIG ====================
FINAL_DIR = "data_files/final"
EXPORT_DIR = r"C:\Users\aviga\OneDrive - University of Toronto\CIV 220 - 2026 TA\Mini-Project\Assigned-Topics"
# =================================================


def main():
    if not os.path.isdir(FINAL_DIR):
        raise FileNotFoundError(f"{FINAL_DIR} not found - run `finalize-assignment` first.")

    files = [f for f in os.listdir(FINAL_DIR) if os.path.isfile(os.path.join(FINAL_DIR, f))]
    if not files:
        raise FileNotFoundError(f"{FINAL_DIR} is empty - run `finalize-assignment` first.")

    os.makedirs(EXPORT_DIR, exist_ok=True)

    copied, unchanged, renamed = 0, 0, 0

    for f in files:
        src = os.path.join(FINAL_DIR, f)
        dst = os.path.join(EXPORT_DIR, f)

        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            print(f"Copied {f} -> {EXPORT_DIR}")
            copied += 1
            continue

        if filecmp.cmp(src, dst, shallow=False):
            print(f"Unchanged, left as-is: {f}")
            unchanged += 1
            continue

        stem, ext = os.path.splitext(f)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        new_name = f"{stem}__{timestamp}{ext}"
        shutil.copy2(src, os.path.join(EXPORT_DIR, new_name))
        print(f"WARNING: {f} already exists in {EXPORT_DIR} and differs - "
              f"wrote new version as {new_name} instead of overwriting.")
        renamed += 1

    print(f"\n{copied} new, {unchanged} unchanged, {renamed} written alongside an existing (differing) file, in {EXPORT_DIR}")


if __name__ == "__main__":
    main()
