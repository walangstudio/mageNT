#!/usr/bin/env bash
set -euo pipefail

# ── Config ──────────────────────────────────────────────
MARKER_FILE=".magent-installed"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAGENT_DIR="$SCRIPT_DIR"
WORKSPACE_DIR="$PWD"
SERVER_NAME="magent"

# ── Defaults ────────────────────────────────────────────
FORCE=false
UNINSTALL=false
UPDATE=false
CLIENT="claudedesktop"
SKIP_TEST=false
GLOBAL_CONFIG=false
CLIENT_EXPLICIT=false
STATUS=false

# ── Parse flags ─────────────────────────────────────────
show_help() {
    cat <<EOF
Usage: ./install.sh [options]

Options:
  -c, --client TYPE   claudedesktop, claude, cursor, windsurf, vscode, gemini,
                      codex, zed, kilo, opencode, goose, pidev, all
                      (default: claudedesktop)
  -f, --force         Skip prompts, overwrite existing config
  -u, --uninstall     Remove mageNT from MCP client config
      --upgrade       Upgrade deps and merge new agents into existing config.yaml
      --update        Alias for --upgrade
      --status        Show where this server is currently installed
      --global        Write to global config path (claude, cursor, gemini, codex,
                      opencode, all)
      --skip-test     Skip test_server.py validation
  -h, --help          Show this help

Examples:
  ./install.sh                        Install for Claude Desktop
  ./install.sh -c claude              Install for Claude Code (workspace)
  ./install.sh -c claude --global     Install for Claude Code (global)
  ./install.sh -c cursor              Install for Cursor (workspace)
  ./install.sh -c cursor --global     Install for Cursor (global)
  ./install.sh -c windsurf            Install for Windsurf
  ./install.sh -c vscode              Install for VS Code (workspace .vscode/mcp.json)
  ./install.sh -c gemini              Install for Gemini CLI (workspace)
  ./install.sh -c codex               Install for OpenAI Codex CLI (workspace)
  ./install.sh -c zed                 Install for Zed (global)
  ./install.sh -c all                 Install for all detected clients
  ./install.sh --status               Show installation status
  ./install.sh --upgrade              Upgrade deps & config
  ./install.sh --upgrade -c claude    Upgrade + reconfigure Claude Code MCP path
  ./install.sh --upgrade -c all       Upgrade + reconfigure all clients
  ./install.sh -u                     Uninstall
  ./install.sh -u -c all              Uninstall from all client configs
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)          FORCE=true; shift ;;
        -u|--uninstall)      UNINSTALL=true; shift ;;
        --update|--upgrade)  UPDATE=true; shift ;;
        --status)            STATUS=true; shift ;;
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

if [[ "$UNINSTALL" == true && "$CLIENT_EXPLICIT" == false ]]; then
    CLIENT="all"
fi

if [[ "$GLOBAL_CONFIG" == true ]]; then
    case "$CLIENT" in
        claude|cursor|gemini|codex|opencode|both|all) ;;
        *) die "--global is only valid with -c claude, cursor, gemini, codex, opencode, or all" ;;
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
            local ver major minor
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || continue
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
    echo "$WORKSPACE_DIR/.mcp.json"
}

