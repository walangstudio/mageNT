"""Check package versions skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class CheckVersions(BaseSkill):
    """Check latest stable versions from package registries."""

    @property
    def name(self) -> str:
        return "check_versions"

    @property
    def slash_command(self) -> str:
        return "/check-versions"

    @property
    def description(self) -> str:
        return "Check latest stable package versions from npm, PyPI, Maven, and other registries"

    @property
    def category(self) -> str:
        return "version"

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "packages",
                "type": "string",
                "description": "Comma-separated list of packages (e.g., 'react,express' or 'fastapi,sqlalchemy')",
                "required": True,
            },
            {
                "name": "registry",
                "type": "string",
                "description": "Package registry: npm, pypi, maven, nuget, go, cargo, rubygems, or auto",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        packages = kwargs.get("packages", "")
        registry = kwargs.get("registry", "auto")

        package_list = [p.strip() for p in packages.split(",") if p.strip()]

        guidance = f"""# Package Version Checker

## Requested Packages
{', '.join(package_list) if package_list else 'No packages specified'}

## Registry Commands by Platform

### npm (Node.js/JavaScript)
```bash
# Check single package
npm view <package> version

# Check multiple packages
npm view react version && npm view express version

# Check all outdated in project
npm outdated

# View all versions available
npm view <package> versions --json
```

### PyPI (Python)
```bash
# Using pip
pip index versions <package>

# Or check on web
# https://pypi.org/project/<package>/

# Check outdated in project
pip list --outdated

# Using pip-tools
pip-compile --upgrade
```

### Maven Central (Java)
```bash
# Using Maven
mvn versions:display-dependency-updates

# Check via API
curl -s "https://search.maven.org/solrsearch/select?q=g:<group>+AND+a:<artifact>&rows=1&wt=json"

# Example for Spring Boot
curl -s "https://search.maven.org/solrsearch/select?q=g:org.springframework.boot+AND+a:spring-boot-starter&rows=1&wt=json" | jq '.response.docs[0].latestVersion'
```

### NuGet (.NET)
```bash
# Using dotnet CLI
dotnet list package --outdated

# Check specific package
nuget list <package> -AllVersions

# Via API
curl -s "https://api.nuget.org/v3-flatcontainer/<package>/index.json" | jq '.versions[-1]'
```

### Go Modules
```bash
# Check latest version
go list -m -versions <module>

# Update to latest
go get <module>@latest

# Check outdated
go list -m -u all
```

### Cargo (Rust)
```bash
# Check outdated
cargo outdated

# View crate info
cargo search <crate>

# Via API
curl -s "https://crates.io/api/v1/crates/<crate>" | jq '.crate.newest_version'
```

### RubyGems
```bash
# Check latest version
gem search <gem> --remote

# Via API
curl -s "https://rubygems.org/api/v1/gems/<gem>.json" | jq '.version'
```

## Quick Version Lookup Commands

### Popular npm Packages
```bash
# React ecosystem
npm view react version           # React
npm view next version            # Next.js
npm view @types/react version    # React types

# Backend
npm view express version         # Express
npm view fastify version         # Fastify
npm view @nestjs/core version    # NestJS

# Build tools
npm view vite version            # Vite
npm view esbuild version         # esbuild
npm view typescript version      # TypeScript

# Testing
npm view vitest version          # Vitest
npm view jest version            # Jest
npm view playwright version      # Playwright
```

### Popular PyPI Packages
```bash
# Web frameworks
pip index versions fastapi
pip index versions django
pip index versions flask

# Data
pip index versions pandas
pip index versions numpy
pip index versions sqlalchemy

# Testing
pip index versions pytest
pip index versions httpx
```

## Batch Version Check Script

### Node.js
```javascript
// check-versions.js
const {{ execSync }} = require('child_process')

const packages = ['react', 'express', 'typescript', 'vite']

packages.forEach(pkg => {{
  try {{
    const version = execSync(`npm view ${{pkg}} version`, {{ encoding: 'utf8' }}).trim()
    console.log(`${{pkg}}: ${{version}}`)
  }} catch (e) {{
    console.log(`${{pkg}}: Error fetching version`)
  }}
}})
```

### Python
```python
# check_versions.py
import subprocess
import json

packages = ['fastapi', 'sqlalchemy', 'pydantic', 'pytest']

for pkg in packages:
    try:
        result = subprocess.run(
            ['pip', 'index', 'versions', pkg],
            capture_output=True, text=True
        )
        # Parse version from output
        print(f"{{pkg}}: {{result.stdout.split()[1] if result.stdout else 'N/A'}}")
    except Exception as e:
        print(f"{{pkg}}: Error")
```

## Version Compatibility Notes

### Semantic Versioning (SemVer)
- **MAJOR.MINOR.PATCH** (e.g., 2.1.3)
- MAJOR: Breaking changes
- MINOR: New features, backwards compatible
- PATCH: Bug fixes, backwards compatible

### Version Ranges in package.json
```json
{{
  "dependencies": {{
    "react": "^18.2.0",    // >=18.2.0 <19.0.0
    "express": "~4.18.0",  // >=4.18.0 <4.19.0
    "lodash": "4.17.21"    // Exact version
  }}
}}
```

### Version Ranges in requirements.txt
```
fastapi>=0.100.0,<1.0.0
pydantic>=2.0.0
sqlalchemy~=2.0.0
```

## Recommended Versions (as of latest stable)

> Note: Always verify these are current by running the commands above.

### Frontend
| Package | Check Command |
|---------|--------------|
| React | `npm view react version` |
| Next.js | `npm view next version` |
| Vue | `npm view vue version` |
| Vite | `npm view vite version` |
| TypeScript | `npm view typescript version` |

### Backend
| Package | Check Command |
|---------|--------------|
| Express | `npm view express version` |
| FastAPI | `pip index versions fastapi` |
| Spring Boot | Check Maven Central |
| .NET | `dotnet --list-sdks` |

### Databases
| Package | Check Command |
|---------|--------------|
| Prisma | `npm view prisma version` |
| Drizzle | `npm view drizzle-orm version` |
| SQLAlchemy | `pip index versions sqlalchemy` |

## Next Steps

1. Run the appropriate commands for your packages
2. Update package.json / requirements.txt / pom.xml
3. Test thoroughly after upgrading
4. Check changelogs for breaking changes
"""

        return {
            "guidance": guidance,
            "context": {
                "packages": package_list,
                "registry": registry,
            },
            "success": True,
        }
