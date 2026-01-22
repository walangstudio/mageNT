"""Error analyzer skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class AnalyzeError(BaseSkill):
    """Analyze error messages and stack traces."""

    @property
    def name(self) -> str:
        return "analyze_error"

    @property
    def slash_command(self) -> str:
        return "/analyze-error"

    @property
    def description(self) -> str:
        return "Analyze error messages and stack traces to identify root causes"

    @property
    def category(self) -> str:
        return "analysis"

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "error_message",
                "type": "string",
                "description": "The error message or stack trace to analyze",
                "required": True,
            },
            {
                "name": "context",
                "type": "string",
                "description": "Additional context (what were you trying to do?)",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        error = kwargs.get("error_message", "No error provided")
        context = kwargs.get("context", "")

        guidance = f"""# Error Analysis Guide

## Error Message
```
{error}
```

"""

        if context:
            guidance += f"""## Context
{context}

"""

        guidance += """## Analysis Framework

### Step 1: Parse the Error

#### Identify Error Components
- **Error Type/Class**: The category of error (e.g., TypeError, NullPointerException)
- **Error Message**: Human-readable description
- **Stack Trace**: Call sequence leading to the error
- **Source Location**: File name and line number

### Step 2: Read the Stack Trace

Stack traces are read **bottom to top** (or top to bottom depending on language):

#### JavaScript/Node.js (read bottom to top)
```
Error: Something went wrong
    at processData (/app/src/service.js:45:12)      <- Error occurred here
    at handleRequest (/app/src/handler.js:23:8)      <- Called by this
    at router (/app/src/router.js:15:5)              <- Which was called by this
```

#### Python (read bottom to top)
```
Traceback (most recent call last):
  File "main.py", line 10, in <module>               <- Entry point
    result = process_data(data)
  File "processor.py", line 25, in process_data      <- Called this
    return transform(item)
  File "transformer.py", line 42, in transform       <- Error here
TypeError: 'NoneType' object is not subscriptable
```

#### Java (read top to bottom)
```
java.lang.NullPointerException: Cannot invoke method on null
    at com.app.Service.process(Service.java:45)      <- Error here
    at com.app.Handler.handle(Handler.java:23)       <- Called by this
    at com.app.Main.main(Main.java:10)               <- Entry point
```

### Step 3: Common Error Patterns

#### Null/Undefined Errors
| Error | Language | Common Cause |
|-------|----------|--------------|
| `TypeError: Cannot read property 'x' of undefined` | JavaScript | Accessing property on undefined |
| `TypeError: 'NoneType' object has no attribute` | Python | Calling method on None |
| `NullPointerException` | Java | Calling method on null |
| `NullReferenceException` | C# | Dereferencing null |

**Solutions:**
- Add null checks before access
- Use optional chaining (`?.`)
- Verify data is loaded before use
- Check function return values

#### Type Errors
| Error | Language | Common Cause |
|-------|----------|--------------|
| `TypeError: X is not a function` | JavaScript | Calling non-function as function |
| `TypeError: unsupported operand type(s)` | Python | Wrong types in operation |
| `ClassCastException` | Java | Invalid type casting |

**Solutions:**
- Check variable types
- Verify function imports
- Use type guards
- Add type annotations

#### Import/Module Errors
| Error | Language | Common Cause |
|-------|----------|--------------|
| `ModuleNotFoundError` | Python | Missing package or wrong path |
| `Cannot find module` | Node.js | Missing package or wrong path |
| `ClassNotFoundException` | Java | Missing dependency or classpath |

**Solutions:**
- Install missing packages
- Check import paths
- Verify module exists
- Check package.json/requirements.txt

#### Connection Errors
| Error | Common Cause |
|-------|--------------|
| `ECONNREFUSED` | Service not running on target port |
| `ETIMEDOUT` | Network timeout, firewall blocking |
| `Connection refused` | Database/service not accepting connections |

**Solutions:**
- Verify service is running
- Check port numbers
- Verify network connectivity
- Check firewall rules

### Step 4: Debugging Actions

Based on the error, try these approaches:

1. **Reproduce**: Can you trigger the error consistently?
2. **Isolate**: Create minimal code that produces the error
3. **Verify assumptions**: Check each variable/value at the error point
4. **Check recent changes**: Did something change recently?
5. **Search**: Look up the exact error message

### Step 5: Quick Fixes by Error Type

#### "X is undefined/null"
```javascript
// Before
const value = obj.nested.property

// After (with checks)
const value = obj?.nested?.property ?? defaultValue
```

#### "Cannot find module"
```bash
# Node.js
npm install <package-name>

# Python
pip install <package-name>
```

#### "Permission denied"
```bash
# Check file permissions
ls -la <file>

# Fix permissions
chmod +x <file>
```

#### "Port already in use"
```bash
# Find process using port
lsof -i :<port>  # macOS/Linux
netstat -ano | findstr :<port>  # Windows

# Kill process or use different port
```

### Step 6: Next Steps

After analyzing the error:
1. [ ] Identify the exact line causing the error
2. [ ] Understand what state the variables are in
3. [ ] Determine why the state is incorrect
4. [ ] Fix the root cause, not just the symptom
5. [ ] Add error handling for edge cases
6. [ ] Write a test to catch this in the future
"""

        return {
            "guidance": guidance,
            "context": {
                "error_message": error[:200] + "..." if len(error) > 200 else error,
                "has_context": bool(context),
            },
            "success": True,
        }