get_global_code_config_paths() {
    local found=()
    [[ -f "$HOME/.claude.json"     ]] && found+=("$HOME/.claude.json")
    [[ -f "$HOME/.claude/mcp.json" ]] && found+=("$HOME/.claude/mcp.json")
    if [[ ${#found[@]} -eq 0 ]]; then
        found+=("$HOME/.claude.json")
    fi
    printf '%s\n' "${found[@]}"
}

get_cursor_config_path() {
    if [[ "$GLOBAL_CONFIG" == true ]]; then
        echo "$HOME/.cursor/mcp.json"
    else
        echo "$WORKSPACE_DIR/.cursor/mcp.json"
    fi
}

get_windsurf_config_path() {
    echo "$HOME/.codeium/windsurf/mcp_config.json"
}

get_vscode_config_path() {
    echo "$WORKSPACE_DIR/.vscode/mcp.json"
}

get_gemini_config_path() {
    if [[ "$GLOBAL_CONFIG" == true ]]; then
        echo "$HOME/.gemini/settings.json"
    else
        echo "$WORKSPACE_DIR/.gemini/settings.json"
    fi
}

get_codex_config_path() {
    if [[ "$GLOBAL_CONFIG" == true ]]; then
        echo "$HOME/.codex/config.toml"
    else
        echo "$WORKSPACE_DIR/.codex/config.toml"
    fi
}

get_zed_config_path() {
    echo "$HOME/.config/zed/settings.json"
}

get_kilo_config_path() {
    echo "$WORKSPACE_DIR/.kilocode/mcp.json"
}

get_opencode_config_path() {
    if [[ "$GLOBAL_CONFIG" == true ]]; then
        echo "$HOME/.config/opencode/opencode.json"
    else
        echo "$WORKSPACE_DIR/opencode.json"
    fi
}

get_goose_config_path() {
    echo "$HOME/.config/goose/config.yaml"
}

# ── Python JSON merge helpers ─────────────────────────────
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
config['mcpServers']['$SERVER_NAME'] = {'command': python_path, 'args': [server_py]}
os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$config_path" "$server_py"
}

remove_mcp_config() {
    local config_path="$1"
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
if '$SERVER_NAME' in servers:
    del servers['$SERVER_NAME']
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print('  Removed $SERVER_NAME from config')
else:
    print('  $SERVER_NAME not found in config')
" "$config_path"
}

# ── VS Code (servers key) ─────────────────────────────────
merge_vscode_config() {
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
config.setdefault('servers', {})
config['servers']['$SERVER_NAME'] = {'type': 'stdio', 'command': python_path, 'args': [server_py]}
os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$config_path" "$server_py"
}

remove_vscode_config() {
    local config_path="$1"
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
servers = config.get('servers', {})
if '$SERVER_NAME' in servers:
    del servers['$SERVER_NAME']
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print('  Removed $SERVER_NAME from VS Code config')
else:
    print('  $SERVER_NAME not found in VS Code config')
" "$config_path"
}

# ── Codex TOML ────────────────────────────────────────────
merge_codex_config() {
    local config_path="$1"
    local server_py="$2"

    if [[ -f "$config_path" ]]; then
        cp "$config_path" "${config_path}.backup.$(date +%Y%m%d%H%M%S)"
        info "Backed up existing config"
    fi

    "$venv_python" -c "
import sys, os, re
config_path = os.path.abspath(sys.argv[1])
python_path = sys.executable
server_py = os.path.abspath(sys.argv[2])
sn = '$SERVER_NAME'
section_header = '[mcp_servers.' + sn + ']'
cmd = python_path + ' ' + server_py
new_section = '\n' + section_header + '\ncommand = \"' + cmd + '\"\nstartup_timeout_sec = 30\ntool_timeout_sec = 300\nenabled = true\n'
os.makedirs(os.path.dirname(config_path) or '.', exist_ok=True)
existing = ''
try:
    with open(config_path) as f:
        existing = f.read()
except FileNotFoundError:
    pass
if section_header in existing:
    lines = existing.split('\n')
    start = next((i for i, l in enumerate(lines) if l.strip() == section_header), -1)
    if start != -1:
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if re.match(r'^\[', lines[i]):
                end = i
                break
        del lines[start:end]
        existing = '\n'.join(lines)
existing = existing.rstrip()
if existing:
    existing += '\n'
with open(config_path, 'w') as f:
    f.write(existing + new_section)
" "$config_path" "$server_py"
}

remove_codex_config() {
    local config_path="$1"
    [[ -f "$config_path" ]] || return 0

    cp "$config_path" "${config_path}.backup.$(date +%Y%m%d%H%M%S)"

    "$venv_python" -c "
import sys, os, re
config_path = sys.argv[1]
sn = '$SERVER_NAME'
section_header = '[mcp_servers.' + sn + ']'
try:
    with open(config_path) as f:
        existing = f.read()
except FileNotFoundError:
    sys.exit(0)
if section_header not in existing:
    print('  $SERVER_NAME not found in codex config')
    sys.exit(0)
lines = existing.split('\n')
start = next((i for i, l in enumerate(lines) if l.strip() == section_header), -1)
if start != -1:
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r'^\[', lines[i]):
            end = i
            break
    del lines[start:end]
    with open(config_path, 'w') as f:
        f.write('\n'.join(lines))
    print('  Removed $SERVER_NAME from codex config')
" "$config_path"
}

# ── Zed (context_servers) ─────────────────────────────────
merge_zed_config() {
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
config.setdefault('context_servers', {})
config['context_servers']['$SERVER_NAME'] = {
    'command': {'path': python_path, 'args': [server_py], 'env': {}}
}
os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$config_path" "$server_py"
}

remove_zed_config() {
    local config_path="$1"
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
cs = config.get('context_servers', {})
if '$SERVER_NAME' in cs:
    del cs['$SERVER_NAME']
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print('  Removed $SERVER_NAME from Zed config')
else:
    print('  $SERVER_NAME not found in Zed config')
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
config['mcp']['$SERVER_NAME'] = {'type': 'local', 'command': [python_path] + extra_args}
d = os.path.dirname(config_path)
if d: os.makedirs(d, exist_ok=True)
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
if '$SERVER_NAME' in mcp:
    del mcp['$SERVER_NAME']
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    print('  Removed $SERVER_NAME from config')
else:
    print('  $SERVER_NAME not found in config')
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
    print('    $SERVER_NAME:')
    print('      name: $SERVER_NAME')
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
config['extensions']['$SERVER_NAME'] = {
    'name': '$SERVER_NAME', 'type': 'stdio', 'cmd': python_path,
    'args': extra_args, 'enabled': True,
}
d = os.path.dirname(config_path)
if d: os.makedirs(d, exist_ok=True)
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
if '$SERVER_NAME' in ext:
    del ext['$SERVER_NAME']
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print('  Removed $SERVER_NAME from config')
else:
    print('  $SERVER_NAME not found in config')
" "$config_path"
}

# ── Config migration ─────────────────────────────────────
migrate_config() {
    local _venv_python="$1"
    local example="$MAGENT_DIR/config.example.yaml"
    local config="$MAGENT_DIR/config.yaml"

    [[ -f "$example" ]] || { info "No config.example.yaml found, skipping migration"; return 0; }
    [[ -f "$config"  ]] || { info "No config.yaml found, skipping migration"; return 0; }

    "$_venv_python" -c "
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

# ── Status helpers ────────────────────────────────────────
_check_in_json() {
    local config_path="$1"
    [[ -f "$config_path" ]] || { echo "NO"; return; }
    grep -q "\"$SERVER_NAME\"" "$config_path" 2>/dev/null && echo "YES" || echo "NO"
}

_check_in_toml() {
    local config_path="$1"
    [[ -f "$config_path" ]] || { echo "NO"; return; }
    grep -q "^\[mcp_servers\.$SERVER_NAME\]" "$config_path" 2>/dev/null && echo "YES" || echo "NO"
}

_check_in_yaml() {
    local config_path="$1"
    [[ -f "$config_path" ]] || { echo "NO"; return; }
    grep -q "  $SERVER_NAME:" "$config_path" 2>/dev/null && echo "YES" || echo "NO"
}

# ── Configure client ─────────────────────────────────────
_configure_one_path() {
    local config_path="$1"
    local _vp="$2"
    local server_py="$3"

    if [[ "$UNINSTALL" == true ]]; then
        if [[ "$(_check_in_json "$config_path")" == "YES" ]]; then
            remove_mcp_config "$config_path" > /dev/null 2>&1
            ok "Removed ($config_path)"
        fi
        return
    fi

    info "Config: $config_path"

    if [[ -f "$config_path" ]] && [[ "$FORCE" != true ]]; then
        local current_cmd
        current_cmd=$("$_vp" -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        c = json.load(f)
    entry = c.get('mcpServers', {}).get('$SERVER_NAME', {})
    print(entry.get('command', ''))
except: pass
" "$config_path" 2>/dev/null) || true

        if [[ -n "$current_cmd" && "$current_cmd" == "$_vp" ]]; then
            info "MCP config already up to date"
            return 0
        elif [[ -n "$current_cmd" ]]; then
            info "Updating MCP config (python path changed)"
        fi
    fi

    merge_mcp_config "$config_path" "$server_py"
    ok "MCP config updated"
}

configure_client() {
    local client_type="$1"
    local _vp="$2"
    local server_py="$3"
    venv_python="$_vp"  # dynamic scoping for merge_mcp_config etc.

    case "$client_type" in
        claudedesktop)
            [[ "$UNINSTALL" != true ]] && info "Client: Claude Desktop"
            _configure_one_path "$(get_desktop_config_path)" "$_vp" "$server_py"
            ;;
        claude)
            if [[ "$GLOBAL_CONFIG" == true ]]; then
                [[ "$UNINSTALL" != true ]] && info "Client: Claude Code (global)"
                while IFS= read -r config_path; do
                    _configure_one_path "$config_path" "$_vp" "$server_py"
                done < <(get_global_code_config_paths)
            else
                [[ "$UNINSTALL" != true ]] && info "Client: Claude Code (workspace)"
                _configure_one_path "$(get_code_config_path)" "$_vp" "$server_py"
            fi
            ;;
        cursor)
            local cursor_path; cursor_path="$(get_cursor_config_path)"
            if [[ "$UNINSTALL" == true ]]; then
                if [[ "$(_check_in_json "$cursor_path")" == "YES" ]]; then
                    remove_mcp_config "$cursor_path" > /dev/null 2>&1; ok "Removed from Cursor"; fi
            else
                info "Client: Cursor"; info "Config: $cursor_path"
                merge_mcp_config "$cursor_path" "$server_py"; ok "MCP config updated"
            fi
            ;;
        windsurf)
            local windsurf_path; windsurf_path="$(get_windsurf_config_path)"
            if [[ "$UNINSTALL" == true ]]; then
                if [[ "$(_check_in_json "$windsurf_path")" == "YES" ]]; then
                    remove_mcp_config "$windsurf_path" > /dev/null 2>&1; ok "Removed from Windsurf"; fi
            else
                info "Client: Windsurf (global)"; info "Config: $windsurf_path"
                merge_mcp_config "$windsurf_path" "$server_py"; ok "MCP config updated"
            fi
            ;;
        vscode)
            local vscode_path; vscode_path="$(get_vscode_config_path)"
            if [[ "$UNINSTALL" == true ]]; then
                if [[ "$(_check_in_json "$vscode_path")" == "YES" ]]; then
                    remove_vscode_config "$vscode_path" > /dev/null 2>&1; ok "Removed from VS Code"; fi
            else
                info "Client: VS Code (workspace)"; info "Config: $vscode_path"
                info "Note: for global VS Code config, use the VS Code command palette"
                merge_vscode_config "$vscode_path" "$server_py"; ok "MCP config updated"
            fi
            ;;
        gemini)
            local gemini_path; gemini_path="$(get_gemini_config_path)"
            if [[ "$UNINSTALL" == true ]]; then
                if [[ "$(_check_in_json "$gemini_path")" == "YES" ]]; then
                    remove_mcp_config "$gemini_path" > /dev/null 2>&1; ok "Removed from Gemini CLI"; fi
            else
                info "Client: Gemini CLI"; info "Config: $gemini_path"
                merge_mcp_config "$gemini_path" "$server_py"; ok "MCP config updated"
            fi
            ;;
        codex)
            local codex_path; codex_path="$(get_codex_config_path)"
            if [[ "$UNINSTALL" == true ]]; then
                if [[ "$(_check_in_toml "$codex_path")" == "YES" ]]; then
                    remove_codex_config "$codex_path" > /dev/null 2>&1; ok "Removed from Codex CLI"; fi
            else
                info "Client: OpenAI Codex CLI"; info "Config: $codex_path"
                merge_codex_config "$codex_path" "$server_py"; ok "MCP config updated"
            fi
            ;;
        zed)
            local zed_path; zed_path="$(get_zed_config_path)"
            if [[ "$UNINSTALL" == true ]]; then
                if [[ "$(_check_in_json "$zed_path")" == "YES" ]]; then
                    remove_zed_config "$zed_path" > /dev/null 2>&1; ok "Removed from Zed"; fi
            else
                info "Client: Zed (global)"; info "Config: $zed_path"
                merge_zed_config "$zed_path" "$server_py"; ok "MCP config updated"
            fi
            ;;
        kilo)
            [[ "$UNINSTALL" != true ]] && info "Client: Kilo Code"
            _configure_one_path "$(get_kilo_config_path)" "$_vp" "$server_py"
            ;;
        opencode)
            local opencode_path; opencode_path="$(get_opencode_config_path)"
            if [[ "$UNINSTALL" == true ]]; then
                if [[ "$(_check_in_json "$opencode_path")" == "YES" ]]; then
                    remove_opencode_config "$opencode_path" "$_vp" > /dev/null 2>&1; ok "Removed from OpenCode"; fi
            else
                info "Client: OpenCode"; info "Config: $opencode_path"
                merge_opencode_config "$opencode_path" "$_vp" "$server_py"; ok "MCP config updated"
            fi
            ;;
        goose)
            local goose_path; goose_path="$(get_goose_config_path)"
            if [[ "$UNINSTALL" == true ]]; then
                if [[ "$(_check_in_yaml "$goose_path")" == "YES" ]]; then
                    remove_goose_config "$goose_path" "$_vp" > /dev/null 2>&1; ok "Removed from Goose"; fi
            else
                info "Client: Goose"; info "Config: $goose_path"
                merge_goose_config "$goose_path" "$_vp" "$server_py"; ok "MCP config updated"
            fi
            ;;
        pidev)
            info "Client: pi.dev"
            echo ""
            echo "  pi.dev does not support MCP servers natively."
            echo "  pi.dev uses TypeScript extensions and CLI tools instead."
            echo "  To use mageNT concepts in pi.dev, see: https://pi.dev/docs/extensions"
            echo ""
            ;;
        both)
            configure_client "claudedesktop" "$_vp" "$server_py"
            echo ""
            configure_client "claude" "$_vp" "$server_py"
            ;;
        all)
            configure_client "claudedesktop" "$_vp" "$server_py"
            echo ""
            configure_client "claude" "$_vp" "$server_py"
            local _ws _gh
            _ws="$WORKSPACE_DIR"
            _gh="$HOME"
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_ws/.cursor/mcp.json" ]] || [[ -f "$_gh/.cursor/mcp.json" ]]; then
                echo ""; configure_client "cursor" "$_vp" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_gh/.codeium/windsurf/mcp_config.json" ]]; then
                echo ""; configure_client "windsurf" "$_vp" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_ws/.vscode/mcp.json" ]]; then
                echo ""; configure_client "vscode" "$_vp" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_ws/.gemini/settings.json" ]] || [[ -f "$_gh/.gemini/settings.json" ]]; then
                echo ""; configure_client "gemini" "$_vp" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_ws/.codex/config.toml" ]] || [[ -f "$_gh/.codex/config.toml" ]]; then
                echo ""; configure_client "codex" "$_vp" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_gh/.config/zed/settings.json" ]]; then
                echo ""; configure_client "zed" "$_vp" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_ws/.kilocode/mcp.json" ]]; then
                echo ""; configure_client "kilo" "$_vp" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$_ws/opencode.json" ]] || [[ -f "$_gh/.config/opencode/opencode.json" ]]; then
                echo ""; configure_client "opencode" "$_vp" "$server_py"
            fi
            if [[ "$UNINSTALL" == true ]] || [[ -f "$(get_goose_config_path)" ]]; then
                echo ""; configure_client "goose" "$_vp" "$server_py"
            fi
            ;;
        *)
            die "Unknown client type: $client_type. Valid: claudedesktop, claude, cursor, windsurf, vscode, gemini, codex, zed, kilo, opencode, goose, pidev, both, all"
            ;;
    esac
}

