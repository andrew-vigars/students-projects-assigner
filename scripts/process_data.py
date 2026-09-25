"""
CLI wrapper for STAGE 1 of 2 (raw -> processed). Lets you run it directly
without installing the package, e.g. from a fresh clone:

    python scripts/process_data.py

The real implementation lives in src/process_data.py; after `pip install .`
the equivalent command is just `process-data`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from process_data import main

if __name__ == "__main__":
    main()
