#!/usr/bin/env python3
"""Compatibility wrapper for dataset validation."""
import sys
from main import main


if __name__ == "__main__":
    main(["validate", *sys.argv[1:]])
