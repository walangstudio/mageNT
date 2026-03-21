# mageNT

![version](https://img.shields.io/badge/version-0.4.0-blue)
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

Think of it like having 32 senior devs on standby, each with their own specialty. You can also run a full spec-driven development cycle — from requirements to parallel implementation to delivery audit — with a single tool call per step.

## Quick Start

Run the installer:

**Linux / macOS / Git Bash (Windows):**
```bash
cd mageNT
./install.sh                              # Claude Desktop
./install.sh -c claude                    # Claude Code (workspace-local)
./install.sh -c claude --global           # Claude Code (global user config)
./install.sh -c cursor                    # Cursor (workspace-local)
./install.sh -c cursor --global           # Cursor (global)
./install.sh -c windsurf                  # Windsurf (global only)
./install.sh -c vscode                    # VS Code (.vscode/mcp.json)
./install.sh -c gemini                    # Gemini CLI (workspace-local)
./install.sh -c gemini --global           # Gemini CLI (global)
./install.sh -c codex                     # OpenAI Codex CLI (workspace-local)
./install.sh -c codex --global            # OpenAI Codex CLI (global)
./install.sh -c zed                       # Zed (global)
./install.sh -c kilo                      # Kilo Code
./install.sh -c opencode                  # OpenCode (workspace-local)
./install.sh -c opencode --global         # OpenCode (global)
./install.sh -c goose                     # Goose
./install.sh -c all                       # all detected clients
```

**Windows (Command Prompt / PowerShell):**
```bat
cd mageNT
install.bat                               REM Claude Desktop
install.bat -c claude                     REM Claude Code (workspace-local)
install.bat -c claude --global            REM Claude Code (global user config)
install.bat -c cursor                     REM Cursor (workspace-local)
install.bat -c cursor --global            REM Cursor (global)
install.bat -c windsurf                   REM Windsurf (global only)
install.bat -c vscode                     REM VS Code (.vscode/mcp.json)
install.bat -c gemini                     REM Gemini CLI (workspace-local)
install.bat -c gemini --global            REM Gemini CLI (global)
install.bat -c codex                      REM OpenAI Codex CLI (workspace-local)
install.bat -c codex --global             REM OpenAI Codex CLI (global)
install.bat -c zed                        REM Zed (global)
install.bat -c kilo                       REM Kilo Code
install.bat -c opencode                   REM OpenCode (workspace-local)
install.bat -c opencode --global          REM OpenCode (global)
install.bat -c goose                      REM Goose
install.bat -c all                        REM all detected clients
```

That's it. The installer handles everything — creates a venv, installs deps, configures your MCP client, runs tests.

Then just restart your client and try:
```
List the available agents
```

## Supported MCP Clients

| Client | `-c TYPE` | Config written | Notes |
|--------|-----------|----------------|-------|
| Claude Desktop | `claudedesktop` | OS-specific `claude_desktop_config.json` | Restart required |
| Claude Code | `claude` | `.mcp.json` (workspace) or `~/.claude.json` (global) | Use `--global` for user scope |
| Cursor | `cursor` | `.cursor/mcp.json` or `~/.cursor/mcp.json` (global) | Use `--global` for global |
| Windsurf | `windsurf` | `~/.codeium/windsurf/mcp_config.json` | Global only |
| VS Code | `vscode` | `.vscode/mcp.json` | Workspace-local; global via VS Code settings UI |
| Gemini CLI | `gemini` | `.gemini/settings.json` or `~/.gemini/settings.json` (global) | Use `--global` for global |
| Codex CLI | `codex` | `.codex/config.toml` or `~/.codex/config.toml` (global) | TOML; use `--global` for global |
| Zed | `zed` | `~/.config/zed/settings.json` | Global only |
| Kilo Code | `kilo` | `.kilocode/mcp.json` | Workspace-local only |
| OpenCode | `opencode` | `opencode.json` / `~/.config/opencode/opencode.json` | Use `--global` for global |
| Goose | `goose` | `~/.config/goose/config.yaml` | Global only |
| pi.dev | `pidev` | n/a | Prints manual instructions; no auto-config |
| All above | `all` | All detected existing configs | Skips clients not yet installed |

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

### Installer Flags

```
  -c, --client TYPE   claudedesktop, claude, cursor, windsurf, vscode, gemini, codex,
                      zed, kilo, opencode, goose, pidev, all  (default: claudedesktop)
  -f, --force         Skip prompts, overwrite existing config
  -u, --uninstall     Remove from MCP client config
      --upgrade       Upgrade deps and reconfigure (alias: --update)
      --status        Show where this server is currently installed
      --global        Write to global config (claude, cursor, gemini, codex, opencode)
      --skip-test     Skip server validation
  -h, --help          Show this help
```

### Checking install status

```bash
./install.sh --status
```

Scans all known config paths and prints a table showing which clients have mageNT registered.

### Updating

Pull the latest source first (or re-download and extract), then:

```bash
./install.sh --upgrade                    # upgrade deps + merge new agents into config
./install.sh --upgrade -c all             # also reconfigure all clients
./install.sh --upgrade -c claude          # upgrade + reconfigure Claude Code MCP path
```

`--update` is an alias for `--upgrade`.

Re-running the installer when already on the latest version exits cleanly with "Nothing to do."
Use `-f` to force reinstall, or `--upgrade -c claude` to reconfigure MCP client paths.

## Manual Setup

If you want to do it yourself:

```bash
cd mageNT
pip install -r requirements.txt
python server.py  # test it works, then Ctrl+C
```

Now add mageNT to your MCP client config (use absolute paths):

### Claude Desktop

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "magent": {
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

On Windows: `"command": "C:\\path\\to\\mageNT\\.venv\\Scripts\\python.exe"`

### Claude Code

Workspace-local (`.mcp.json` in your project root):
```json
{
  "mcpServers": {
    "magent": {
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

Global user scope:
```bash
claude mcp add --scope user magent -- /absolute/path/to/mageNT/.venv/bin/python /absolute/path/to/mageNT/server.py
```

### Cursor

`.cursor/mcp.json` (workspace) or `~/.cursor/mcp.json` (global):
```json
{
  "mcpServers": {
    "magent": {
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

### Windsurf

`~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "magent": {
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

### VS Code

`.vscode/mcp.json` in your workspace root (note: VS Code uses `servers`, not `mcpServers`):
```json
{
  "servers": {
    "magent": {
      "type": "stdio",
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

For user-level config, add via VS Code Settings UI under `mcp.servers`.

### Gemini CLI

`.gemini/settings.json` (workspace) or `~/.gemini/settings.json` (global):
```json
{
  "mcpServers": {
    "magent": {
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

### OpenAI Codex CLI

`.codex/config.toml` (workspace) or `~/.codex/config.toml` (global):
```toml
[mcp_servers.magent]
command = "/absolute/path/to/mageNT/.venv/bin/python /absolute/path/to/mageNT/server.py"
startup_timeout_sec = 30
tool_timeout_sec = 300
enabled = true
```

### Zed

`~/.config/zed/settings.json`:
```json
{
  "context_servers": {
    "magent": {
      "command": {
        "path": "/absolute/path/to/mageNT/.venv/bin/python",
        "args": ["/absolute/path/to/mageNT/server.py"],
        "env": {}
      }
    }
  }
}
```

### Kilo Code

`.kilocode/mcp.json` in your workspace root:
```json
{
  "mcpServers": {
    "magent": {
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

### OpenCode

`opencode.json` (workspace) or `~/.config/opencode/opencode.json` (global):
```json
{
  "mcp": {
    "magent": {
      "command": "/absolute/path/to/mageNT/.venv/bin/python",
      "args": ["/absolute/path/to/mageNT/server.py"]
    }
  }
}
```

### Goose

`~/.config/goose/config.yaml`:
```yaml
extensions:
  magent:
    type: stdio
    cmd: /absolute/path/to/mageNT/.venv/bin/python
    args:
      - /absolute/path/to/mageNT/server.py
    enabled: true
```

### pi.dev

pi.dev does not support MCP servers natively. It uses TypeScript extensions instead. See the existing pi.dev bridge example in the **Supported MCP Clients** section above.

On Windows, use `C:\absolute\path\to\mageNT\.venv\Scripts\python.exe` for the command. Restart the client after editing any config.

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

33 agents across different areas:

| What they do | Who's available |
|----------|--------|
| Business stuff | Business Analyst, Product Manager, Delivery Manager |
| Architecture & Design | System Architect, UI/UX Designer |
| Frontend | React, Next.js, Vue.js, Svelte devs |
| Backend | Node.js, Python, Java, Go, .NET, Rust, API, Integration specialists |
| Infrastructure | Database Admin, DevOps, Cloud Architect |
| Quality & Security | QA Engineer, SDET, Automation QA, Security Engineer, Performance Engineer |
| Mobile | Flutter, React Native, Android (Kotlin/Java), iOS (Swift/Obj-C), Mobile Dev |
| Other | Technical Writer, Debugging Expert, Full-Stack Dev |

## Spec-Driven Development

A structured flow for building new projects or features from scratch:

```
create_spec → create_arch_spec → run_parallel_agents → audit_spec
```

**1. Create a requirements spec**
```
Create a spec for a blog platform with user auth, post CRUD, and comments
```
Returns a `spec_id`. Spec stored to `specs/{spec_id}/spec.md`.

**2. Generate architecture**
```
Create an arch spec for spec_id: blog-platform-a1b2c3d4
```
System Architect produces tech stack, component design, API contracts, and data models.

**3. Run agents in parallel**
```
Run parallel agents for spec_id: blog-platform-a1b2c3d4, phase: build
```
Agents are auto-selected from the arch spec using keyword matching. All run concurrently. Results are saved automatically.

```
Run parallel agents for spec_id: blog-platform-a1b2c3d4, phase: qa
```
QA Engineer and Security Engineer review the architecture for risks.

**4. Audit against spec**
```
Audit spec: blog-platform-a1b2c3d4
```
Delivery Manager checks every acceptance checklist item — `MET`, `PARTIAL`, or `MISSING` — and returns a go/no-go decision.

When starting any workflow or spec, mageNT will ask if you'd like to follow a **TDD cycle** instead. It's optional.

## Skill Tools

10 skills are available as direct MCP tools alongside the agent consultation tools:

| Tool | What it does |
|------|-------------|
| `skill_debug_code` | Structured debugging guidance |
| `skill_analyze_error` | Error/exception root cause analysis |
| `skill_scaffold_react` | React + Vite project scaffold |
| `skill_scaffold_nextjs` | Next.js App Router scaffold |
| `skill_scaffold_fastapi` | FastAPI + Pydantic scaffold |
| `skill_scaffold_express` | Express.js scaffold |
| `skill_security_scan` | OWASP-aligned security checklist |
| `skill_generate_tests` | Test generation guidance |
| `skill_run_tests` | Test runner guidance |
| `skill_check_versions` | Dependency version and compatibility check |

Skills are also auto-invoked during `run_parallel_agents` based on the arch spec content.

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
- `tdd` - Test-driven development (red → green → refactor cycle)

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
├── agents/             # The 33 agents
├── skills/             # Reusable skills (scaffold, test, debug, security, etc.)
├── rules/              # Code quality rules
├── hooks/              # Automation hooks
├── workflows/          # Multi-agent workflow templates
├── specs/              # Spec-driven development output (created at runtime)
├── utils/              # Orchestration, spec store, skill registry, prompt builders
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