# ── Show status ───────────────────────────────────────────
show_status() {
    local version installed_version
    version=$(get_version)
    installed_version=$(get_installed_version)
    local _ws _gh
    _ws="$WORKSPACE_DIR"
    _gh="$HOME"

    echo ""
    echo "  mageNT v${version} — Status"
    echo "  ────────────────────────────────────────────────────────────────────────────"
    printf "  %-30s %-9s %s\n" "Client" "Installed" "Config path"
    echo "  ────────────────────────────────────────────────────────────────────────────"

    _row() {
        local label="$1" status="$2" path="$3"
        if [[ "$status" == "YES" ]]; then
            printf "  %-30s %-9s %s\n" "$label" "YES" "$path"
        else
            printf "  %-30s %s\n" "$label" "NO"
        fi
    }

    local p s
    p="$(get_desktop_config_path)";   s=$(_check_in_json "$p"); _row "claudedesktop" "$s" "$p"
    p="$(get_code_config_path)";      s=$(_check_in_json "$p"); _row "claude (workspace)" "$s" "$p"
    while IFS= read -r gp; do
        s=$(_check_in_json "$gp"); _row "claude (global)" "$s" "$gp"
    done < <(get_global_code_config_paths)
    p="$_ws/.cursor/mcp.json";        s=$(_check_in_json "$p"); _row "cursor (workspace)" "$s" "$p"
    p="$_gh/.cursor/mcp.json";        s=$(_check_in_json "$p"); _row "cursor (global)" "$s" "$p"
    p="$(get_windsurf_config_path)";  s=$(_check_in_json "$p"); _row "windsurf" "$s" "$p"
    p="$(get_vscode_config_path)";    s=$(_check_in_json "$p"); _row "vscode (workspace)" "$s" "$p"
    p="$_ws/.gemini/settings.json";   s=$(_check_in_json "$p"); _row "gemini (workspace)" "$s" "$p"
    p="$_gh/.gemini/settings.json";   s=$(_check_in_json "$p"); _row "gemini (global)" "$s" "$p"
    p="$_ws/.codex/config.toml";      s=$(_check_in_toml "$p"); _row "codex (workspace)" "$s" "$p"
    p="$_gh/.codex/config.toml";      s=$(_check_in_toml "$p"); _row "codex (global)" "$s" "$p"
    p="$(get_zed_config_path)";       s=$(_check_in_json "$p"); _row "zed" "$s" "$p"
    p="$(get_kilo_config_path)";      s=$(_check_in_json "$p"); _row "kilo" "$s" "$p"
    p="$_ws/opencode.json";           s=$(_check_in_json "$p"); _row "opencode (workspace)" "$s" "$p"
    p="$_gh/.config/opencode/opencode.json"; s=$(_check_in_json "$p"); _row "opencode (global)" "$s" "$p"
    p="$(get_goose_config_path)";     s=$(_check_in_yaml "$p"); _row "goose" "$s" "$p"

    echo "  ────────────────────────────────────────────────────────────────────────────"
    if [[ -n "$installed_version" ]]; then
        echo "  Package: v${installed_version} installed"
    else
        echo "  Package: not installed"
    fi
    echo ""
}

