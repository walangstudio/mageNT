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
GLOBAL_CONFIG=false
CLIENT_EXPLICIT=false

# ── Parse flags ─────────────────────────────────────────
show_help() {
    cat <<EOF
Usage: ./install.sh [options]

Options:
  -c, --client TYPE   MCP client: desktop, code, kilo, opencode, goose, all (default: desktop)
  -f, --force         Skip prompts, overwrite existing config
  -u, --uninstall     Remove mageNT from MCP client config
      --upgrade       Upgrade deps and merge new agents into existing config.yaml
      --update        Alias for --upgrade
      --global        Write to global config path (applies to: code, opencode, all)
                      Default (no --global): writes to parent workspace dir
      --skip-test     Skip test_server.py validation
  -h, --help          Show this help

Examples:
  ./install.sh                      Install for Claude Desktop
  ./install.sh -c code              Install for Claude Code (workspace-local)
  ./install.sh -c code --global     Install for Claude Code (global config)
  ./install.sh -c kilo              Install for Kilo Code (workspace-local)
  ./install.sh -c opencode          Install for OpenCode (workspace-local)
  ./install.sh -c opencode --global Install for OpenCode (global)
  ./install.sh -c goose             Install for Goose
  ./install.sh -c all               Install for all detected clients
  ./install.sh --upgrade            Upgrade deps & config
  ./install.sh --upgrade -c code    Upgrade + reconfigure Claude Code MCP path
  ./install.sh -u                   Uninstall
  ./install.sh -u -c all            Uninstall from all client configs
  ./install.sh -f --skip-test       Force install, skip tests
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)          FORCE=true; shift ;;
        -u|--uninstall)      UNINSTALL=true; shift ;;
        --update|--upgrade)  UPDATE=true; shift ;;
        -c|--client)         CLIENT="$2"; CLIENT_EXPLICIT=true; shift 2 ;;
        --global)            GLOBAL_CONFIG=true; shift ;;
        --skip-test)         SKIP_TEST=true; shift ;;
        -h|--help)           show_help ;;
        *) echo "Unknown option: $1"; show_help ;;
    esac
done

# ── Helpers ─────────────────────────────────────────────
info()  { echo "  $*"; }
ok()    { echo "  OK: $*"; }
err()   { echo "  ERROR: $*" >&2; }
die()   { err "$*"; exit 1; }

if [[ "$GLOBAL_CONFIG" == true ]]; then
    case "$CLIENT" in
        code|both|opencode|all) ;;
        *) die "--global is only valid with -c code, opencode, both, or all" ;;
    esac
fi

get_version() {
    grep '__version__' "$MAGENT_DIR/__init__.py" | sed 's/.*"\(.*\)".*/\1/'
}

get_installed_version() {
    local marker="$MAGENT_DIR/$MARKER_FILE"
    [[ -f "$marker" ]] && cat "$marker" || echo ""
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

# ── Venv python path ────────────────────────────────────
get_venv_python() {
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

# ── MCP config paths ─────────────────────────────────────
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
    echo "$(dirname "$MAGENT_DIR")/.mcp.json"
}

get_global_code_config_paths() {
    echo "$HOME/.claude.json"
}

get_kilo_config_path() {
    echo "$(dirname "$MAGENT_DIR")/.kilocode/mcp.json"
}

get_opencode_config_path() {
    if [[ "$GLOBAL_CONFIG" == true ]]; then
        echo "$HOME/.config/opencode/opencode.json"
    else
        echo "$(dirname "$MAGENT_DIR")/opencode.json"
    fi
}

get_goose_config_path() {
    echo "$HOME/.config/goose/config.yaml"
}

# ── JSON/YAML operations (uses Python, no jq needed) ─────
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

merge_opencode_config() {
    local config_path="$1"
    local _venv_python="$2"
    shift 2
    local extra_args=("$@")

    if [[ -f "$config_path" ]]; then
        cp "$config_path" "${config_path}.backup.$(date +%Y%m%d%H%M%S)"
        info "Backed up existing config"
    fi

    "$_venv_python" -c "
import json, sys, os

config_path = os.path.abspath(sys.argv[1])
python_path = sys.executable
extra_args = sys.argv[2:]

try:
    with open(config_path) as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}

config.setdefault('mcp', {})
config['mcp']['magent'] = {'type': 'local', 'command': [python_path] + extra_args}

d = os.path.dirname(config_path)
if d:
    os.makedirs(d, exist_ok=True)
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$config_path" "${extra_args[@]}"
}

