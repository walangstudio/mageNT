"""Generate tests skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class GenerateTests(BaseSkill):
    """Generate test cases for code."""

    @property
    def name(self) -> str:
        return "generate_tests"

    @property
    def slash_command(self) -> str:
        return "/generate-tests"

    @property
    def description(self) -> str:
        return "Generate test cases for functions, classes, or modules"

    @property
    def category(self) -> str:
        return "testing"

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "code",
                "type": "string",
                "description": "The code to generate tests for",
                "required": True,
            },
            {
                "name": "language",
                "type": "string",
                "description": "Programming language: javascript, typescript, python, java, go",
                "required": False,
            },
            {
                "name": "framework",
                "type": "string",
                "description": "Test framework: jest, vitest, pytest, junit, gotest",
                "required": False,
            },
            {
                "name": "test_type",
                "type": "string",
                "description": "Type of tests: unit, integration, or both",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        code = kwargs.get("code", "")
        language = kwargs.get("language", "typescript")
        framework = kwargs.get("framework", "vitest")
        test_type = kwargs.get("test_type", "unit")

        guidance = f"""# Test Generation Guide

## Configuration
- Language: {language}
- Framework: {framework}
- Test Type: {test_type}

## Code to Test
```{language}
{code if code else "// Paste or reference your code here"}
```

## Test Writing Guidelines

### Test Structure (AAA Pattern)

Every test should follow the **Arrange-Act-Assert** pattern:

```
1. ARRANGE: Set up test data and preconditions
2. ACT: Execute the code under test
3. ASSERT: Verify the expected outcome
```

### Test Naming Conventions

Good test names describe:
- What is being tested
- Under what conditions
- Expected result

```
// Format: should_[expected]_when_[condition]
// or: [method]_[scenario]_[expectedResult]

"should return user when valid ID provided"
"createUser_withValidData_returnsNewUser"
"handles empty input gracefully"
```

## Test Templates by Framework

### Jest / Vitest (TypeScript)
```typescript
import {{ describe, it, expect, beforeEach, vi }} from 'vitest'
// or for Jest:
// import {{ describe, it, expect, beforeEach, jest }} from '@jest/globals'

import {{ YourFunction, YourClass }} from './your-module'

describe('YourFunction', () => {{
  // Test happy path
  it('should return expected result with valid input', () => {{
    // Arrange
    const input = {{ /* test data */ }}
    const expected = {{ /* expected result */ }}

    // Act
    const result = YourFunction(input)

    // Assert
    expect(result).toEqual(expected)
  }})

  // Test edge cases
  it('should handle empty input', () => {{
    expect(YourFunction(null)).toBeNull()
    expect(YourFunction(undefined)).toBeUndefined()
    expect(YourFunction([])).toEqual([])
  }})

  // Test error cases
  it('should throw error for invalid input', () => {{
    expect(() => YourFunction('invalid')).toThrow('Expected error message')
  }})
}})

describe('YourClass', () => {{
  let instance: YourClass

  beforeEach(() => {{
    instance = new YourClass()
  }})

  describe('methodName', () => {{
    it('should do something', () => {{
      const result = instance.methodName()
      expect(result).toBeDefined()
    }})
  }})
}})

// Mocking example
describe('with mocks', () => {{
  it('should call dependency', () => {{
    const mockFn = vi.fn().mockReturnValue('mocked')
    // or Jest: const mockFn = jest.fn().mockReturnValue('mocked')

    const result = functionThatUsesDependency(mockFn)

    expect(mockFn).toHaveBeenCalledWith('expected arg')
    expect(result).toBe('mocked')
  }})
}})
```

### Pytest (Python)
```python
import pytest
from unittest.mock import Mock, patch
from your_module import your_function, YourClass


class TestYourFunction:
    \"\"\"Tests for your_function.\"\"\"

    def test_returns_expected_with_valid_input(self):
        \"\"\"Should return expected result with valid input.\"\"\"
        # Arrange
        input_data = {{"key": "value"}}
        expected = {{"result": "expected"}}

        # Act
        result = your_function(input_data)

        # Assert
        assert result == expected

    def test_handles_empty_input(self):
        \"\"\"Should handle empty input gracefully.\"\"\"
        assert your_function(None) is None
        assert your_function({{}}) == {{}}

    def test_raises_error_for_invalid_input(self):
        \"\"\"Should raise ValueError for invalid input.\"\"\"
        with pytest.raises(ValueError, match="Invalid input"):
            your_function("invalid")

    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (0, 0),
        (-1, -2),
    ])
    def test_with_multiple_inputs(self, input, expected):
        \"\"\"Should handle multiple inputs correctly.\"\"\"
        assert your_function(input) == expected


class TestYourClass:
    \"\"\"Tests for YourClass.\"\"\"

    @pytest.fixture
    def instance(self):
        \"\"\"Create instance for tests.\"\"\"
        return YourClass()

    def test_method_does_something(self, instance):
        \"\"\"Method should do something.\"\"\"
        result = instance.method_name()
        assert result is not None


# Mocking example
class TestWithMocks:
    \"\"\"Tests using mocks.\"\"\"

    @patch('your_module.external_service')
    def test_calls_external_service(self, mock_service):
        \"\"\"Should call external service correctly.\"\"\"
        mock_service.return_value = "mocked response"

        result = function_using_service()

        mock_service.assert_called_once_with("expected arg")
        assert result == "mocked response"
```

