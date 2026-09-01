"""Shared test fixtures for tdad-fullstack tests.

Combines:
- Upstream sample_repo fixtures (Python — from tdad 0.1.0)
- New fullstack fixtures (multi-language — added in this fork)
"""
from pathlib import Path

import pytest


@pytest.fixture
def sample_repo():
    """Path to the upstream Python sample repository fixture."""
    return Path(__file__).parent / "fixtures" / "sample_repo"


@pytest.fixture
def sample_calculator(sample_repo):
    return sample_repo / "src" / "calculator.py"


@pytest.fixture
def sample_utils(sample_repo):
    return sample_repo / "src" / "utils.py"


@pytest.fixture
def sample_test_calculator(sample_repo):
    return sample_repo / "tests" / "test_calculator.py"


@pytest.fixture
def fullstack_repo():
    """Path to the multi-language fixture (tdad-fullstack fork)."""
    return Path(__file__).parent / "fixtures" / "fullstack"


# Pytest by default collects any .py file under tests/ whose name matches
# test_*.py or *_test.py. Our fixtures live under tests/fixtures/ and
# contain files that match those patterns but are NOT real tests —
# they're example source files used by the parser tests. Block collection.
collect_ignore_glob = [
    "fixtures/fullstack/**",
]
