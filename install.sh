#!/usr/bin/env bash
set -euo pipefail

# ── Config ──────────────────────────────────────────────
MARKER_FILE=".magent-installed"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAGENT_DIR="$SCRIPT_DIR"

# ── Defaults ────────────────────────────────────────────
FORCE=false
UNINSTALL=false
UPDATE=false
CLIENT="desktop"
SKIP_TEST=false

# ── Parse flags ─────────────────────────────────────────
show_help() {
    cat <<EOF
Usage: ./install.sh [options]

Options:
  -c, --client TYPE   MCP client: desktop, code, both (default: desktop)
  -f, --force         Skip prompts, overwrite existing config
  -u, --uninstall     Remove mageNT from MCP client config
      --update        Upgrade deps and merge new agents into existing config.yaml
      --skip-test     Skip test_server.py validation
  -h, --help          Show this help

Examples:
  ./install.sh                    Install for Claude Desktop
  ./install.sh -c code            Install for Claude Code
  ./install.sh -c both            Install for both
  ./install.sh --update           Update deps and merge new agents into config
  ./install.sh -u                 Uninstall
  ./install.sh -f --skip-test     Force install, skip tests
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)     FORCE=true; shift ;;
        -u|--uninstall) UNINSTALL=true; shift ;;
        --update)       UPDATE=true; shift ;;
        -c|--client)    CLIENT="$2"; shift 2 ;;
        --skip-test)    SKIP_TEST=true; shift ;;
        -h|--help)      show_help ;;
        *) echo "Unknown option: $1"; show_help ;;
    esac
done

# ── Helpers ─────────────────────────────────────────────
info()  { echo "  $*"; }
ok()    { echo "  OK: $*"; }
err()   { echo "  ERROR: $*" >&2; }
die()   { err "$*"; exit 1; }

get_version() {
    grep '__version__' "$MAGENT_DIR/__init__.py" | sed 's/.*"\(.*\)".*/\1/'
}

# ── Python detection ────────────────────────────────────
find_python() {
    for cmd in python3 python py; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || continue
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
                command -v "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

# ── Venv python path ───────────────────────────────────
get_venv_python() {
    # Check both layouts (Windows creates Scripts/, some setups create bin/)
    if [[ -f "$MAGENT_DIR/.venv/Scripts/python.exe" ]]; then
        echo "$MAGENT_DIR/.venv/Scripts/python.exe"
    elif [[ -f "$MAGENT_DIR/.venv/bin/python" ]]; then
        echo "$MAGENT_DIR/.venv/bin/python"
    elif [[ -f "$MAGENT_DIR/.venv/bin/python3.exe" ]]; then
        echo "$MAGENT_DIR/.venv/bin/python3.exe"
    elif [[ -f "$MAGENT_DIR/.venv/bin/python3" ]]; then
        echo "$MAGENT_DIR/.venv/bin/python3"
    else
        return 1
    fi
}

# ── MCP config paths ───────────────────────────────────
get_desktop_config_path() {
    case "$(uname -s)" in
        Darwin)
            echo "$HOME/Library/Application Support/Claude/claude_desktop_config.json" ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                local appdata
                appdata=$(cmd.exe /c "echo %APPDATA%" 2>/dev/null | tr -d '\r')
                echo "$appdata/Claude/claude_desktop_config.json"
            else
                echo "$HOME/.config/Claude/claude_desktop_config.json"
            fi ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "$APPDATA/Claude/claude_desktop_config.json" ;;
        *)
            echo "$HOME/.config/Claude/claude_desktop_config.json" ;;
    esac
}

get_code_config_path() {
    echo "$MAGENT_DIR/.mcp.json"
}

# ── JSON operations (uses Python, no jq needed) ────────
merge_mcp_config() {
    local config_path="$1"
    local server_py="$2"

    if [[ -f "$config_path" ]]; then
        cp "$config_path" "${config_path}.backup.$(date +%Y%m%d%H%M%S)"
        info "Backed up existing config"
    fi

    "$venv_python" -c "
import json, sys, os

config_path = os.path.abspath(sys.argv[1])
# Use sys.executable for the real native Python path
python_path = sys.executable
server_py = os.path.abspath(sys.argv[2])

try:
    with open(config_path) as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}

config.setdefault('mcpServers', {})
config['mcpServers']['magent'] = {
    'command': python_path,
    'args': [server_py]
}

os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$config_path" "$server_py"
}

remove_mcp_config() {
    local config_path="$1"
    local venv_python="$2"

    [[ -f "$config_path" ]] || return 0

    cp "$config_path" "${config_path}.backup.$(date +%Y%m%d%H%M%S)"

    "$venv_python" -c "
import json, sys

config_path = sys.argv[1]
try:
    with open(config_path) as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(0)

servers = config.get('mcpServers', {})
if 'magent' in servers:
    del servers['magent']
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print('  Removed magent from config')
else:
    print('  magent not found in config')
" "$config_path"
}