### JUnit 5 (Java)
```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class YourClassTest {{

    private YourClass instance;

    @BeforeEach
    void setUp() {{
        instance = new YourClass();
    }}

    @Test
    @DisplayName("should return expected result with valid input")
    void shouldReturnExpectedWithValidInput() {{
        // Arrange
        String input = "valid";
        String expected = "result";

        // Act
        String result = instance.process(input);

        // Assert
        assertEquals(expected, result);
    }}

    @Test
    @DisplayName("should throw exception for null input")
    void shouldThrowForNullInput() {{
        assertThrows(IllegalArgumentException.class, () -> {{
            instance.process(null);
        }});
    }}

    @ParameterizedTest
    @ValueSource(strings = {{"a", "b", "c"}})
    void shouldHandleMultipleInputs(String input) {{
        assertNotNull(instance.process(input));
    }}
}}

// With Mockito
class YourServiceTest {{

    @Mock
    private Repository repository;

    @InjectMocks
    private YourService service;

    @BeforeEach
    void setUp() {{
        MockitoAnnotations.openMocks(this);
    }}

    @Test
    void shouldCallRepository() {{
        when(repository.findById(1L)).thenReturn(Optional.of(new Entity()));

        service.getById(1L);

        verify(repository).findById(1L);
    }}
}}
```

### Go Test
```go
package yourpackage

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestYourFunction(t *testing.T) {{
    t.Run("returns expected with valid input", func(t *testing.T) {{
        // Arrange
        input := "valid"
        expected := "result"

        // Act
        result := YourFunction(input)

        // Assert
        assert.Equal(t, expected, result)
    }})

    t.Run("handles empty input", func(t *testing.T) {{
        result := YourFunction("")
        assert.Empty(t, result)
    }})

    t.Run("returns error for invalid input", func(t *testing.T) {{
        _, err := YourFunction("invalid")
        require.Error(t, err)
        assert.Contains(t, err.Error(), "invalid")
    }})
}}

// Table-driven tests (Go idiom)
func TestYourFunctionTableDriven(t *testing.T) {{
    tests := []struct {{
        name     string
        input    string
        expected string
        wantErr  bool
    }}{{
        {{"valid input", "abc", "ABC", false}},
        {{"empty input", "", "", false}},
        {{"invalid input", "!", "", true}},
    }}

    for _, tt := range tests {{
        t.Run(tt.name, func(t *testing.T) {{
            result, err := YourFunction(tt.input)
            if tt.wantErr {{
                require.Error(t, err)
                return
            }}
            require.NoError(t, err)
            assert.Equal(t, tt.expected, result)
        }})
    }}
}}
```

## Test Categories to Cover

### 1. Happy Path Tests
- Normal, expected inputs
- Successful operations
- Valid data flows

### 2. Edge Cases
- Empty inputs (null, undefined, empty string, empty array)
- Boundary values (0, -1, MAX_INT, etc.)
- Single item collections
- Maximum size inputs

### 3. Error Cases
- Invalid inputs
- Missing required fields
- Wrong types
- Unauthorized access

### 4. Integration Points
- API calls (mock external services)
- Database operations
- File system operations
- Third-party services

## Test Checklist

For the code provided, consider testing:

- [ ] Function with valid input returns expected output
- [ ] Function handles null/undefined/empty input
- [ ] Function throws appropriate errors for invalid input
- [ ] All code branches are covered
- [ ] Error messages are meaningful
- [ ] Side effects are verified (for impure functions)
- [ ] Async operations complete correctly
- [ ] Edge cases are handled
"""

        return {
            "guidance": guidance,
            "context": {
                "language": language,
                "framework": framework,
                "test_type": test_type,
                "has_code": bool(code),
            },
            "success": True,
        }
