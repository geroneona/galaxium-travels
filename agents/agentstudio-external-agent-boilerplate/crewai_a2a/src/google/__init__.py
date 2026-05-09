"""Minimal stub package for the ``google`` namespace to satisfy mypy.

This file intentionally provides a namespace package placeholder so mypy
doesn't raise an AssertionError when resolving ``google`` imports from
installed libraries that use namespace packages (e.g. google.*).
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
