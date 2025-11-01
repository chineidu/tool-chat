# Testing Guide

This document provides information about the testing setup and how to run tests for the Tool Chat application.

## Overview

The project uses **pytest** for testing with a focus on database CRUD operations. Tests are isolated using SQLite in-memory databases to ensure no interference with production data.

## Test Structure

```text
tests/
├── conftest.py          # Test configuration and fixtures
└── test_crud.py         # CRUD operation tests
```

### Test Categories

- **CRUD Tests**: Comprehensive tests for database operations (users, feedback, roles)
- **Database Isolation**: Each test uses a clean SQLite in-memory database
- **Transaction Rollback**: Changes are rolled back after each test

## Prerequisites

- Python 3.13+
- uv package manager
- Dependencies installed via `uv sync`

## Running Tests

### Using Make (Recommended)

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose
```

### Using uv Directly

```bash
# Run all tests
uv run -m pytest

# Run specific test file
uv run -m pytest tests/test_crud.py

# Run specific test class
uv run -m pytest tests/test_crud.py::TestUserCRUD

# Run specific test method
uv run -m pytest tests/test_crud.py::TestUserCRUD::test_create_user_success
```

### Using Python Directly

```bash
# Run all tests
python -m pytest

# Run with different output formats
python -m pytest --tb=short  # Shorter traceback
python -m pytest --tb=line   # One line per failure
```

## Test Fixtures

### Database Fixtures (`conftest.py`)

- **`engine`**: Creates SQLite in-memory database engine
- **`tables`**: Creates all database tables
- **`initialized_db`**: Initializes database with default roles (ADMIN, USER, GUEST)
- **`db_session`**: Provides database session with transaction rollback

### Fixture Dependencies

```text
engine → tables → initialized_db → db_session
```

Each test gets a clean database session that rolls back all changes after the test completes.

## Test Configuration

### pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- Tests are located in the `tests/` directory
- Source code is available via `src/` in Python path

## Adding New Tests

### 1. Create Test File

```bash
touch tests/test_new_feature.py
```

### 2. Basic Test Structure

```python
import pytest
from sqlalchemy.orm.session import Session

class TestNewFeature:
    """Test new feature functionality."""

    def test_feature_success(self, db_session: Session) -> None:
        """Test successful feature operation."""
        # Arrange
        # Act
        # Assert
        pass

    def test_feature_failure(self, db_session: Session) -> None:
        """Test feature failure cases."""
        # Arrange
        # Act
        # Assert
        pass
```

### 3. Use Database Session

```python
def test_my_operation(self, db_session: Session) -> None:
    """Test database operation."""
    # db_session is automatically injected by pytest
    # All changes are rolled back after the test
    result = my_crud_function(db_session, data)
    assert result is not None
```

## Test Coverage

To check test coverage:

```bash
# Generate HTML coverage report
uv run pytest --cov=src --cov-report=html

# View coverage in browser
open htmlcov/index.html
```

## Debugging Tests

### Verbose Output

```bash
# Show detailed test execution
uv run pytest -v -s

# Show print statements in tests
uv run pytest -s
```

### Failed Tests Only

```bash
# Run only failed tests from previous run
uv run pytest --lf

# Run failed tests and stop on first failure
uv run pytest --lf --tb=short
```

### Debug Specific Test

```bash
# Drop into debugger on failure
uv run pytest --pdb

# Drop into debugger on specific test
uv run pytest tests/test_crud.py::TestUserCRUD::test_create_user_success --pdb
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `pythonpath = ["src"]` is set in pytest config
2. **Database Errors**: Check that fixtures are properly configured
3. **Test Isolation**: Each test should be independent and not rely on other tests

### Environment Variables

If tests require environment variables, set them before running:

```bash
export DATABASE_URL="sqlite:///:memory:"
uv run pytest
```

### Clean Test Run

```bash
# Clean cache and run tests
make clean-cache
make test
```

## CI/CD Integration

Tests can be run in CI/CD pipelines using:

```bash
# Install dependencies
uv sync

# Run tests with coverage
uv run pytest --cov=src --cov-report=xml

# Run linting
make lint
```

## Performance

- Tests use SQLite in-memory database for speed
- Transaction rollback ensures test isolation
- Parallel test execution possible with `pytest-xdist`

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass: `make test`
3. Check code coverage: `uv run pytest --cov=src`
4. Run linting: `make lint`
5. Format code: `make format`
