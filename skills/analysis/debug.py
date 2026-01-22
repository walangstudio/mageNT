"""Debug code skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class DebugCode(BaseSkill):
    """Debug and analyze code issues."""

    @property
    def name(self) -> str:
        return "debug_code"

    @property
    def slash_command(self) -> str:
        return "/debug"

    @property
    def description(self) -> str:
        return "Debug and analyze code issues with systematic approaches"

    @property
    def category(self) -> str:
        return "analysis"

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "issue_description",
                "type": "string",
                "description": "Description of the issue or bug",
                "required": True,
            },
            {
                "name": "code_snippet",
                "type": "string",
                "description": "The problematic code snippet",
                "required": False,
            },
            {
                "name": "language",
                "type": "string",
                "description": "Programming language (javascript, python, java, etc.)",
                "required": False,
            },
            {
                "name": "error_message",
                "type": "string",
                "description": "Any error messages received",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        issue = kwargs.get("issue_description", "No description provided")
        code = kwargs.get("code_snippet", "")
        language = kwargs.get("language", "unknown")
        error = kwargs.get("error_message", "")

        guidance = f"""# Debugging Guide

## Issue Description
{issue}

## Systematic Debugging Approach

### Step 1: Understand the Problem
- [ ] Can you reproduce the issue consistently?
- [ ] What is the expected behavior?
- [ ] What is the actual behavior?
- [ ] When did this start happening? (recent changes?)

### Step 2: Gather Information
"""

        if error:
            guidance += f"""
#### Error Message Analysis
```
{error}
```

Key things to identify:
- Error type/class
- Error message
- Stack trace location (file, line number)
- Root cause vs symptom
"""

        if code:
            guidance += f"""
#### Code Under Investigation
```{language}
{code}
```

Code review checklist:
- [ ] Variable initialization
- [ ] Null/undefined checks
- [ ] Array bounds
- [ ] Type coercion issues
- [ ] Async/await handling
- [ ] Exception handling
- [ ] Resource cleanup
"""

        guidance += """
### Step 3: Isolate the Problem

#### Binary Search Debugging
1. Identify the last known working state
2. Find the midpoint between working and broken
3. Test at midpoint - does it work?
4. Repeat until you find the exact change

#### Component Isolation
- Test each component independently
- Mock dependencies to isolate behavior
- Use minimal reproducible examples

### Step 4: Common Issue Patterns

#### JavaScript/TypeScript
- `undefined is not a function` - Check method exists, check `this` binding
- `Cannot read property of undefined` - Add null checks, verify data structure
- Async issues - Check Promise handling, race conditions
- Closure issues - Variable capture in loops

#### Python
- `AttributeError` - Check object type, verify attribute exists
- `TypeError` - Check function signatures, argument types
- `ImportError` - Check module paths, virtual environment
- Indentation - Verify consistent tabs/spaces

#### Java
- `NullPointerException` - Add null checks, use Optional
- `ClassCastException` - Verify type hierarchy
- `ConcurrentModificationException` - Use proper concurrent collections

#### Database
- Connection issues - Check credentials, network, pool exhaustion
- Slow queries - Check indexes, explain plan
- Deadlocks - Check transaction order, lock acquisition

### Step 5: Debugging Tools

#### General
- Print/console.log debugging (strategic placement)
- Debugger breakpoints
- Watch expressions
- Call stack inspection

#### Language-Specific

**JavaScript/Node.js:**
```javascript
// Debug logging
console.log('Variable state:', JSON.stringify(obj, null, 2))
console.trace('Call stack at this point')

// Node.js debugger
node --inspect app.js
```

**Python:**
```python
# Debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Interactive debugging
import pdb; pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()
```

**Java:**
```java
// Debug logging
System.out.println("Debug: " + variable);

// Use IDE debugger with conditional breakpoints
```

### Step 6: Fix Verification
- [ ] Does the fix address the root cause?
- [ ] Are there similar patterns elsewhere that need fixing?
- [ ] Add tests to prevent regression
- [ ] Document the fix for future reference

### Step 7: Prevention
- Add logging at key points
- Improve error messages
- Add input validation
- Write tests for edge cases
"""

        return {
            "guidance": guidance,
            "context": {
                "issue_description": issue,
                "language": language,
                "has_code": bool(code),
                "has_error": bool(error),
            },
            "success": True,
        }