# ── Banner ───────────────────────────────────────────────
VERSION=$(get_version)
INSTALLED_VERSION=$(get_installed_version)
echo ""
echo "  mageNT v${VERSION}"
if [[ "$UPDATE" == true && -n "$INSTALLED_VERSION" && "$INSTALLED_VERSION" != "$VERSION" ]]; then
    echo "  Upgrading from v${INSTALLED_VERSION}"
fi
if [[ "$STATUS" == true ]]; then
    echo "  Mode: status"
elif [[ "$UNINSTALL" == true ]]; then
    echo "  Mode: uninstall"
elif [[ "$UPDATE" == true ]]; then
    echo "  Mode: update"
else
    echo "  Mode: install (client: $CLIENT)"
fi
echo "  ─────────────────────────────"
echo ""

# ── Status ───────────────────────────────────────────────
if [[ "$STATUS" == true ]]; then
    show_status
    exit 0
fi

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
                info "Use --upgrade -c claude|all to also reconfigure MCP client."
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
    claude|kilo)
        echo "  1. Open this directory in your editor"
        echo "  2. Try: \"List the available agents\""
        ;;
    cursor|windsurf|vscode|gemini|codex|zed|opencode|goose)
        echo "  1. Restart the client to load the new MCP server"
        echo "  2. Try: \"List the available agents\""
        ;;
    *)
        echo "  1. Restart Claude Desktop (quit fully, then reopen)"
        echo "  2. Try: \"List the available agents\""
        ;;
esac
echo ""
