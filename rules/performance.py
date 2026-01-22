"""Performance rules for code optimization."""

import re
from .base import (
    BaseRule,
    RuleCategory,
    RuleContext,
    RuleResult,
    RuleSeverity,
    RuleViolation,
)


class NoN1QueryRule(BaseRule):
    """Detect potential N+1 query patterns."""

    N1_PATTERNS = [
        # Loop with query inside
        (r'for\s+\w+\s+in\s+\w+:.*\n\s+.*\.(?:get|filter|find|query|select|fetch)', "Query inside loop"),
        # ORM calls that might trigger N+1
        (r'\.all\(\).*for\s+\w+\s+in', "Iteration after .all() may trigger N+1"),
    ]

    LAZY_LOAD_PATTERNS = [
        (r'\.objects\.get\([^)]+\)\.\w+_set\.all\(\)', "Lazy loading related objects"),
        (r'ForeignKey.*on_delete', "ForeignKey without select_related hint"),
    ]

    @property
    def name(self) -> str:
        return "no-n1-queries"

    @property
    def description(self) -> str:
        return "Detect N+1 query patterns that cause performance issues"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PERFORMANCE

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")

        # Check for query patterns inside loops
        in_loop = False
        loop_start = 0

        for line_num, line in enumerate(lines, 1):
            # Track loop entry
            if re.match(r'\s*(for|while)\s+', line):
                in_loop = True
                loop_start = line_num

            # Check for queries inside loops
            if in_loop:
                query_patterns = [
                    r'\.get\(',
                    r'\.filter\(',
                    r'\.find\(',
                    r'\.find_one\(',
                    r'\.query\(',
                    r'\.execute\(',
                    r'SELECT\s+',
                    r'\.fetch',
                ]
                for pattern in query_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append(
                            RuleViolation(
                                rule_name=self.name,
                                message="Database query inside loop (potential N+1)",
                                severity=self.severity,
                                line_number=line_num,
                                suggestion="Batch queries outside the loop or use eager loading",
                                code_snippet=line.strip()[:80],
                            )
                        )

            # Track loop exit (simplified - check for dedent)
            if in_loop and line.strip() and not line.startswith(" " * 4) and line_num > loop_start:
                in_loop = False

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} potential N+1 queries" if violations else "No N+1 patterns detected",
        )

    def get_guidance(self) -> str:
        return """**no-n1-queries**: Avoid queries inside loops.

**Bad (N+1 queries):**
```python
# Makes N+1 database calls
users = User.objects.all()
for user in users:
    orders = Order.objects.filter(user=user)  # N queries!
```

**Good (batched queries):**
```python
# Django - use select_related/prefetch_related
users = User.objects.prefetch_related('orders').all()
for user in users:
    orders = user.orders.all()  # No extra query!

# SQLAlchemy - use joinedload
users = session.query(User).options(joinedload(User.orders)).all()

# Raw SQL - JOIN or batch
user_ids = [u.id for u in users]
orders = Order.objects.filter(user_id__in=user_ids)
```"""


class NoSyncInAsyncRule(BaseRule):
    """Detect blocking synchronous calls in async code."""

    BLOCKING_PATTERNS = [
        (r'async\s+def\s+\w+.*:\s*\n(?:.*\n)*?\s+time\.sleep\(', "time.sleep in async function"),
        (r'async\s+def\s+\w+.*:\s*\n(?:.*\n)*?\s+requests\.', "requests in async function"),
        (r'async\s+def\s+\w+.*:\s*\n(?:.*\n)*?\s+open\(', "file open in async function"),
        (r'async\s+def\s+\w+.*:\s*\n(?:.*\n)*?\s+input\(', "input() in async function"),
    ]

    SYNC_CALLS = [
        (r'time\.sleep\(', "Use asyncio.sleep() instead of time.sleep()"),
        (r'requests\.(get|post|put|delete|patch)\(', "Use aiohttp or httpx instead of requests"),
        (r'\bopen\([^)]+\)(?!.*aio)', "Use aiofiles for async file operations"),
    ]

    @property
    def name(self) -> str:
        return "no-sync-in-async"

    @property
    def description(self) -> str:
        return "Detect blocking synchronous calls in async functions"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PERFORMANCE

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")
        in_async_function = False
        async_indent = 0

        for line_num, line in enumerate(lines, 1):
            # Track async function entry
            async_match = re.match(r'^(\s*)async\s+def\s+', line)
            if async_match:
                in_async_function = True
                async_indent = len(async_match.group(1))
                continue

            # Track function exit
            if in_async_function and line.strip():
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= async_indent and not line.strip().startswith('#'):
                    if re.match(r'^\s*(def|async def|class)\s+', line):
                        in_async_function = False

            # Check for blocking calls in async context
            if in_async_function:
                for pattern, message in self.SYNC_CALLS:
                    if re.search(pattern, line):
                        violations.append(
                            RuleViolation(
                                rule_name=self.name,
                                message=f"Blocking call in async function: {message}",
                                severity=self.severity,
                                line_number=line_num,
                                suggestion=message,
                                code_snippet=line.strip()[:80],
                            )
                        )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} blocking calls in async code" if violations else "No blocking calls in async code",
        )

    def get_guidance(self) -> str:
        return """**no-sync-in-async**: Don't block the event loop.

**Blocking calls and their async alternatives:**

| Blocking | Async Alternative |
|----------|-------------------|
| `time.sleep()` | `await asyncio.sleep()` |
| `requests.get()` | `await httpx.get()` or `aiohttp` |
| `open()` | `await aiofiles.open()` |
| `input()` | `aioconsole.ainput()` |

**Example fix:**
```python
# Bad
async def fetch_data():
    time.sleep(1)  # Blocks event loop!
    response = requests.get(url)  # Blocks!

# Good
async def fetch_data():
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
```

**When you must use sync code:**
```python
await asyncio.to_thread(blocking_function, args)
```"""