remove_opencode_config() {
    local config_path="$1"
    local _venv_python="$2"

    [[ -f "$config_path" ]] || return 0
    cp "$config_path" "${config_path}.backup.$(date +%Y%m%d%H%M%S)"

    "$_venv_python" -c "
import json, sys, os

config_path = sys.argv[1]
try:
    with open(config_path) as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(0)

mcp = config.get('mcp', {})
if 'magent' in mcp:
    del mcp['magent']
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print('  Removed magent from config')
else:
    print('  magent not found in config')
" "$config_path"
}

merge_goose_config() {
    local config_path="$1"
    local _venv_python="$2"
    shift 2
    local extra_args=("$@")

    if [[ -f "$config_path" ]]; then
        cp "$config_path" "${config_path}.backup.$(date +%Y%m%d%H%M%S)"
        info "Backed up existing config"
    fi

    "$_venv_python" -c "
import sys, os

try:
    import yaml
except ImportError:
    python_path = sys.executable
    extra_args = sys.argv[2:]
    print('  PyYAML not available. Add manually to ~/.config/goose/config.yaml:')
    print('  extensions:')
    print('    magent:')
    print('      name: magent')
    print('      type: stdio')
    print('      cmd: ' + python_path)
    print('      args: ' + str(extra_args))
    print('      enabled: true')
    sys.exit(0)

config_path = os.path.abspath(sys.argv[1])
python_path = sys.executable
extra_args = sys.argv[2:]

try:
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
except FileNotFoundError:
    config = {}

config.setdefault('extensions', {})
config['extensions']['magent'] = {
    'name': 'magent',
    'type': 'stdio',
    'cmd': python_path,
    'args': extra_args,
    'enabled': True,
}

d = os.path.dirname(config_path)
if d:
    os.makedirs(d, exist_ok=True)
with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
" "$config_path" "${extra_args[@]}"
}

remove_goose_config() {
    local config_path="$1"
    local _venv_python="$2"

    [[ -f "$config_path" ]] || return 0
    cp "$config_path" "${config_path}.backup.$(date +%Y%m%d%H%M%S)"

    "$_venv_python" -c "
import sys, os

try:
    import yaml
except ImportError:
    print('  PyYAML not available, cannot auto-remove from Goose config')
    sys.exit(0)

config_path = sys.argv[1]
try:
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
except FileNotFoundError:
    sys.exit(0)

ext = config.get('extensions', {})
if 'magent' in ext:
    del ext['magent']
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print('  Removed magent from config')
else:
    print('  magent not found in config')
" "$config_path"
}

# ── Config migration ─────────────────────────────────────
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

example_agents = example.get('agents', {}) or {}
config_agents  = config.setdefault('agents', {})
for name, block in example_agents.items():
    if name not in config_agents:
        new_block = dict(block)
        new_block['enabled'] = False
        config_agents[name] = new_block
        added_agents.append(name)

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

