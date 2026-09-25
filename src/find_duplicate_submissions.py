# pip install pandas openpyxl
"""
Pulls the full raw rows (with timestamps) for any UTORid that submitted the
form more than once, so you can compare their choices and decide which
submission to keep (e.g. latest timestamp = corrected mistake).

Does NOT modify prefs.xlsx, prefs.csv, or any other converter output.
Run this, review duplicate_submissions.csv, then manually remove the
rows you don't want to keep from prefs.csv (or re-run convert_prefs.py +
resolve_unmatched_choices.py after fixing prefs.xlsx).
"""
import pandas as pd

from paths import ensure_dir

PREFS_XLSX = "data_files/raw/prefs.xlsx"
COL_UTORID = "Your UTORid:"
OUT_CSV = "data_files/processed/duplicate_submissions.csv"


def main():
    raw = pd.read_excel(PREFS_XLSX, sheet_name=0)
    raw.columns = [str(c).replace("\xa0", " ").strip() if isinstance(c, str) else c for c in raw.columns]
    raw[COL_UTORID] = raw[COL_UTORID].astype(str).str.strip()

    dupe_utorids = raw.loc[raw[COL_UTORID].duplicated(keep=False), COL_UTORID].unique().tolist()
    if not dupe_utorids:
        print("No duplicate UTORids found.")
        return

    dupes = raw[raw[COL_UTORID].isin(dupe_utorids)].copy()
    dupes = dupes.sort_values([COL_UTORID, "Completion time"])
    ensure_dir(OUT_CSV)
    dupes.to_csv(OUT_CSV, index=False)

    print(f"Found {len(dupe_utorids)} UTORid(s) with multiple submissions: {dupe_utorids}")
    print(f"Wrote {len(dupes)} rows to {OUT_CSV}, sorted by UTORid then Completion time (latest last).")


if __name__ == "__main__":
    main()
