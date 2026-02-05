"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def ai_samples_dir(fixtures_dir: Path) -> Path:
    """Return path to samples with bad writing practices."""
    return fixtures_dir / "ai_generated"


@pytest.fixture
def human_samples_dir(fixtures_dir: Path) -> Path:
    """Return path to human-written samples."""
    return fixtures_dir / "human_written"


@pytest.fixture
def sample_markdown() -> str:
    """Return sample Markdown with bad writing patterns."""
    return """\
# A Comprehensive Guide

This guide delves into the intricacies of the topic.

## Key Features

- **Feature One:** This is a crucial component
- **Feature Two:** Showcasing the robust architecture
- **Feature Three:** Leveraging cutting-edge technology

The landscape of modern development is multifaceted.
Not only does it require technical skills, but also creativity.

I hope this helps! Let me know if you need more information.
"""


@pytest.fixture
def sample_python() -> str:
    """Return sample Python with bad writing patterns."""
    return '''\
"""A comprehensive module for data processing.

This module delves into the intricacies of data handling,
showcasing robust patterns for modern development.
"""


def process_data(data: list) -> list:
    """Process the data in a comprehensive manner.

    This function leverages cutting-edge algorithms to
    enhance the data processing pipeline.

    Args:
        data: The input data to process.

    Returns:
        The processed data.
    """
    # I hope this helps with your data processing needs
    return [item * 2 for item in data]  # Crucial transformation
'''
