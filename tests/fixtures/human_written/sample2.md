# Using pytest for Python testing

pytest is a testing framework for Python. It works with any Python
project and has a simple syntax.

## Installation

```bash
pip install pytest
```

## Writing tests

Create a file named `test_*.py`:

```python
def test_addition():
    assert 1 + 1 == 2
```

Run tests:

```bash
pytest
```

## Fixtures

Use fixtures to set up test data:

```python
import pytest

@pytest.fixture
def sample_data():
    return [1, 2, 3]

def test_sum(sample_data):
    assert sum(sample_data) == 6
```

## Markers

Skip tests or mark them as expected to fail:

```python
@pytest.mark.skip(reason="not implemented")
def test_future_feature():
    pass

@pytest.mark.xfail
def test_known_bug():
    assert False
```

See the [pytest documentation](https://docs.pytest.org/) for more.