# ── Configure client ─────────────────────────────────────
_configure_one_path() {
    local config_path="$1"
    local venv_python="$2"
    local server_py="$3"

    info "Config: $config_path"

    if [[ "$UNINSTALL" == true ]]; then
        remove_mcp_config "$config_path" "$venv_python"
    else
        if [[ -f "$config_path" ]] && [[ "$FORCE" != true ]]; then
            current_cmd=$("$venv_python" -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        c = json.load(f)
    entry = c.get('mcpServers', {}).get('magent', {})
    print(entry.get('command', ''))
except: pass
" "$config_path" 2>/dev/null) || true

            if [[ -n "$current_cmd" && "$current_cmd" == "$venv_python" ]]; then
                info "MCP config already up to date"
                return 0
            elif [[ -n "$current_cmd" ]]; then
                info "Updating MCP config (python path changed)"
            fi
        fi

        merge_mcp_config "$config_path" "$server_py"
        ok "MCP config updated"
    fi
}

configure_client() {
    local client_type="$1"
    local venv_python="$2"
    local server_py="$3"

    case "$client_type" in
        desktop)
            info "Client: Claude Desktop"
            _configure_one_path "$(get_desktop_config_path)" "$venv_python" "$server_py"
            ;;
        code)
            if [[ "$GLOBAL_CONFIG" == true ]]; then
                info "Client: Claude Code (global)"
                while IFS= read -r config_path; do
                    _configure_one_path "$config_path" "$venv_python" "$server_py"
                done < <(get_global_code_config_paths)
            else
                info "Client: Claude Code (workspace)"
                _configure_one_path "$(get_code_config_path)" "$venv_python" "$server_py"
            fi
            ;;
        kilo)
            info "Client: Kilo Code"
            _configure_one_path "$(get_kilo_config_path)" "$venv_python" "$server_py"
            ;;
        opencode)
            info "Client: OpenCode"
            local opencode_path
            opencode_path="$(get_opencode_config_path)"
            info "Config: $opencode_path"
            if [[ "$UNINSTALL" == true ]]; then
                remove_opencode_config "$opencode_path" "$venv_python"
            else
                merge_opencode_config "$opencode_path" "$venv_python" "$server_py"
                ok "MCP config updated"
            fi
            ;;
        goose)
            info "Client: Goose"
            local goose_path
            goose_path="$(get_goose_config_path)"
            info "Config: $goose_path"
            if [[ "$UNINSTALL" == true ]]; then
                remove_goose_config "$goose_path" "$venv_python"
            else
                merge_goose_config "$goose_path" "$venv_python" "$server_py"
                ok "MCP config updated"
            fi
            ;;
        both)
            configure_client "desktop" "$venv_python" "$server_py"
            echo ""
            configure_client "code" "$venv_python" "$server_py"
            ;;
        all)
            configure_client "desktop" "$venv_python" "$server_py"
            echo ""
            configure_client "code" "$venv_python" "$server_py"
            local _kilo_path _opencode_ws _opencode_global _goose_path
            _kilo_path="$(get_kilo_config_path)"
            _opencode_ws="$(dirname "$MAGENT_DIR")/opencode.json"
            _opencode_global="$HOME/.config/opencode/opencode.json"
            _goose_path="$(get_goose_config_path)"
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_kilo_path" ]]; then
                echo ""
                configure_client "kilo" "$venv_python" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_opencode_ws" ]] || [[ -f "$_opencode_global" ]]; then
                echo ""
                configure_client "opencode" "$venv_python" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_goose_path" ]]; then
                echo ""
                configure_client "goose" "$venv_python" "$server_py"
            fi
            ;;
        *)
            die "Unknown client type: $client_type. Valid: desktop, code, kilo, opencode, goose, both, all"
            ;;
    esac
}

# ── Banner ───────────────────────────────────────────────
VERSION=$(get_version)
INSTALLED_VERSION=$(get_installed_version)
echo ""
echo "  mageNT v${VERSION}"
if [[ "$UPDATE" == true && -n "$INSTALLED_VERSION" && "$INSTALLED_VERSION" != "$VERSION" ]]; then
    echo "  Upgrading from v${INSTALLED_VERSION}"
fi
if [[ "$UNINSTALL" == true ]]; then
    echo "  Mode: uninstall"
elif [[ "$UPDATE" == true ]]; then
    echo "  Mode: update"
else
    echo "  Mode: install (client: $CLIENT)"
fi
echo "  ─────────────────────────────"
echo ""

