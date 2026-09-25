"""
STAGE 4 (optional): export the final results out of the repo.

Copies everything in data_files/final/ (assignment.csv,
assignment_summary.csv, assignment_readable.csv) into a plain
"Assigned-Topics" folder one level up from the repo, alongside the topics
sign-up workbook - so the results are somewhere easy to find/share without
digging into the repo's data_files/ layout.

Does NOT touch data_files/final/ itself (copies out, doesn't move) and does
NOT touch the topics workbook or its "Final" sheet - pasting into that
sheet is still a manual step.
"""
import os
import shutil

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

    for f in files:
        shutil.copy2(os.path.join(FINAL_DIR, f), os.path.join(EXPORT_DIR, f))
        print(f"Copied {f} -> {EXPORT_DIR}")

    print(f"\nExported {len(files)} file(s) to {EXPORT_DIR}")


if __name__ == "__main__":
    main()
