# Students Projects Assigner

This project automates the assignment of students to project topics based on their ranked preferences. It uses a lottery and optimization algorithm to ensure fair and efficient assignments, even when there are more topics than students or overlapping preferences.

## Features
- Handles incomplete, duplicated, and empty preferences
- Supports more topics than students
- Uses a lottery for first-choice conflicts
- Assigns unranked topics if necessary
- Outputs assignment and summary CSV files

## Quick Start (for a new TA)

Run in order, from inside `students-projects-assigner/`:

```
process-data                    # raw xlsx -> processed CSVs, then stops for you to review
finalize-assignment              # processed CSVs -> final assignment
verify-assignment                # sanity-checks the final output against the raw files
assign-unregistered-students     # optional: random topic for students who never submitted
export-assignment                # copies the final output out of the repo, e.g. to share
```

Between `process-data` and `finalize-assignment`, **stop and look** at `data_files/processed/` - that's the point of splitting it into two steps. See "The Workflow" below for what to check at each stage.

## One-Time Setup

### 1. Create a virtual environment
```
python -m venv .venv
```
Activate it:
- macOS/Linux: `source .venv/bin/activate`
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (Git Bash): `source .venv/Scripts/activate`

### 2. Install dependencies
Dependencies are declared in `pyproject.toml` (numpy, pandas, scipy, openpyxl):
```
pip install .
```
This also installs the `process-data`, `finalize-assignment`, `verify-assignment`, `assign-unregistered-students`, and `export-assignment` commands into your virtual environment. If you'd rather not install anything, every command also runs directly, e.g. `python scripts/process_data.py`.

### 3. Point the scripts at this year's files
A few paths are hardcoded per-TA (not read from a config file), because they point at files that live outside this repo. **Before your first run, update these:**

| Setting | File | What to set it to |
|---|---|---|
| `TOPICS_XLSX` | `src/convert_topics.py` | Path to the topics master workbook (the one with the `Sign-up-sheet` tab) |
| `TOPICS_XLSX` | `src/convert_prefs.py` | Same path as above |
| `EXPORT_DIR` | `src/export_assignment.py` | Folder you want the final results copied to (defaults to a sibling `Assigned-Topics` folder) |

If your Forms export uses different column names than `"1st Choice"`, `"Your UTORid:"`, etc., also check the `CONFIG` section at the top of `src/convert_prefs.py` - it expects the raw Forms export's exact column headers.

### 4. Place this year's raw data
Put the raw Microsoft Forms export (downloaded as `.xlsx`) at:
```
data_files/raw/prefs.xlsx
```
If you'll be running `assign-unregistered-students` (Stage 4, for students who never submitted the form), also export the official class roster and put it at:
```
data_files/raw/class_list.csv
```
with columns `Name, UTORid, Course, Role` (extra columns are ignored; only rows where `Role` is `Student` are used).

Nothing under `data_files/` is ever committed to git - see Protecting Student Privacy below.

## The Workflow

