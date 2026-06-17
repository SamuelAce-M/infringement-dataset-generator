#!/usr/bin/env python3
"""Compatibility wrapper for manifest preparation."""
import sys
from main import main


if __name__ == "__main__":
    main(["prepare-manifests", *sys.argv[1:]])