# ── Uninstall path ───────────────────────────────────────
if [[ "$UNINSTALL" == true ]]; then
    VENV_PYTHON=$(get_venv_python 2>/dev/null) || true

    if [[ -z "$VENV_PYTHON" || ! -f "$VENV_PYTHON" ]]; then
        VENV_PYTHON=$(find_python) || die "Python not found"
    fi

    configure_client "$CLIENT" "$VENV_PYTHON" ""

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

# ── Update path ──────────────────────────────────────────
if [[ "$UPDATE" == true ]]; then
    if [[ -n "$INSTALLED_VERSION" ]]; then
        if [[ "$INSTALLED_VERSION" == "$VERSION" ]]; then
            if [[ "$CLIENT_EXPLICIT" != true && "$FORCE" != true ]]; then
                info "Already at v${VERSION}. Nothing to do."
                info "Use --upgrade -c code|all to also reconfigure MCP client."
                echo ""
                exit 0
            fi
            info "Already at v${VERSION} — reconfiguring MCP client"
        else
            info "Upgrading v${INSTALLED_VERSION} → v${VERSION}"
        fi
    else
        info "No marker found — running full update"
    fi
    echo ""

    VENV_PYTHON=$(get_venv_python 2>/dev/null) || true

    if [[ -z "$VENV_PYTHON" || ! -f "$VENV_PYTHON" ]]; then
        SYSTEM_PYTHON=$(find_python) || die "Python 3.10+ is required"
        info "No venv found — creating one first..."
        "$SYSTEM_PYTHON" -m venv "$MAGENT_DIR/.venv"
        VENV_PYTHON=$(get_venv_python)
    fi

    info "Upgrading dependencies..."
    "$VENV_PYTHON" -m pip install -r "$MAGENT_DIR/requirements.txt" --upgrade --quiet 2>&1 | tail -1 || true
    ok "Dependencies upgraded"
    echo ""

    info "Migrating config.yaml..."
    migrate_config "$VENV_PYTHON"
    echo ""

    if [[ "$CLIENT_EXPLICIT" == true ]]; then
        info "Reconfiguring MCP client ($CLIENT)..."
        SERVER_PY="$MAGENT_DIR/server.py"
        configure_client "$CLIENT" "$VENV_PYTHON" "$SERVER_PY"
        echo ""
    fi

    if [[ "$SKIP_TEST" != true ]]; then
        info "Validating installation..."
        if "$VENV_PYTHON" "$MAGENT_DIR/test_server.py" > /dev/null 2>&1; then
            ok "All tests passed"
        else
            err "Validation failed. Run 'python test_server.py' for details."
        fi
        echo ""
    fi

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

if [[ -n "$INSTALLED_VERSION" && "$INSTALLED_VERSION" == "$VERSION" && "$FORCE" != true ]]; then
    info "Already at v${VERSION}. Nothing to do."
    info "Use --upgrade to upgrade dependencies, or -f to force reinstall."
    echo ""
    exit 0
fi

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
configure_client "$CLIENT" "$VENV_PYTHON" "$SERVER_PY"
echo ""

# 7. Write marker
echo "$VERSION" > "$MAGENT_DIR/$MARKER_FILE"

# ── Done ─────────────────────────────────────────────────
echo "  ─────────────────────────────"
echo "  mageNT installed successfully!"
echo ""
echo "  Next steps:"
case "$CLIENT" in
    code)
        echo "  1. Open this directory in Claude Code"
        echo "  2. Try: \"List the available agents\""
        ;;
    kilo)
        echo "  1. Open this directory in Kilo Code"
        echo "  2. Try: \"List the available agents\""
        ;;
    opencode|goose)
        echo "  1. Restart the client to load the new MCP server"
        echo "  2. Try: \"List the available agents\""
        ;;
    *)
        echo "  1. Restart Claude Desktop (quit fully, then reopen)"
        echo "  2. Try: \"List the available agents\""
        ;;
esac
echo ""