class MemoizationRule(BaseRule):
    """Suggest memoization for expensive repeated calculations."""

    EXPENSIVE_PATTERNS = [
        (r'def\s+(\w+)\([^)]*\):.*\n(?:.*\n)*?\1\([^)]*\)', "Recursive function without memoization"),
    ]

    @property
    def name(self) -> str:
        return "consider-memoization"

    @property
    def description(self) -> str:
        return "Suggest memoization for potentially expensive repeated calculations"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PERFORMANCE

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        # Check for recursive functions without caching decorators
        lines = code.split("\n")
        function_name = None
        function_start = 0
        has_cache_decorator = False

        for line_num, line in enumerate(lines, 1):
            # Check for caching decorators
            if re.search(r'@(lru_cache|cache|cached|memoize)', line):
                has_cache_decorator = True
                continue

            # Check for function definition
            func_match = re.match(r'\s*def\s+(\w+)\s*\(', line)
            if func_match:
                # Check previous function for recursive calls
                if function_name and not has_cache_decorator:
                    # Look for recursive calls in the previous function
                    pass

                function_name = func_match.group(1)
                function_start = line_num
                has_cache_decorator = False
                continue

            # Check for recursive call in current function
            if function_name and re.search(rf'\b{function_name}\s*\(', line):
                if not has_cache_decorator:
                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=f"Recursive function '{function_name}' may benefit from memoization",
                            severity=self.severity,
                            line_number=function_start,
                            suggestion="Add @functools.lru_cache or @functools.cache decorator",
                        )
                    )
                    has_cache_decorator = True  # Don't report again for same function

        return RuleResult(
            rule_name=self.name,
            passed=True,  # This is just a suggestion
            violations=violations,
            message=f"Found {len(violations)} memoization opportunities" if violations else "No memoization suggestions",
        )

    def get_guidance(self) -> str:
        return """**consider-memoization**: Cache expensive repeated calculations.

**When to memoize:**
- Recursive functions (fibonacci, tree traversal)
- Functions called repeatedly with same arguments
- Expensive computations (parsing, calculations)

**Python:**
```python
from functools import lru_cache, cache

@lru_cache(maxsize=128)  # LRU with size limit
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

@cache  # Unlimited cache (Python 3.9+)
def expensive_calculation(x, y):
    return complex_math(x, y)
```

**JavaScript:**
```javascript
// Simple memoization
const memoize = (fn) => {
  const cache = new Map();
  return (...args) => {
    const key = JSON.stringify(args);
    if (!cache.has(key)) {
      cache.set(key, fn(...args));
    }
    return cache.get(key);
  };
};
```"""


class LazyLoadingRule(BaseRule):
    """Suggest lazy loading for expensive initializations."""

    EAGER_PATTERNS = [
        (r'^\s*(\w+)\s*=\s*load_\w+\(', "Eager loading at module level"),
        (r'^\s*(\w+)\s*=\s*\w+\.connect\(', "Database connection at module level"),
        (r'^\s*(\w+)\s*=\s*open\(', "File opened at module level"),
    ]

    @property
    def name(self) -> str:
        return "consider-lazy-loading"

    @property
    def description(self) -> str:
        return "Suggest lazy loading for expensive module-level initializations"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PERFORMANCE

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")
        in_function = False
        in_class = False

        for line_num, line in enumerate(lines, 1):
            # Track scope
            if re.match(r'^def\s+|^async\s+def\s+', line):
                in_function = True
            elif re.match(r'^class\s+', line):
                in_class = True
            elif line and not line.startswith(' ') and not line.startswith('\t'):
                in_function = False
                in_class = False

            # Only check module-level code
            if in_function or in_class:
                continue

            for pattern, message in self.EAGER_PATTERNS:
                if re.search(pattern, line):
                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=message,
                            severity=self.severity,
                            line_number=line_num,
                            suggestion="Consider lazy loading or dependency injection",
                            code_snippet=line.strip()[:80],
                        )
                    )

        return RuleResult(
            rule_name=self.name,
            passed=True,  # This is just a suggestion
            violations=violations,
            message=f"Found {len(violations)} lazy loading opportunities" if violations else "No lazy loading suggestions",
        )

    def get_guidance(self) -> str:
        return """**consider-lazy-loading**: Defer expensive operations.

**Problem:**
```python
# Module level - runs on import!
db = connect_to_database()  # Slow!
config = load_large_config()  # Slow!
```

**Solution - Lazy loading:**
```python
_db = None

def get_db():
    global _db
    if _db is None:
        _db = connect_to_database()
    return _db

# Or use functools
from functools import lru_cache

@lru_cache
def get_config():
    return load_large_config()
```

**Benefits:**
- Faster import times
- Resources only loaded when needed
- Easier testing (can mock before first use)"""


# Export all performance rules
PERFORMANCE_RULES = [
    NoN1QueryRule,
    NoSyncInAsyncRule,
    MemoizationRule,
    LazyLoadingRule,
]
