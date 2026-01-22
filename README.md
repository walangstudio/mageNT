# mageNT

A local MCP server that gives Claude access to a team of specialized development agents. No API keys needed - works with your existing Claude Pro subscription.

## What is this?

mageNT adds domain-specific expertise to Claude through the Model Context Protocol. Instead of Claude being a generalist, you can ask it to consult specialists:

- Need requirements? Talk to the Business Analyst
- Building a React app? Consult the React Developer
- Setting up an API? Ask the Node.js Backend Developer

Each agent has deep knowledge of their domain - best practices, common patterns, and practical guidance.

## Installation

```bash
cd mageNT
pip install -r requirements.txt
```

Test it works:
```bash
python server.py
```

You should see agents loading. Press Ctrl+C to stop.

## Connect to Claude Desktop

Add mageNT to your Claude Desktop config:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "magent": {
      "command": "python",
      "args": ["C:\\path\\to\\mageNT\\server.py"]
    }
  }
}
```

Use your actual path. Double backslashes on Windows, forward slashes on Mac/Linux.

Restart Claude Desktop completely (quit, not just close the window).

## Usage

Once connected, just ask Claude naturally:

```
List the available agents
```

```
I need to build a user authentication system - can you help?
```

```
Start a full_stack_web workflow for a task management app
```

Claude will automatically use the right agents for the job.

## Available Agents

**24 agents** across different specializations:

| Category | Agents |
|----------|--------|
| Business | Business Analyst, Product Manager |
| Design | UI/UX Designer, System Architect |
| Frontend | React, Next.js, Vue.js developers |
| Backend | Node.js, Python, Java, Go, .NET developers |
| Data | Database Administrator |
| DevOps | DevOps Engineer, Cloud Architect |
| Quality | QA Engineer, Security Engineer, Performance Engineer |
| Support | Technical Writer, Debugging Expert |

## Code Quality Features

mageNT includes a **Rules Engine** with 20 built-in rules:

- Security checks (hardcoded secrets, SQL injection, XSS)
- Code style validation
- Performance patterns (N+1 queries, sync in async)
- Git hygiene (commit messages, .gitignore)

And a **Hooks System** for automation:

- Pre-commit validation
- Code edit checks
- Security scanning

Use them through Claude:
```
Check this code for security issues: [paste code]
```

## Configuration

Edit `config.yaml` to customize:

```yaml
agents:
  react_developer:
    enabled: true
    expertise_level: "senior"  # junior, mid, senior, principal
    specialization: "React 18, TypeScript, Tailwind"
```

## Workflows

Pre-built multi-agent workflows:

- `full_stack_web` - Requirements, frontend, backend, database, testing
- `api_service` - API design and implementation
- `frontend_app` - UI/UX focused workflow

Start one with:
```
Start the full_stack_web workflow for [your project]
```

## Adding Custom Agents

Create a new file in `agents/`:

```python
from agents.base import BaseAgent

class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "my_agent"

    @property
    def role(self) -> str:
        return "My Specialist Role"

    # ... implement other required properties
```

Register it in `server.py` and add to `config.yaml`.

## Troubleshooting

**Tools don't appear in Claude:**
1. Check the path in your config is correct and absolute
2. Make sure you restarted Claude Desktop completely
3. Try running `python server.py` to see if there are errors

**Python not found:**
Use the full path to Python in your config, or add Python to your PATH.

**Import errors:**
Make sure you're in the mageNT directory and dependencies are installed:
```bash
pip install -r requirements.txt
```

## Project Structure

```
mageNT/
├── server.py           # MCP server entry point
├── config.yaml         # Your configuration
├── agents/             # Agent implementations
├── rules/              # Code quality rules
├── hooks/              # Automation hooks
├── workflows/          # Workflow templates
└── tests/              # Test suite
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Requirements

- Python 3.10+
- Claude Pro subscription
- Claude Desktop or Claude Code

## License

MIT
