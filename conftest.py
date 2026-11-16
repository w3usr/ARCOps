"""pytest configuration: Django settings come from pyproject.toml."""

import pytest


@pytest.fixture(autouse=True)
def _fresh_cache():
    """allauth keeps its rate-limit counters in the per-process cache; xdist would carry them over."""
    from django.core.cache import cache

    cache.clear()
