# mageNT

Give Claude a team of specialist developers through MCP. Works with Claude Desktop, Claude Code, or any MCP client.

## What's this?

Ever wish Claude had deep expertise in specific areas? That's what mageNT does. Instead of getting generic advice, you can consult actual specialists:

- Need requirements? Talk to the Business Analyst
- Building a React app? Get the React Developer
- Designing an API? Ask the API Developer

Think of it like having 24 senior devs on standby, each with their own specialty.

## Quick Start

Run the installer:

```bash
cd mageNT
./install.sh                    # for Claude Desktop
./install.sh -c code            # for Claude Code
./install.sh -c both            # for both
```

That's it. The installer handles everything - creates a venv, installs deps, configures your MCP client, runs tests.

Then just restart Claude and try:
```
List the available agents
```

## Manual Setup

If you want to do it yourself:

```bash
cd mageNT
pip install -r requirements.txt
python server.py  # test it works, then Ctrl+C
```

Now add mageNT to your config:

**Claude Desktop** (`%APPDATA%\Claude\claude_desktop_config.json` on Windows):
```json
{
  "mcpServers": {
    "magent": {
      "command": "python",
      "args": ["/full/path/to/mageNT/server.py"]
    }
  }
}
```

**Claude Code** (create `.mcp.json` in your project):
```json
{
  "mcpServers": {
    "magent": {
      "command": "python",
      "args": ["/full/path/to/mageNT/server.py"]
    }
  }
}
```

Paths need to be absolute. Use `\\` on Windows, `/` on Mac/Linux.

Restart Claude completely (actually quit it, not just close the window).

## How to Use

Just talk to Claude normally:

```
I need to build user authentication - what's the best approach?
```

```
Can you review this React component for performance issues?
```

```
Start a full_stack_web workflow for a todo app
```

Claude knows when to pull in specialists automatically. Or you can request specific agents:

```
Consult the Security Engineer about this auth code
```

## Who's on the Team

24 agents across different areas:

| What they do | Who's available |
|----------|--------|
| Business stuff | Business Analyst, Product Manager |
| Architecture & Design | System Architect, UI/UX Designer |
| Frontend | React, Next.js, Vue.js devs |
| Backend | Node.js, Python, Java, Go, .NET, API specialists |
| Infrastructure | Database Admin, DevOps, Cloud Architect |
| Quality & Security | QA, Security Engineer, Performance Engineer, Automation QA |
| Other | Technical Writer, Debugging Expert, Full-Stack Dev, Mobile Dev |

## Code Quality Tools

There's also a rules engine that checks for common issues:

- Security problems (secrets in code, SQL injection, XSS)
- Style violations
- Performance antipatterns (N+1 queries, etc)
- Git stuff (bad commit messages, missing .gitignore)

Plus automation hooks:
- Pre-commit checks
- Code edit validation
- Security scans

Just ask Claude:
```
Check this code for issues: [paste code]
```

## Customizing

Edit `config.yaml` to tune agents:

```yaml
agents:
  react_developer:
    enabled: true
    expertise_level: "senior"  # junior, mid, senior, or principal
    specialization: "React 18, TypeScript, Tailwind"
```

## Workflows

Pre-built workflows coordinate multiple agents:

- `full_stack_web` - Full app (requirements → design → frontend → backend → testing)
- `api_service` - API design and implementation
- `frontend_app` - UI/UX focused

Start one like:
```
Start the full_stack_web workflow for a blog platform
```

## Making Your Own Agents

Drop a new file in `agents/`:

```python
from agents.base import BaseAgent

class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "my_agent"

    @property
    def role(self) -> str:
        return "My Specialist"

    # implement the rest...
```

Register it in `server.py` and add to `config.yaml`.

## Common Issues

**Agents not showing up?**
- Check your config path is correct and absolute
- Actually restart Claude (quit it completely)
- Run `python server.py` to see any errors

**Python not found?**
- Use full path to python in your config
- Or add Python to PATH

**Import errors?**
```bash
cd mageNT
pip install -r requirements.txt
```

## What's Where

```
mageNT/
├── server.py           # MCP server
├── config.yaml         # Your settings
├── install.sh          # Automated installer
├── agents/             # The 24 agents
├── rules/              # Code quality rules
├── hooks/              # Automation hooks
├── workflows/          # Multi-agent workflows
└── tests/              # Tests
```

## Testing

```bash
python -m pytest tests/ -v
```

## Requirements

- Python 3.10+
- Any MCP client (Claude Desktop, Claude Code, Cline, Continue, etc.)

## License

MIT
