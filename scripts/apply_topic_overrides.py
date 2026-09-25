"""
CLI wrapper for applying custom topic overrides. Lets you run it directly
without installing the package:

    python scripts/apply_topic_overrides.py

The real implementation lives in src/apply_topic_overrides.py; after
`pip install .` the equivalent command is just `apply-topic-overrides`.
Also runs automatically as the last step of `process-data`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apply_topic_overrides import main

if __name__ == "__main__":
    main()