# ── Config migration (merge new keys without touching existing) ────────────
migrate_config() {
    local venv_python="$1"
    local example="$MAGENT_DIR/config.example.yaml"
    local config="$MAGENT_DIR/config.yaml"

    [[ -f "$example" ]] || { info "No config.example.yaml found, skipping migration"; return 0; }
    [[ -f "$config"  ]] || { info "No config.yaml found, skipping migration"; return 0; }

    "$venv_python" -c "
import sys

try:
    import yaml
except ImportError:
    print('  PyYAML not available, skipping config migration')
    sys.exit(0)

example_path = sys.argv[1]
config_path  = sys.argv[2]

with open(example_path) as f:
    example = yaml.safe_load(f)

with open(config_path) as f:
    config = yaml.safe_load(f) or {}

added_agents    = []
added_workflows = []

# Merge agents: add any key from example that is missing in config
example_agents = example.get('agents', {}) or {}
config_agents  = config.setdefault('agents', {})
for name, block in example_agents.items():
    if name not in config_agents:
        # New agents arrive disabled so they don't change existing behaviour
        new_block = dict(block)
        new_block['enabled'] = False
        config_agents[name] = new_block
        added_agents.append(name)

# Merge workflows: add any key from example that is missing in config
example_workflows = example.get('workflows', {}) or {}
config_workflows  = config.setdefault('workflows', {})
for name, block in example_workflows.items():
    if name not in config_workflows:
        config_workflows[name] = block
        added_workflows.append(name)

with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

if added_agents:
    print('  New agents added (disabled): ' + ', '.join(added_agents))
if added_workflows:
    print('  New workflows added: ' + ', '.join(added_workflows))
if not added_agents and not added_workflows:
    print('  config.yaml already up to date')
" "$example" "$config"
}

# ── Configure client ────────────────────────────────────
configure_client() {
    local client_type="$1"
    local venv_python="$2"
    local server_py="$3"
    local config_path

    if [[ "$client_type" == "desktop" ]]; then
        config_path=$(get_desktop_config_path)
        info "Client: Claude Desktop"
    else
        config_path=$(get_code_config_path)
        info "Client: Claude Code"
    fi

    info "Config: $config_path"

    if [[ "$UNINSTALL" == true ]]; then
        remove_mcp_config "$config_path" "$venv_python"
    else
        # Check if already configured
        if [[ -f "$config_path" ]] && [[ "$FORCE" != true ]]; then
            if "$venv_python" -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        c = json.load(f)
    if 'magent' in c.get('mcpServers', {}):
        sys.exit(0)
except: pass
sys.exit(1)
" "$config_path" 2>/dev/null; then
                read -rp "  magent already in config. Overwrite? [y/N] " answer
                [[ "$answer" =~ ^[Yy]$ ]] || { info "Skipped"; return 0; }
            fi
        fi

        merge_mcp_config "$config_path" "$server_py"
        ok "MCP config updated"
    fi
}

# ── Banner ──────────────────────────────────────────────
VERSION=$(get_version)
echo ""
echo "  mageNT v${VERSION}"
if [[ "$UNINSTALL" == true ]]; then
    echo "  Mode: uninstall"
elif [[ "$UPDATE" == true ]]; then
    echo "  Mode: update"
else
    echo "  Mode: install (client: $CLIENT)"
fi
echo "  ─────────────────────────────"
echo ""

# ── Uninstall path ──────────────────────────────────────
if [[ "$UNINSTALL" == true ]]; then
    VENV_PYTHON=$(get_venv_python)

    if [[ ! -f "$VENV_PYTHON" ]]; then
        # Fall back to system python for JSON ops
        VENV_PYTHON=$(find_python) || die "Python not found"
    fi

    if [[ "$CLIENT" == "both" ]]; then
        configure_client "desktop" "$VENV_PYTHON" ""
        configure_client "code" "$VENV_PYTHON" ""
    else
        configure_client "$CLIENT" "$VENV_PYTHON" ""
    fi

    rm -f "$MAGENT_DIR/$MARKER_FILE"
    info "Removed version marker"

    if [[ -d "$MAGENT_DIR/.venv" ]]; then
        if [[ "$FORCE" == true ]]; then
            rm -rf "$MAGENT_DIR/.venv"
            info "Removed .venv"
        else
            read -rp "  Remove virtual environment (.venv)? [y/N] " answer
            if [[ "$answer" =~ ^[Yy]$ ]]; then
                rm -rf "$MAGENT_DIR/.venv"
                info "Removed .venv"
            else
                info "Kept .venv"
            fi
        fi
    fi

    echo ""
    echo "  mageNT uninstalled."
    echo ""
    exit 0
