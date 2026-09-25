"""Shared helper for the data_files/{raw,processed,final} layout.

data_files/ is entirely gitignored, so on a fresh clone none of its
subfolders exist yet - every script that writes into it must create its
own output directory first rather than assuming it's there.
"""
import os


def ensure_dir(path):
    """Create the parent directory of `path` if it doesn't already exist."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
