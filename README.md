# mageNT

![version](https://img.shields.io/badge/version-0.3.0-blue)
![python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet)
![platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![license](https://img.shields.io/badge/license-MIT-green)

Give Claude a team of specialist developers through MCP. Works with Claude Desktop, Claude Code, or any MCP client.

## What's this?

Ever wish Claude had deep expertise in specific areas? That's what mageNT does. Instead of getting generic advice, you can consult actual specialists:

- Need requirements? Talk to the Business Analyst
- Building a React app? Get the React Developer
- Designing an API? Ask the API Developer

Think of it like having 32 senior devs on standby, each with their own specialty.

## Quick Start

Run the installer:

**Linux / macOS / Git Bash (Windows):**
```bash
cd mageNT
./install.sh                           # Claude Desktop
./install.sh -c code                   # Claude Code (workspace-local)
./install.sh -c code --global          # Claude Code (global user config)
./install.sh -c kilo                   # Kilo Code
./install.sh -c opencode               # OpenCode (workspace-local)
./install.sh -c opencode --global      # OpenCode (global)
./install.sh -c goose                  # Goose
./install.sh -c all                    # all detected clients
```

**Windows (Command Prompt / PowerShell):**
```bat
cd mageNT
install.bat                            REM Claude Desktop
install.bat -c code                    REM Claude Code (workspace-local)
install.bat -c code --global           REM Claude Code (global user config)
install.bat -c kilo                    REM Kilo Code
install.bat -c opencode                REM OpenCode (workspace-local)
install.bat -c opencode --global       REM OpenCode (global)
install.bat -c goose                   REM Goose
install.bat -c all                     REM all detected clients
```

That's it. The installer handles everything — creates a venv, installs deps, configures your MCP client, runs tests.

Then just restart your client and try:
```
List the available agents
```

## Supported MCP Clients

| Client | `-c TYPE` | Config written | Notes |
|--------|-----------|----------------|-------|
| Claude Desktop | `desktop` | OS-specific `claude_desktop_config.json` | Restart required |
| Claude Code | `code` | `.mcp.json` (workspace) or `~/.claude.json` (global) | Use `--global` for user scope |
| Kilo Code | `kilo` | `.kilocode/mcp.json` | Workspace-local only |
| OpenCode | `opencode` | `opencode.json` / `~/.config/opencode/opencode.json` | Use `--global` for user scope |
| Goose | `goose` | `~/.config/goose/config.yaml` | Global only |
| pi.dev | manual | `~/.pi/agent/settings.json` + TS extension | No auto-config; see manual setup below |
| All above | `all` | All existing configs | Skips clients not yet installed |

### pi.dev manual setup

pi.dev uses a TypeScript extension API rather than standard MCP JSON. Add a minimal bridge extension:

```typescript
// ~/.pi/extensions/magent-bridge.ts
import { Extension } from "@pi-dev/sdk";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

export default class MagentBridge extends Extension {
  name = "magent";

  async activate() {
    const transport = new StdioClientTransport({
      command: "/path/to/mageNT/.venv/bin/python",
      args: ["/path/to/mageNT/server.py"],
    });
    const client = new Client({ name: "magent-bridge", version: "1.0.0" }, {});
    await client.connect(transport);
    this.registerMcpClient(client);
  }
}
```

Register it in `~/.pi/agent/settings.json`:
```json
{
  "extensions": ["~/.pi/extensions/magent-bridge.ts"]
}
```

### Updating

```bash
./install.sh --upgrade             # upgrade deps + merge new agents into config
./install.sh --upgrade -c code     # upgrade + reconfigure Claude Code MCP path
```

`--update` also works as an alias for `--upgrade`.

Re-running the installer when already on the latest version exits cleanly with "Nothing to do."
Use `-f` to force reinstall, or `--upgrade -c code` to reconfigure MCP client paths.

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

**Claude Code** — create `.mcp.json` in your workspace root (the directory you open in Claude Code):
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

Or for global user config (`~/.claude/mcp.json` / `%USERPROFILE%\.claude\mcp.json`), same format.

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

32 agents across different areas:

| What they do | Who's available |
|----------|--------|
| Business stuff | Business Analyst, Product Manager, Delivery Manager |
| Architecture & Design | System Architect, UI/UX Designer |
| Frontend | React, Next.js, Vue.js, Svelte devs |
| Backend | Node.js, Python, Java, Go, .NET, Rust, API, Integration specialists |
| Infrastructure | Database Admin, DevOps, Cloud Architect |
| Quality & Security | QA, Security Engineer, Performance Engineer, Automation QA |
| Mobile | Flutter, React Native, Android (Kotlin/Java), iOS (Swift/Obj-C), Mobile Dev |
| Other | Technical Writer, Debugging Expert, Full-Stack Dev |

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

**Full lifecycle:**
- `new_system` - Greenfield project, all phases (requirements → design → dev → test → docs → deployment → sign-off)
- `add_feature` - Add a feature to an existing system with full quality gates
- `bug_fix` - Diagnose, fix, and regression-test a bug
- `full_audit` - Comprehensive health check of an existing system

**Focused workflows:**
- `full_stack_web` - Full web app (frontend + backend + database)
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
- For Claude Code: `.mcp.json` must be in the workspace root (the folder you open), not inside `mageNT/`
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
├── install.sh          # Automated installer (Linux/macOS/Git Bash)
├── install.bat         # Automated installer (Windows CMD/PowerShell)
├── agents/             # The 32 agents
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