fi

# ── Update path ─────────────────────────────────────────
if [[ "$UPDATE" == true ]]; then
    # Need Python to update deps — use existing venv if available
    VENV_PYTHON=$(get_venv_python 2>/dev/null) || true

    if [[ -z "$VENV_PYTHON" || ! -f "$VENV_PYTHON" ]]; then
        SYSTEM_PYTHON=$(find_python) || die "Python 3.10+ is required"
        info "No venv found — creating one first..."
        "$SYSTEM_PYTHON" -m venv "$MAGENT_DIR/.venv"
        VENV_PYTHON=$(get_venv_python)
    fi

    # 1. Upgrade dependencies
    info "Upgrading dependencies..."
    "$VENV_PYTHON" -m pip install -r "$MAGENT_DIR/requirements.txt" --upgrade --quiet 2>&1 | tail -1 || true
    ok "Dependencies upgraded"
    echo ""

    # 2. Merge new agents/workflows into existing config.yaml
    info "Migrating config.yaml..."
    migrate_config "$VENV_PYTHON"
    echo ""

    # 3. Run tests
    if [[ "$SKIP_TEST" != true ]]; then
        info "Validating installation..."
        if "$VENV_PYTHON" "$MAGENT_DIR/test_server.py" > /dev/null 2>&1; then
            ok "All tests passed"
        else
            err "Validation failed. Run 'python test_server.py' for details."
        fi
        echo ""
    fi

    # 4. Update marker
    echo "$VERSION" > "$MAGENT_DIR/$MARKER_FILE"
    ok "Marker updated to v${VERSION}"

    echo "  ─────────────────────────────"
    echo "  mageNT updated to v${VERSION}!"
    echo ""
    echo "  Restart Claude (quit fully, then reopen) to load new agents."
    echo ""
    exit 0
fi

# ── Install path ─────────────────────────────────────────

# 1. Find Python
info "Checking Python..."
SYSTEM_PYTHON=$(find_python) || die "Python 3.10+ is required. Install from https://python.org"
PY_VER=$("$SYSTEM_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
ok "Python $PY_VER"
echo ""

# 2. Setup venv
info "Setting up virtual environment..."
if [[ -d "$MAGENT_DIR/.venv" ]] && [[ "$FORCE" != true ]]; then
    ok "Using existing .venv"
else
    "$SYSTEM_PYTHON" -m venv "$MAGENT_DIR/.venv"
    ok "Created .venv"
fi

VENV_PYTHON=$(get_venv_python)
[[ -f "$VENV_PYTHON" ]] || die "venv python not found at $VENV_PYTHON"
echo ""

# 3. Install deps
info "Installing dependencies..."
"$VENV_PYTHON" -m pip install -r "$MAGENT_DIR/requirements.txt" --quiet 2>&1 | tail -1 || true
ok "Dependencies installed"
echo ""

# 4. Init config
info "Checking configuration..."
if [[ ! -f "$MAGENT_DIR/config.yaml" ]]; then
    cp "$MAGENT_DIR/config.example.yaml" "$MAGENT_DIR/config.yaml"
    ok "Created config.yaml from template"
else
    ok "config.yaml exists"
fi
echo ""

# 5. Run tests
if [[ "$SKIP_TEST" != true ]]; then
    info "Validating installation..."
    if "$VENV_PYTHON" "$MAGENT_DIR/test_server.py" > /dev/null 2>&1; then
        ok "All tests passed"
    else
        err "Validation failed. Run 'python test_server.py' for details."
        err "Use --skip-test to skip this step."
        exit 1
    fi
    echo ""
fi

# 6. Configure MCP client
info "Configuring MCP client..."
SERVER_PY="$MAGENT_DIR/server.py"

if [[ "$CLIENT" == "both" ]]; then
    configure_client "desktop" "$VENV_PYTHON" "$SERVER_PY"
    echo ""
    configure_client "code" "$VENV_PYTHON" "$SERVER_PY"
else
    configure_client "$CLIENT" "$VENV_PYTHON" "$SERVER_PY"
fi
echo ""

# 7. Write marker
echo "$VERSION" > "$MAGENT_DIR/$MARKER_FILE"

# ── Done ────────────────────────────────────────────────
echo "  ─────────────────────────────"
echo "  mageNT installed successfully!"
echo ""
echo "  Next steps:"
if [[ "$CLIENT" == "code" ]]; then
    echo "  1. Open this directory in Claude Code"
    echo "  2. Try: \"List the available agents\""
else
    echo "  1. Restart Claude Desktop (quit fully, then reopen)"
    echo "  2. Try: \"List the available agents\""
fi
echo ""
