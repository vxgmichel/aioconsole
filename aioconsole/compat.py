"""Compatibility helpers for the different Python versions."""

import sys

PY36 = (3, 6) <= sys.version_info < (3, 7)
platform = sys.platform
