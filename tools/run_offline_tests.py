#!/usr/bin/env python3
"""Run tests/test_*.py with the standard library. No pytest, no network."""

from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"


def main() -> int:
    failed = []
    ran = 0
    for path in sorted(TESTS.glob("test_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            failed.append(f"{path.name}: could not load")
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            fn = getattr(module, name)
            if not callable(fn):
                continue
            ran += 1
            try:
                fn()
            except Exception:
                failed.append(f"{path.name}::{name}\n{traceback.format_exc()}")
    if failed:
        print(f"FAIL offline tests: {len(failed)} failed of {ran}")
        for item in failed:
            print(item)
        return 1
    print(f"PASS offline tests: {ran} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
