"""
CLI wrapper for STAGE 4 (export final results out of the repo). Lets you
run it directly without installing the package, e.g. from a fresh clone:

    python scripts/export_assignment.py

The real implementation lives in src/export_assignment.py; after
`pip install .` the equivalent command is just `export-assignment`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from export_assignment import main

if __name__ == "__main__":
    main()