### Stage 1 - `process-data`
Converts the raw workbook(s) into `data_files/processed/` and **stops** - it does not run the assignment. Review before continuing:
- `prefs.csv` - one row per student, ready for assignment
- `topics.csv` / `topics_lookup.csv` - the topic master list
- `unmatched_choices_remaining.csv` - **only appears if something needs a manual fix** (a choice that couldn't be matched to any topic by number or name)
- `flagged_utorids.csv` - students who typed a student number instead of a UTORid (informational, safe to leave as-is)
- `suggestions_review.csv` - free-text "suggest a topic" write-ins. Reviewing these and manually hand-assigning a custom topic to a student is **always a manual step done by the TA** - no script touches this file or acts on it automatically. Some TAs keep a personal working copy (e.g. `suggestions_review_annotated.csv`) to track their decisions; that file is yours, edit it however you like.
- `duplicate_submissions.csv` - if a student submitted the form more than once, only their latest submission (by completion time) is kept automatically; this file shows you what was dropped, in case you want to double check.
- `topic_overrides_applied.csv` - **only appears if you provided `data_files/raw/topic_overrides.csv`** - audit trail of approved custom topics applied (see below).

#### Approving a custom suggested topic
The Forms says: *"if we like your suggested topic, we'll assign it as your first choice."* To honor that for specific students (after reviewing `suggestions_review.csv`), create `data_files/raw/topic_overrides.csv`:
```
utorid,custom_topic_name
someutorid,Some New Topic Name
```
- `utorid` must match exactly what's in `prefs.csv`'s `student` column (for a student who submitted with a student number instead of a UTORid, use that number here).
- This file is entirely optional - if it doesn't exist, this step is skipped and nothing changes.
- Each row gets a new sequential `TopicNNN` id, is added to `topics.csv`/`topics_lookup.csv`, and becomes that student's rank1 (their real choices shift down a slot, dropping the old rank5 - inconsequential, since an uncontested new topic means the lottery locks them in immediately and their lower ranks are never consulted). Their **original** rank1 genuinely reopens and flows back through the real lottery/optimizer in `finalize-assignment` - not a manual patch, so whoever lost that original lottery gets a fair shot at it.
- Applying this changes `prefs.csv`, so re-run `finalize-assignment` (and `verify-assignment`) afterward.

### Stage 2 - `finalize-assignment`
Runs the assignment algorithm (`src/assigner.py`, unmodified core logic) and writes to `data_files/final/`:
- `assignment.csv` - raw algorithm output (student, topic_id, cost, rank_assigned, won_lottery, assigned_unranked)
- `assignment_summary.csv` - aggregate stats (how many got their 1st/2nd/3rd choice, etc.)
- `assignment_readable.csv` - the same assignment with real names and topic names joined in, ready to paste into the topics sign-up sheet

To tune the algorithm itself (rank-to-cost weights, random seed, penalty for unranked topics), edit the `CONFIG` section at the top of `src/assigner.py`.

### Stage 3 - `verify-assignment`
Independently re-checks the final output against the two raw source files (not against the pipeline's own intermediate files), and reports any discrepancy:
- a student missing from, duplicated in, or unexpectedly added to the final output
- a student's name not matching their raw Forms submission
- a topic id/name not matching the master workbook (flagged for a look - a legitimately hand-assigned custom topic will also trip this, that's expected)
- a topic assigned to more than one student

Prints `PASS` if everything checks out, otherwise lists exactly what to look at.

### Stage 4 (optional) - `assign-unregistered-students`
For students on the official roster (`data_files/raw/class_list.csv`) who never submitted the Forms preferences at all. Compares the roster against `assignment_readable.csv` and randomly assigns each genuine no-show one of the still-unused topics (separate `SEED=2026`, reproducible). Writes `data_files/final/assignment_readable_full.csv` - your original `assignment_readable.csv` is left untouched.

Matching "who's missing" isn't just an exact UTORid check - a real student can submit under a student number instead of a UTORid, with an exact-case difference, or with a truncated/typo'd name or UTORid. This is handled in layers of decreasing confidence:
1. Exact UTORid match, or case-only difference -> definitely already submitted, excluded automatically.
2. Their name exactly matches a known student-number submission (`flagged_utorids.csv`) -> excluded automatically.
3. Their name is a partial/truncated match against a known student-number submission, or their UTORid is a close-but-not-exact fuzzy match against an existing assignment's UTORid *and* they share a name word -> **not** auto-resolved (two different students can coincidentally share a first name) - held out and written to `data_files/final/possible_duplicate_identities.csv` for you to confirm by eye. If confirmed as the same person, nothing more to do. If not, delete that row and re-run so they get a random topic.

### Stage 5 - `export-assignment`
Copies everything in `data_files/final/` (including `assignment_readable_full.csv` and `possible_duplicate_identities.csv`, once Stage 4 has run) to the folder set in `EXPORT_DIR` (`src/export_assignment.py`), so the results are somewhere easy to find without digging into the repo. **Never silently overwrites** - a new/changed file is copied normally, an unchanged file is left alone, and a file that already exists in `EXPORT_DIR` but differs gets written alongside it with a timestamp suffix instead of replacing it, so you decide what to keep.

## Project Layout
- `src/` - all core logic (converters, the assignment algorithm, the stage orchestrators). This is what gets installed as the package.
- `scripts/` - thin CLI launcher stubs, for running any stage without installing the package (`python scripts/process_data.py`, etc.).
- `data_files/raw|processed|final/` - all real data for the current run. Entirely gitignored, regardless of any other exception rule in `.gitignore`.
- `prefs_sample.csv` - example input format, safe to commit (no real student data).

## Protecting Student Privacy
- Everything under `data_files/` (raw exports, processed CSVs, and final assignment output) is excluded from version control by `.gitignore`.
- The `export-assignment` folder (outside the repo) is **not** covered by this repo's `.gitignore` - make sure wherever you point `EXPORT_DIR` isn't itself a git repo, or set up its own ignore rules.
- Delete or encrypt files containing sensitive information when no longer needed.

## Troubleshooting
- **"Permission denied" writing a CSV**: the file is open elsewhere (commonly Excel) - close it and re-run the command.
- **`ModuleNotFoundError`**: make sure your virtual environment is activated and you've run `pip install .`.
- **`unmatched_choices_remaining.csv` appears after `process-data`**: a student's ranked choice couldn't be matched to a topic by number or by name. Open the file, figure out the intended topic, and either fix the raw Forms export and re-run, or manually edit `data_files/processed/prefs.csv`.
- For anything else, contact the project maintainer or your course instructor.

---

**This tool is for educational use. Protect student privacy at all times.**

---

*Portions of this project and documentation were assisted by ChatGPT and Claude.*
