"""
CLI wrapper for STAGE 2 of 2 (processed -> final). Lets you run it directly
without installing the package, e.g. from a fresh clone:

    python scripts/finalize_assignment.py

The real implementation lives in src/finalize_assignment.py; after
`pip install .` the equivalent command is just `finalize-assignment`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from finalize_assignment import main

if __name__ == "__main__":
    main()
