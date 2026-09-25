"""
CLI wrapper for STAGE 4 (assign remaining topics to no-show students). Lets
you run it directly without installing the package:

    python scripts/assign_unregistered_students.py

The real implementation lives in src/assign_unregistered_students.py; after
`pip install .` the equivalent command is just `assign-unregistered-students`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from assign_unregistered_students import main

if __name__ == "__main__":
    main()
