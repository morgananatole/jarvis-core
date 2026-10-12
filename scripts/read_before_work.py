#!/usr/bin/env python3
"""Read the current canonical base before project work. No model or network call."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from knowledge_center import read_bundle

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    print(json.dumps(read_bundle(contents=args.full), ensure_ascii=False, indent=2))
