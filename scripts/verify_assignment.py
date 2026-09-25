"""
CLI wrapper for STAGE 3 (final reconciliation check). Lets you run it
directly without installing the package, e.g. from a fresh clone:

    python scripts/verify_assignment.py

The real implementation lives in src/verify_assignment.py; after
`pip install .` the equivalent command is just `verify-assignment`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from verify_assignment import main

if __name__ == "__main__":
    main()
