"""Compatibility helpers for the different Python versions."""

import sys

PY35 = sys.version_info >= (3, 5)
PY37 = sys.version_info >= (3, 7)
platform = sys.platform
