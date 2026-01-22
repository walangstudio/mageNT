"""Run tests skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class RunTests(BaseSkill):
    """Run project tests with appropriate test runner."""

    @property
    def name(self) -> str:
        return "run_tests"

    @property
    def slash_command(self) -> str:
        return "/run-tests"

    @property
    def description(self) -> str:
        return "Run project tests with the appropriate test runner"

    @property
    def category(self) -> str:
        return "testing"

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "test_type",
                "type": "string",
                "description": "Type of tests: unit, integration, e2e, or all",
                "required": False,
            },
            {
                "name": "framework",
                "type": "string",
                "description": "Test framework: jest, vitest, pytest, junit, or auto-detect",
                "required": False,
            },
            {
                "name": "coverage",
                "type": "boolean",
                "description": "Generate coverage report",
                "required": False,
            },
            {
                "name": "watch",
                "type": "boolean",
                "description": "Run in watch mode",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        test_type = kwargs.get("test_type", "all")
        framework = kwargs.get("framework", "auto-detect")
        coverage = kwargs.get("coverage", False)
        watch = kwargs.get("watch", False)

        guidance = f"""# Test Runner Guide

## Configuration
- Test Type: {test_type}
- Framework: {framework}
- Coverage: {coverage}
- Watch Mode: {watch}

## Auto-Detection

First, detect the project type and test framework:

### Check for Configuration Files

```bash
# Check what exists
ls -la package.json pyproject.toml pom.xml build.gradle go.mod Cargo.toml 2>/dev/null
```

### Framework Detection

| File/Pattern | Framework | Command |
|--------------|-----------|---------|
| `jest.config.*` | Jest | `npm test` or `npx jest` |
| `vitest.config.*` | Vitest | `npm test` or `npx vitest` |
| `pytest.ini` or `pyproject.toml` with pytest | Pytest | `pytest` |
| `pom.xml` | Maven/JUnit | `mvn test` |
| `build.gradle` | Gradle/JUnit | `./gradlew test` |
| `go.mod` | Go Test | `go test ./...` |
| `Cargo.toml` | Cargo Test | `cargo test` |

## Test Commands by Framework

### JavaScript/TypeScript

#### Jest
```bash
# Run all tests
npx jest

# Run with coverage
npx jest --coverage

# Run in watch mode
npx jest --watch

# Run specific file
npx jest path/to/test.spec.ts

# Run tests matching pattern
npx jest -t "should handle"
```

#### Vitest
```bash
# Run all tests
npx vitest run

# Run with coverage
npx vitest run --coverage

# Run in watch mode
npx vitest

# Run specific file
npx vitest run path/to/test.spec.ts

# Run with UI
npx vitest --ui
```

#### Playwright (E2E)
```bash
# Run all E2E tests
npx playwright test

# Run with UI mode
npx playwright test --ui

# Run specific test
npx playwright test tests/login.spec.ts

# Generate report
npx playwright show-report
```

#### Cypress (E2E)
```bash
# Open Cypress UI
npx cypress open

# Run headlessly
npx cypress run

# Run specific spec
npx cypress run --spec "cypress/e2e/login.cy.ts"
```

### Python

#### Pytest
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run with verbose output
pytest -v

# Run specific file
pytest tests/test_user.py

# Run specific test
pytest tests/test_user.py::test_create_user

# Run tests matching pattern
pytest -k "login"

# Run with parallel execution
pytest -n auto
```

#### Unittest
```bash
# Run all tests
python -m unittest discover

# Run specific test
python -m unittest tests.test_user.TestUser.test_create
```

### Java

#### Maven + JUnit
```bash
# Run all tests
mvn test

# Run specific test class
mvn test -Dtest=UserServiceTest

# Run specific test method
mvn test -Dtest=UserServiceTest#testCreateUser

# Skip tests during build
mvn package -DskipTests
```

#### Gradle + JUnit
```bash
# Run all tests
./gradlew test

# Run specific test
./gradlew test --tests "UserServiceTest"

# Run with continuous mode
./gradlew test --continuous
```

### Go
```bash
# Run all tests
go test ./...

# Run with verbose output
go test -v ./...

# Run with coverage
go test -cover ./...

# Generate coverage profile
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# Run specific package
go test ./internal/user/...

# Run specific test
go test -run TestCreateUser ./...
```

### Rust
```bash
# Run all tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_name

# Run tests in specific module
cargo test module_name::
```

## Test Organization

### Running by Type

#### Unit Tests Only
```bash
# Jest/Vitest (by folder convention)
npx jest unit/
npx vitest run src/**/*.unit.test.ts

# Pytest (by marker)
pytest -m unit

# Go (by pattern)
go test -run "Unit" ./...
```

#### Integration Tests Only
```bash
# Jest/Vitest
npx jest integration/

# Pytest
pytest -m integration
pytest tests/integration/

# Maven
mvn verify -Pintegration-tests
```

#### E2E Tests Only
```bash
# Playwright
npx playwright test

# Cypress
npx cypress run

# Pytest with selenium
pytest tests/e2e/
```

## Coverage Reports

### Generate Coverage
"""

        if coverage:
            guidance += """
#### JavaScript
```bash
# Jest
npx jest --coverage --coverageReporters="text" --coverageReporters="html"

# Vitest
npx vitest run --coverage
```

#### Python
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
```

#### Go
```bash
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out -o coverage.html
```

### Coverage Targets
| Metric | Good | Better | Best |
|--------|------|--------|------|
| Line Coverage | 60% | 80% | 90%+ |
| Branch Coverage | 50% | 70% | 85%+ |
| Function Coverage | 70% | 85% | 95%+ |
"""

        if watch:
            guidance += """
## Watch Mode

Watch mode reruns tests when files change:

```bash
# Jest
npx jest --watch

# Vitest (default behavior)
npx vitest

# Pytest with pytest-watch
pip install pytest-watch
ptw

# Go with air or similar
go install github.com/cosmtrek/air@latest
air
```
"""

        guidance += """
## Troubleshooting Test Failures

### Common Issues

1. **Tests timing out**
   - Increase timeout: `jest.setTimeout(10000)`
   - Check for unresolved promises
   - Mock slow dependencies

2. **Flaky tests**
   - Add proper waits (not sleep)
   - Isolate test data
   - Run tests in isolation: `--runInBand`

3. **Import errors**
   - Check module paths
   - Verify test config (tsconfig, etc.)
   - Clear cache: `jest --clearCache`

4. **Database/state issues**
   - Reset state in beforeEach
   - Use transactions that rollback
   - Mock external services

## Next Steps

1. Run the tests for your project
2. Review any failures
3. Check coverage gaps
4. Add missing test cases
"""

        return {
            "guidance": guidance,
            "context": {
                "test_type": test_type,
                "framework": framework,
                "coverage": coverage,
                "watch": watch,
            },
            "success": True,
        }
