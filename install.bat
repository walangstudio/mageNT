@echo off
setlocal enabledelayedexpansion

rem ── Config ──────────────────────────────────────────────
set "MARKER_FILE=.magent-installed"
set "MAGENT_DIR=%~dp0"
if "!MAGENT_DIR:~-1!"=="\" set "MAGENT_DIR=!MAGENT_DIR:~0,-1!"
set "SERVER_NAME=magent"

rem ── Defaults ────────────────────────────────────────────
set "FORCE=false"
set "UNINSTALL=false"
set "UPDATE=false"
set "CLIENT=claudedesktop"
set "SKIP_TEST=false"
set "GLOBAL_CONFIG=false"
set "CLIENT_EXPLICIT=false"
set "STATUS=false"

goto :parse_args

rem ════════════════════════════════════════════════════════
:show_help
echo Usage: install.bat [options]
echo.
echo Options:
echo   -c, --client TYPE   MCP client: claudedesktop, claude, cursor, windsurf,
echo                       vscode, gemini, codex, zed, kilo, opencode, goose,
echo                       pidev, all  (default: claudedesktop)
echo   -f, --force         Skip prompts, overwrite existing config
echo   -u, --uninstall     Remove mageNT from MCP client config
echo       --upgrade       Upgrade deps and merge new agents into existing config.yaml
echo       --update        Alias for --upgrade
echo       --status        Show where this server is currently installed
echo       --global        Write to global config path (claude, cursor, gemini,
echo                       codex, opencode, all)
echo       --skip-test     Skip test_server.py validation
echo   -h, --help          Show this help
echo.
echo Examples:
echo   install.bat                        Install for Claude Desktop
echo   install.bat -c claude              Install for Claude Code (workspace)
echo   install.bat -c claude --global     Install for Claude Code (global)
echo   install.bat -c cursor              Install for Cursor (workspace)
echo   install.bat -c cursor --global     Install for Cursor (global)
echo   install.bat -c windsurf            Install for Windsurf
echo   install.bat -c vscode              Install for VS Code (workspace)
echo   install.bat -c gemini              Install for Gemini CLI
echo   install.bat -c codex               Install for OpenAI Codex CLI
echo   install.bat -c zed                 Install for Zed (global)
echo   install.bat -c kilo                Install for Kilo Code
echo   install.bat -c opencode            Install for OpenCode (workspace)
echo   install.bat -c opencode --global   Install for OpenCode (global)
echo   install.bat -c goose               Install for Goose
echo   install.bat -c all                 Install for all detected clients
echo   install.bat --status               Show installation status
echo   install.bat --upgrade              Upgrade deps ^& config
echo   install.bat --upgrade -c all        Upgrade + reconfigure all clients
echo   install.bat --upgrade -c claude    Upgrade + reconfigure Claude Code MCP path
echo   install.bat -u                     Uninstall
echo   install.bat -u -c all              Uninstall from all client configs
exit /b 0

rem ════════════════════════════════════════════════════════
:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="-h"          goto :show_help
if /i "%~1"=="--help"      goto :show_help
if /i "%~1"=="-f"          goto :pf_force
if /i "%~1"=="--force"     goto :pf_force
if /i "%~1"=="-u"          goto :pf_uninstall
if /i "%~1"=="--uninstall" goto :pf_uninstall
if /i "%~1"=="--update"    goto :pf_update
if /i "%~1"=="--upgrade"   goto :pf_update
if /i "%~1"=="--status"    goto :pf_status
if /i "%~1"=="--global"    goto :pf_global
if /i "%~1"=="--skip-test" goto :pf_skip_test
if /i "%~1"=="-c"          goto :pf_client
if /i "%~1"=="--client"    goto :pf_client
echo Unknown option: %~1
goto :show_help

:pf_force
set "FORCE=true"
shift
goto :parse_args
:pf_uninstall
set "UNINSTALL=true"
shift
goto :parse_args
:pf_update
set "UPDATE=true"
shift
goto :parse_args
:pf_status
set "STATUS=true"
shift
goto :parse_args
:pf_global
set "GLOBAL_CONFIG=true"
shift
goto :parse_args
:pf_skip_test
set "SKIP_TEST=true"
shift
goto :parse_args
:pf_client
if "%~2"=="" (
    echo   ERROR: --client requires a value >&2
    exit /b 1
)
set "CLIENT=%~2"
set "CLIENT_EXPLICIT=true"
shift
shift
goto :parse_args

rem ════════════════════════════════════════════════════════
:args_done

rem ── Default uninstall to all clients ─────────────────
if "!UNINSTALL!"=="true" (
    if "!CLIENT_EXPLICIT!"=="false" set "CLIENT=all"
)

rem ── Validate --global ─────────────────────────────────
if "!GLOBAL_CONFIG!"=="true" (
    if not "!CLIENT!"=="claude" (
        if not "!CLIENT!"=="cursor" (
            if not "!CLIENT!"=="gemini" (
                if not "!CLIENT!"=="codex" (
                    if not "!CLIENT!"=="both" (
                        if not "!CLIENT!"=="opencode" (
                            if not "!CLIENT!"=="all" (
                                echo   ERROR: --global is only valid with -c claude, cursor, gemini, codex, opencode, both, or all >&2
                                exit /b 1
                            )
                        )
                    )
                )
            )
        )
    )
)

rem ── Read version from __init__.py ────────────────────────
set "VERSION=unknown"
set "_PY_VER=%TEMP%\magent_version.py"
echo for line in open(r'!MAGENT_DIR!\__init__.py'): > "!_PY_VER!"
echo     if '__version__' in line: >> "!_PY_VER!"
echo         print(line.split('=',1)[1].strip().strip(chr(34)+chr(39))); break >> "!_PY_VER!"
for %%P in (python python3 py) do (
    if "!VERSION!"=="unknown" (
        where %%P >nul 2>&1 && (
            for /f "usebackq delims=" %%V in (`%%P "!_PY_VER!" 2^>nul`) do (
                set "VERSION=%%V"
            )
        )
    )
)
del /f /q "!_PY_VER!" 2>nul

rem ── Read installed version ───────────────────────────────
set "INSTALLED_VERSION="
if exist "!MAGENT_DIR!\!MARKER_FILE!" (
    set /p INSTALLED_VERSION=<"!MAGENT_DIR!\!MARKER_FILE!"
)

rem ── Compute config paths ─────────────────────────────────
set "DESKTOP_CONFIG=!APPDATA!\Claude\claude_desktop_config.json"
set "_PARENT=%CD%"

if "!GLOBAL_CONFIG!"=="true" (
    set "CODE_CONFIG=!USERPROFILE!\.claude.json"
) else (
    set "CODE_CONFIG=!_PARENT!\.mcp.json"
)

if "!GLOBAL_CONFIG!"=="true" (
    set "CURSOR_CONFIG=!USERPROFILE!\.cursor\mcp.json"
) else (
    set "CURSOR_CONFIG=!_PARENT!\.cursor\mcp.json"
)

set "WINDSURF_CONFIG=!USERPROFILE!\.codeium\windsurf\mcp_config.json"
set "VSCODE_CONFIG=!_PARENT!\.vscode\mcp.json"

if "!GLOBAL_CONFIG!"=="true" (
    set "GEMINI_CONFIG=!USERPROFILE!\.gemini\settings.json"
) else (
    set "GEMINI_CONFIG=!_PARENT!\.gemini\settings.json"
)

if "!GLOBAL_CONFIG!"=="true" (
    set "CODEX_CONFIG=!USERPROFILE!\.codex\config.toml"
) else (
    set "CODEX_CONFIG=!_PARENT!\.codex\config.toml"
)

set "ZED_CONFIG=!USERPROFILE!\.config\zed\settings.json"
set "KILO_CONFIG=!_PARENT!\.kilocode\mcp.json"

if "!GLOBAL_CONFIG!"=="true" (
    set "OPENCODE_CONFIG=!USERPROFILE!\.config\opencode\opencode.json"
) else (
    set "OPENCODE_CONFIG=!_PARENT!\opencode.json"
)

set "GOOSE_CONFIG=!USERPROFILE!\.config\goose\config.yaml"

rem ── Write Python helpers to temp files ───────────────────
set "PY_MERGE=!TEMP!\magent_merge.py"
set "PY_REMOVE=!TEMP!\magent_remove.py"
set "PY_CHECK=!TEMP!\magent_check.py"
set "PY_MIGRATE=!TEMP!\magent_migrate.py"
set "PY_MERGE_OPENCODE=!TEMP!\magent_merge_opencode.py"
set "PY_REMOVE_OPENCODE=!TEMP!\magent_remove_opencode.py"
set "PY_MERGE_GOOSE=!TEMP!\magent_merge_goose.py"
set "PY_REMOVE_GOOSE=!TEMP!\magent_remove_goose.py"
set "PY_MERGE_VSCODE=!TEMP!\magent_merge_vscode.py"
set "PY_REMOVE_VSCODE=!TEMP!\magent_remove_vscode.py"
set "PY_MERGE_CODEX=!TEMP!\magent_merge_codex.py"
set "PY_REMOVE_CODEX=!TEMP!\magent_remove_codex.py"
set "PY_MERGE_ZED=!TEMP!\magent_merge_zed.py"
set "PY_REMOVE_ZED=!TEMP!\magent_remove_zed.py"
set "PY_STATUS=!TEMP!\magent_status.py"

rem -- PY_MERGE (mcpServers) --
echo import json, sys, os > "!PY_MERGE!"
echo config_path = os.path.abspath(sys.argv[1]) >> "!PY_MERGE!"
echo python_path = sys.executable >> "!PY_MERGE!"
echo server_py = os.path.abspath(sys.argv[2]) >> "!PY_MERGE!"
echo try: >> "!PY_MERGE!"
echo     with open(config_path) as f: config = json.load(f) >> "!PY_MERGE!"
echo except (FileNotFoundError, json.JSONDecodeError): config = {} >> "!PY_MERGE!"
echo config.setdefault('mcpServers', {}) >> "!PY_MERGE!"
echo config['mcpServers']['magent'] = {'command': python_path, 'args': [server_py]} >> "!PY_MERGE!"
echo d = os.path.dirname(os.path.abspath(config_path)) >> "!PY_MERGE!"
echo if d: os.makedirs(d, exist_ok=True) >> "!PY_MERGE!"
echo with open(config_path, 'w') as f: >> "!PY_MERGE!"
echo     json.dump(config, f, indent=2) >> "!PY_MERGE!"
echo     f.write('\n') >> "!PY_MERGE!"

rem -- PY_REMOVE --
echo import json, sys, os > "!PY_REMOVE!"
echo config_path = sys.argv[1] >> "!PY_REMOVE!"
echo lbl = sys.argv[2] if len(sys.argv) > 2 else 'config' >> "!PY_REMOVE!"
echo if not os.path.exists(config_path): sys.exit(0) >> "!PY_REMOVE!"
echo try: >> "!PY_REMOVE!"
echo     with open(config_path) as f: config = json.load(f) >> "!PY_REMOVE!"
echo except (FileNotFoundError, json.JSONDecodeError): sys.exit(0) >> "!PY_REMOVE!"
echo servers = config.get('mcpServers', {}) >> "!PY_REMOVE!"
echo if 'magent' in servers: >> "!PY_REMOVE!"
echo     del servers['magent'] >> "!PY_REMOVE!"
echo     with open(config_path, 'w') as f: json.dump(config, f, indent=2); f.write('\n') >> "!PY_REMOVE!"
echo     print('  OK: Removed from ' + lbl) >> "!PY_REMOVE!"

rem -- PY_CHECK --
echo import json, sys, os > "!PY_CHECK!"
echo config_path = sys.argv[1] >> "!PY_CHECK!"
echo venv_python = sys.argv[2] >> "!PY_CHECK!"
echo try: >> "!PY_CHECK!"
echo     with open(config_path) as f: c = json.load(f) >> "!PY_CHECK!"
echo     entry = c.get('mcpServers', {}).get('magent', {}) >> "!PY_CHECK!"
echo     cmd = entry.get('command', '') >> "!PY_CHECK!"
echo     if cmd == venv_python: print('uptodate') >> "!PY_CHECK!"
echo     elif cmd: print('changed') >> "!PY_CHECK!"
echo     else: print('missing') >> "!PY_CHECK!"
echo except: print('missing') >> "!PY_CHECK!"

rem -- PY_MIGRATE --
echo import sys > "!PY_MIGRATE!"
echo try: import yaml >> "!PY_MIGRATE!"
echo except ImportError: >> "!PY_MIGRATE!"
echo     print('  PyYAML not available, skipping config migration') >> "!PY_MIGRATE!"
echo     sys.exit(0) >> "!PY_MIGRATE!"
echo example_path = sys.argv[1] >> "!PY_MIGRATE!"
echo config_path = sys.argv[2] >> "!PY_MIGRATE!"
echo with open(example_path) as f: example = yaml.safe_load(f) >> "!PY_MIGRATE!"
echo with open(config_path) as f: config = yaml.safe_load(f) or {} >> "!PY_MIGRATE!"
echo added_agents = [] >> "!PY_MIGRATE!"
echo added_workflows = [] >> "!PY_MIGRATE!"
echo config_agents = config.setdefault('agents', {}) >> "!PY_MIGRATE!"
echo for name, block in (example.get('agents', {}) or {}).items(): >> "!PY_MIGRATE!"
echo     if name not in config_agents: >> "!PY_MIGRATE!"
echo         nb = dict(block); nb['enabled'] = False >> "!PY_MIGRATE!"
echo         config_agents[name] = nb; added_agents.append(name) >> "!PY_MIGRATE!"
echo config_workflows = config.setdefault('workflows', {}) >> "!PY_MIGRATE!"
echo for name, block in (example.get('workflows', {}) or {}).items(): >> "!PY_MIGRATE!"
echo     if name not in config_workflows: >> "!PY_MIGRATE!"
echo         config_workflows[name] = block; added_workflows.append(name) >> "!PY_MIGRATE!"
echo with open(config_path, 'w') as f: yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False) >> "!PY_MIGRATE!"
echo if added_agents: print('  New agents added (disabled): ' + ', '.join(added_agents)) >> "!PY_MIGRATE!"
echo if added_workflows: print('  New workflows added: ' + ', '.join(added_workflows)) >> "!PY_MIGRATE!"
echo if not added_agents and not added_workflows: print('  config.yaml already up to date') >> "!PY_MIGRATE!"

rem -- PY_MERGE_OPENCODE --
echo import json, sys, os > "!PY_MERGE_OPENCODE!"
echo config_path = os.path.abspath(sys.argv[1]) >> "!PY_MERGE_OPENCODE!"
echo python_path = sys.executable >> "!PY_MERGE_OPENCODE!"
echo extra_args = sys.argv[2:] >> "!PY_MERGE_OPENCODE!"
echo try: >> "!PY_MERGE_OPENCODE!"
echo     with open(config_path) as f: config = json.load(f) >> "!PY_MERGE_OPENCODE!"
echo except (FileNotFoundError, json.JSONDecodeError): config = {} >> "!PY_MERGE_OPENCODE!"
echo config.setdefault('mcp', {}) >> "!PY_MERGE_OPENCODE!"
echo config['mcp']['magent'] = {'type': 'local', 'command': [python_path] + extra_args} >> "!PY_MERGE_OPENCODE!"
echo d = os.path.dirname(config_path) >> "!PY_MERGE_OPENCODE!"
echo if d: os.makedirs(d, exist_ok=True) >> "!PY_MERGE_OPENCODE!"
echo with open(config_path, 'w') as f: >> "!PY_MERGE_OPENCODE!"
echo     json.dump(config, f, indent=2) >> "!PY_MERGE_OPENCODE!"
echo     f.write('\n') >> "!PY_MERGE_OPENCODE!"

rem -- PY_REMOVE_OPENCODE --
echo import json, sys, os > "!PY_REMOVE_OPENCODE!"
echo config_path = sys.argv[1] >> "!PY_REMOVE_OPENCODE!"
echo if not os.path.exists(config_path): sys.exit(0) >> "!PY_REMOVE_OPENCODE!"
echo try: >> "!PY_REMOVE_OPENCODE!"
echo     with open(config_path) as f: config = json.load(f) >> "!PY_REMOVE_OPENCODE!"
echo except: sys.exit(0) >> "!PY_REMOVE_OPENCODE!"
echo mcp = config.get('mcp', {}) >> "!PY_REMOVE_OPENCODE!"
echo if 'magent' in mcp: >> "!PY_REMOVE_OPENCODE!"
echo     del mcp['magent'] >> "!PY_REMOVE_OPENCODE!"
echo     with open(config_path, 'w') as f: json.dump(config, f, indent=2); f.write('\n') >> "!PY_REMOVE_OPENCODE!"
echo     print('  Removed magent from config') >> "!PY_REMOVE_OPENCODE!"

rem -- PY_MERGE_GOOSE --
echo import sys, os > "!PY_MERGE_GOOSE!"
echo try: import yaml >> "!PY_MERGE_GOOSE!"
echo except ImportError: >> "!PY_MERGE_GOOSE!"
echo     py = sys.executable; args = sys.argv[2:] >> "!PY_MERGE_GOOSE!"
echo     print('  PyYAML not available. Add manually to config.yaml:') >> "!PY_MERGE_GOOSE!"
echo     print('  extensions:') >> "!PY_MERGE_GOOSE!"
echo     print('    magent:') >> "!PY_MERGE_GOOSE!"
echo     print('      name: magent') >> "!PY_MERGE_GOOSE!"
echo     print('      type: stdio') >> "!PY_MERGE_GOOSE!"
echo     print('      cmd: ' + py) >> "!PY_MERGE_GOOSE!"
echo     print('      args: ' + str(args)) >> "!PY_MERGE_GOOSE!"
echo     print('      enabled: true') >> "!PY_MERGE_GOOSE!"
echo     sys.exit(0) >> "!PY_MERGE_GOOSE!"
echo config_path = os.path.abspath(sys.argv[1]) >> "!PY_MERGE_GOOSE!"
echo python_path = sys.executable >> "!PY_MERGE_GOOSE!"
echo extra_args = sys.argv[2:] >> "!PY_MERGE_GOOSE!"
echo try: >> "!PY_MERGE_GOOSE!"
echo     with open(config_path) as f: config = yaml.safe_load(f) or {} >> "!PY_MERGE_GOOSE!"
echo except FileNotFoundError: config = {} >> "!PY_MERGE_GOOSE!"
echo config.setdefault('extensions', {}) >> "!PY_MERGE_GOOSE!"
echo config['extensions']['magent'] = {'name': 'magent', 'type': 'stdio', 'cmd': python_path, 'args': extra_args, 'enabled': True} >> "!PY_MERGE_GOOSE!"
echo d = os.path.dirname(config_path) >> "!PY_MERGE_GOOSE!"
echo if d: os.makedirs(d, exist_ok=True) >> "!PY_MERGE_GOOSE!"
echo with open(config_path, 'w') as f: yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False) >> "!PY_MERGE_GOOSE!"

rem -- PY_REMOVE_GOOSE --
echo import sys, os > "!PY_REMOVE_GOOSE!"
echo try: import yaml >> "!PY_REMOVE_GOOSE!"
echo except ImportError: print('  PyYAML not available'); sys.exit(0) >> "!PY_REMOVE_GOOSE!"
echo config_path = sys.argv[1] >> "!PY_REMOVE_GOOSE!"
echo if not os.path.exists(config_path): sys.exit(0) >> "!PY_REMOVE_GOOSE!"
echo try: >> "!PY_REMOVE_GOOSE!"
echo     with open(config_path) as f: config = yaml.safe_load(f) or {} >> "!PY_REMOVE_GOOSE!"
echo except: sys.exit(0) >> "!PY_REMOVE_GOOSE!"
echo ext = config.get('extensions', {}) >> "!PY_REMOVE_GOOSE!"
echo if 'magent' in ext: >> "!PY_REMOVE_GOOSE!"
echo     del ext['magent'] >> "!PY_REMOVE_GOOSE!"
echo     with open(config_path, 'w') as f: yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False) >> "!PY_REMOVE_GOOSE!"
echo     print('  Removed magent from config') >> "!PY_REMOVE_GOOSE!"

rem -- PY_MERGE_VSCODE (servers key) --
echo import json, sys, os > "!PY_MERGE_VSCODE!"
echo config_path = os.path.abspath(sys.argv[1]) >> "!PY_MERGE_VSCODE!"
echo python_path = sys.executable >> "!PY_MERGE_VSCODE!"
echo server_py = os.path.abspath(sys.argv[2]) >> "!PY_MERGE_VSCODE!"
echo try: >> "!PY_MERGE_VSCODE!"
echo     with open(config_path) as f: config = json.load(f) >> "!PY_MERGE_VSCODE!"
echo except (FileNotFoundError, json.JSONDecodeError): config = {} >> "!PY_MERGE_VSCODE!"
echo config.setdefault('servers', {}) >> "!PY_MERGE_VSCODE!"
echo config['servers']['magent'] = {'type': 'stdio', 'command': python_path, 'args': [server_py]} >> "!PY_MERGE_VSCODE!"
echo d = os.path.dirname(os.path.abspath(config_path)) >> "!PY_MERGE_VSCODE!"
echo if d: os.makedirs(d, exist_ok=True) >> "!PY_MERGE_VSCODE!"
echo with open(config_path, 'w') as f: json.dump(config, f, indent=2); f.write('\n') >> "!PY_MERGE_VSCODE!"

rem -- PY_REMOVE_VSCODE --
echo import json, sys, os > "!PY_REMOVE_VSCODE!"
echo config_path = sys.argv[1] >> "!PY_REMOVE_VSCODE!"
echo if not os.path.exists(config_path): sys.exit(0) >> "!PY_REMOVE_VSCODE!"
echo try: >> "!PY_REMOVE_VSCODE!"
echo     with open(config_path) as f: config = json.load(f) >> "!PY_REMOVE_VSCODE!"
echo except: sys.exit(0) >> "!PY_REMOVE_VSCODE!"
echo servers = config.get('servers', {}) >> "!PY_REMOVE_VSCODE!"
echo if 'magent' in servers: >> "!PY_REMOVE_VSCODE!"
echo     del servers['magent'] >> "!PY_REMOVE_VSCODE!"
echo     with open(config_path, 'w') as f: json.dump(config, f, indent=2); f.write('\n') >> "!PY_REMOVE_VSCODE!"
echo     print('  Removed magent from VS Code config') >> "!PY_REMOVE_VSCODE!"

rem -- PY_MERGE_CODEX (TOML) --
echo import sys, os, re > "!PY_MERGE_CODEX!"
echo config_path = os.path.abspath(sys.argv[1]) >> "!PY_MERGE_CODEX!"
echo python_path = sys.executable >> "!PY_MERGE_CODEX!"
echo server_py = os.path.abspath(sys.argv[2]) >> "!PY_MERGE_CODEX!"
echo sn = 'magent' >> "!PY_MERGE_CODEX!"
echo section_header = '[mcp_servers.' + sn + ']' >> "!PY_MERGE_CODEX!"
echo cmd = python_path + ' ' + server_py >> "!PY_MERGE_CODEX!"
echo new_section = '\n' + section_header + '\ncommand = "' + cmd + '"\nstartup_timeout_sec = 30\ntool_timeout_sec = 300\nenabled = true\n' >> "!PY_MERGE_CODEX!"
echo os.makedirs(os.path.dirname(config_path) or '.', exist_ok=True) >> "!PY_MERGE_CODEX!"
echo existing = '' >> "!PY_MERGE_CODEX!"
echo try: >> "!PY_MERGE_CODEX!"
echo     with open(config_path) as f: existing = f.read() >> "!PY_MERGE_CODEX!"
echo except FileNotFoundError: pass >> "!PY_MERGE_CODEX!"
echo if section_header in existing: >> "!PY_MERGE_CODEX!"
echo     lines = existing.split('\n') >> "!PY_MERGE_CODEX!"
echo     start = next((i for i, l in enumerate(lines) if l.strip() == section_header), -1) >> "!PY_MERGE_CODEX!"
echo     if start != -1: >> "!PY_MERGE_CODEX!"
echo         end = len(lines) >> "!PY_MERGE_CODEX!"
echo         for i in range(start + 1, len(lines)): >> "!PY_MERGE_CODEX!"
echo             if re.match(r'^\[', lines[i]): end = i; break >> "!PY_MERGE_CODEX!"
echo         del lines[start:end] >> "!PY_MERGE_CODEX!"
echo         existing = '\n'.join(lines) >> "!PY_MERGE_CODEX!"
echo existing = existing.rstrip() >> "!PY_MERGE_CODEX!"
echo if existing: existing += '\n' >> "!PY_MERGE_CODEX!"
echo with open(config_path, 'w') as f: f.write(existing + new_section) >> "!PY_MERGE_CODEX!"

rem -- PY_REMOVE_CODEX --
echo import sys, os, re > "!PY_REMOVE_CODEX!"
echo config_path = sys.argv[1] >> "!PY_REMOVE_CODEX!"
echo sn = 'magent' >> "!PY_REMOVE_CODEX!"
echo section_header = '[mcp_servers.' + sn + ']' >> "!PY_REMOVE_CODEX!"
echo if not os.path.exists(config_path): sys.exit(0) >> "!PY_REMOVE_CODEX!"
echo with open(config_path) as f: existing = f.read() >> "!PY_REMOVE_CODEX!"
echo if section_header not in existing: >> "!PY_REMOVE_CODEX!"
echo     sys.exit(0) >> "!PY_REMOVE_CODEX!"
echo lines = existing.split('\n') >> "!PY_REMOVE_CODEX!"
echo start = next((i for i, l in enumerate(lines) if l.strip() == section_header), -1) >> "!PY_REMOVE_CODEX!"
echo if start != -1: >> "!PY_REMOVE_CODEX!"
echo     end = len(lines) >> "!PY_REMOVE_CODEX!"
echo     for i in range(start + 1, len(lines)): >> "!PY_REMOVE_CODEX!"
echo         if re.match(r'^\[', lines[i]): end = i; break >> "!PY_REMOVE_CODEX!"
echo     del lines[start:end] >> "!PY_REMOVE_CODEX!"
echo     with open(config_path, 'w') as f: f.write('\n'.join(lines)) >> "!PY_REMOVE_CODEX!"
echo     print('  Removed magent from codex config') >> "!PY_REMOVE_CODEX!"

rem -- PY_MERGE_ZED (context_servers) --
echo import json, sys, os > "!PY_MERGE_ZED!"
echo config_path = os.path.abspath(sys.argv[1]) >> "!PY_MERGE_ZED!"
echo python_path = sys.executable >> "!PY_MERGE_ZED!"
echo server_py = os.path.abspath(sys.argv[2]) >> "!PY_MERGE_ZED!"
echo try: >> "!PY_MERGE_ZED!"
echo     with open(config_path) as f: config = json.load(f) >> "!PY_MERGE_ZED!"
echo except (FileNotFoundError, json.JSONDecodeError): config = {} >> "!PY_MERGE_ZED!"
echo config.setdefault('context_servers', {}) >> "!PY_MERGE_ZED!"
echo config['context_servers']['magent'] = {'command': {'path': python_path, 'args': [server_py], 'env': {}}} >> "!PY_MERGE_ZED!"
echo os.makedirs(os.path.dirname(config_path), exist_ok=True) >> "!PY_MERGE_ZED!"
echo with open(config_path, 'w') as f: json.dump(config, f, indent=2); f.write('\n') >> "!PY_MERGE_ZED!"

rem -- PY_REMOVE_ZED --
echo import json, sys, os > "!PY_REMOVE_ZED!"
echo config_path = sys.argv[1] >> "!PY_REMOVE_ZED!"
echo if not os.path.exists(config_path): sys.exit(0) >> "!PY_REMOVE_ZED!"
echo try: >> "!PY_REMOVE_ZED!"
echo     with open(config_path) as f: config = json.load(f) >> "!PY_REMOVE_ZED!"
echo except: sys.exit(0) >> "!PY_REMOVE_ZED!"
echo cs = config.get('context_servers', {}) >> "!PY_REMOVE_ZED!"
echo if 'magent' in cs: >> "!PY_REMOVE_ZED!"
echo     del cs['magent'] >> "!PY_REMOVE_ZED!"
echo     with open(config_path, 'w') as f: json.dump(config, f, indent=2); f.write('\n') >> "!PY_REMOVE_ZED!"
echo     print('  Removed magent from Zed config') >> "!PY_REMOVE_ZED!"

rem -- PY_STATUS --
echo import sys, os > "!PY_STATUS!"
echo config_path = sys.argv[1] >> "!PY_STATUS!"
echo fmt = sys.argv[2] if len(sys.argv) > 2 else 'json' >> "!PY_STATUS!"
echo if not os.path.exists(config_path): print('NO'); sys.exit(0) >> "!PY_STATUS!"
echo try: >> "!PY_STATUS!"
echo     if fmt == 'toml': >> "!PY_STATUS!"
echo         c = open(config_path).read() >> "!PY_STATUS!"
echo         print('YES' if '[mcp_servers.magent]' in c else 'NO') >> "!PY_STATUS!"
echo     elif fmt == 'yaml': >> "!PY_STATUS!"
echo         c = open(config_path).read() >> "!PY_STATUS!"
echo         print('YES' if '  magent:' in c else 'NO') >> "!PY_STATUS!"
echo     else: >> "!PY_STATUS!"
echo         import json >> "!PY_STATUS!"
echo         c = json.dumps(json.load(open(config_path))) >> "!PY_STATUS!"
echo         print('YES' if '"magent"' in c else 'NO') >> "!PY_STATUS!"
echo except: print('NO') >> "!PY_STATUS!"

rem ── Banner ───────────────────────────────────────────────
echo.
echo   mageNT v!VERSION!
if "!STATUS!"=="true" (
    echo   Mode: status
) else if "!UPDATE!"=="true" (
    if not "!INSTALLED_VERSION!"=="" (
        if not "!INSTALLED_VERSION!"=="!VERSION!" (
            echo   Upgrading from v!INSTALLED_VERSION!
        )
    )
    echo   Mode: update
) else if "!UNINSTALL!"=="true" (
    echo   Mode: uninstall
) else (
    echo   Mode: install ^(client: !CLIENT!^)
)
echo   -----------------------------
echo.

rem ── Status ───────────────────────────────────────────────
if "!STATUS!"=="true" (
    call :find_venv_python
    if "!VENV_PYTHON!"=="" call :find_python & set "VENV_PYTHON=!SYSTEM_PYTHON!"
    call :show_status
    goto :cleanup
)

rem ── Uninstall path ───────────────────────────────────────
if not "!UNINSTALL!"=="true" goto :not_uninstall

call :find_venv_python
if "!VENV_PYTHON!"=="" (
    call :find_python
    if "!SYSTEM_PYTHON!"=="" (
        echo   ERROR: Python not found >&2
        exit /b 1
    )
    set "VENV_PYTHON=!SYSTEM_PYTHON!"
)

call :configure_client "!CLIENT!" "!VENV_PYTHON!" ""

del /f /q "!MAGENT_DIR!\!MARKER_FILE!" 2>nul
echo   Removed version marker

if exist "!MAGENT_DIR!\.venv" (
    if "!FORCE!"=="true" (
        rmdir /s /q "!MAGENT_DIR!\.venv"
        echo   Removed .venv
    ) else (
        set /p "_ans=  Remove virtual environment (.venv)? [y/N] "
        if /i "!_ans!"=="y" (
            rmdir /s /q "!MAGENT_DIR!\.venv"
            echo   Removed .venv
        ) else (
            echo   Kept .venv
        )
    )
)

echo.
echo   mageNT uninstalled.
echo.
goto :cleanup

:not_uninstall

rem ── Update path ──────────────────────────────────────────
if not "!UPDATE!"=="true" goto :not_update

if not "!INSTALLED_VERSION!"=="" (
    if "!INSTALLED_VERSION!"=="!VERSION!" (
        if not "!CLIENT_EXPLICIT!"=="true" (
            if not "!FORCE!"=="true" (
                echo   Already at v!VERSION!. Nothing to do.
                echo   Use --upgrade -c claude^|all to also reconfigure MCP client.
                echo.
                goto :cleanup
            )
        )
        echo   Already at v!VERSION! -- reconfiguring MCP client
    ) else (
        echo   Upgrading v!INSTALLED_VERSION! --^> v!VERSION!
    )
) else (
    echo   No marker found -- running full update
)
echo.


call :find_venv_python
if "!VENV_PYTHON!"=="" (
    call :find_python
    if "!SYSTEM_PYTHON!"=="" (
        echo   ERROR: Python 3.10+ is required >&2
        exit /b 1
    )
    echo   No venv found -- creating one first...
    "!SYSTEM_PYTHON!" -m venv "!MAGENT_DIR!\.venv"
    call :find_venv_python
)

rem 1. Upgrade dependencies
echo   Upgrading dependencies...
"!VENV_PYTHON!" -m pip install -r "!MAGENT_DIR!\requirements.txt" --upgrade --quiet >nul 2>&1
echo   OK: Dependencies upgraded
echo.

rem 2. Migrate config.yaml
echo   Migrating config.yaml...
if exist "!MAGENT_DIR!\config.example.yaml" (
    if exist "!MAGENT_DIR!\config.yaml" (
        "!VENV_PYTHON!" "!PY_MIGRATE!" "!MAGENT_DIR!\config.example.yaml" "!MAGENT_DIR!\config.yaml"
    ) else (
        echo   No config.yaml found, skipping migration
    )
) else (
    echo   No config.example.yaml found, skipping migration
)
echo.

rem 3. Reconfigure MCP client if -c was explicit
if "!CLIENT_EXPLICIT!"=="true" (
    echo   Reconfiguring MCP client ^(!CLIENT!^)...
    set "SERVER_PY=!MAGENT_DIR!\server.py"
    call :configure_client "!CLIENT!" "!VENV_PYTHON!" "!SERVER_PY!"
    echo.
)

rem 4. Run tests
if not "!SKIP_TEST!"=="true" (
    echo   Validating installation...
    "!VENV_PYTHON!" "!MAGENT_DIR!\test_server.py" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   OK: All tests passed
    ) else (
        echo   ERROR: Validation failed. Run 'python test_server.py' for details. >&2
    )
    echo.
)

rem 5. Update marker
echo !VERSION!> "!MAGENT_DIR!\!MARKER_FILE!"
echo   OK: Marker updated to v!VERSION!

echo   -----------------------------
echo   mageNT updated to v!VERSION!!
echo.
echo   Restart Claude (quit fully, then reopen) to load new agents.
echo.
goto :cleanup

:not_update

rem ── Install path ─────────────────────────────────────────

if not "!INSTALLED_VERSION!"=="" (
    if "!INSTALLED_VERSION!"=="!VERSION!" (
        if not "!FORCE!"=="true" (
            echo   Already at v!VERSION!. Nothing to do.
            echo   Use --upgrade to upgrade dependencies, or -f to force reinstall.
            echo.
            goto :cleanup
        )
    )
)

rem 1. Find Python
echo   Checking Python...
call :find_python
if "!SYSTEM_PYTHON!"=="" (
    echo   ERROR: Python 3.10+ is required. Install from https://python.org >&2
    exit /b 1
)
for /f "usebackq delims=" %%V in (`"!SYSTEM_PYTHON!" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul`) do set "PY_VER=%%V"
echo   OK: Python !PY_VER!
echo.

rem 2. Setup venv
echo   Setting up virtual environment...
if exist "!MAGENT_DIR!\.venv" (
    if not "!FORCE!"=="true" (
        echo   OK: Using existing .venv
        goto :venv_done
    )
)
"!SYSTEM_PYTHON!" -m venv "!MAGENT_DIR!\.venv"
echo   OK: Created .venv

:venv_done
call :find_venv_python
if "!VENV_PYTHON!"=="" (
    echo   ERROR: venv python not found >&2
    exit /b 1
)
echo.

rem 3. Install deps
echo   Installing dependencies...
"!VENV_PYTHON!" -m pip install -r "!MAGENT_DIR!\requirements.txt" --quiet 2>nul
echo   OK: Dependencies installed
echo.

rem 4. Init config
echo   Checking configuration...
if not exist "!MAGENT_DIR!\config.yaml" (
    copy /y "!MAGENT_DIR!\config.example.yaml" "!MAGENT_DIR!\config.yaml" >nul
    echo   OK: Created config.yaml from template
) else (
    echo   OK: config.yaml exists
)
echo.

rem 5. Run tests
if not "!SKIP_TEST!"=="true" (
    echo   Validating installation...
    "!VENV_PYTHON!" "!MAGENT_DIR!\test_server.py" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   OK: All tests passed
    ) else (
        echo   ERROR: Validation failed. Run 'python test_server.py' for details. >&2
        echo   ERROR: Use --skip-test to skip this step. >&2
        exit /b 1
    )
    echo.
)

rem 6. Configure MCP client
echo   Configuring MCP client...
set "SERVER_PY=!MAGENT_DIR!\server.py"
call :configure_client "!CLIENT!" "!VENV_PYTHON!" "!SERVER_PY!"
echo.

rem 7. Write marker
echo !VERSION!> "!MAGENT_DIR!\!MARKER_FILE!"

rem ── Done ─────────────────────────────────────────────────
echo   -----------------------------
echo   mageNT installed successfully!
echo.
echo   Next steps:
if "!CLIENT!"=="claude" (
    echo   1. Open the workspace in Claude Code
    echo   2. Try: "List the available agents"
) else if "!CLIENT!"=="claudedesktop" (
    echo   1. Restart Claude Desktop ^(quit fully, then reopen^)
    echo   2. Try: "List the available agents"
) else (
    echo   1. Restart your MCP client to load the server
    echo   2. Try: "List the available agents"
)
echo.

:cleanup
del /f /q "!PY_MERGE!" "!PY_REMOVE!" "!PY_CHECK!" "!PY_MIGRATE!" 2>nul
del /f /q "!PY_MERGE_OPENCODE!" "!PY_REMOVE_OPENCODE!" "!PY_MERGE_GOOSE!" "!PY_REMOVE_GOOSE!" 2>nul
del /f /q "!PY_MERGE_VSCODE!" "!PY_REMOVE_VSCODE!" "!PY_MERGE_CODEX!" "!PY_REMOVE_CODEX!" 2>nul
del /f /q "!PY_MERGE_ZED!" "!PY_REMOVE_ZED!" "!PY_STATUS!" 2>nul
endlocal
exit /b 0

rem ════════════════════════════════════════════════════════
:find_python
set "SYSTEM_PYTHON="
for %%P in (python python3 py) do (
    if "!SYSTEM_PYTHON!"=="" (
        where %%P >nul 2>&1 && (
            "%%P" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1 && (
                for /f "usebackq delims=" %%Q in (`where %%P 2^>nul`) do (
                    if "!SYSTEM_PYTHON!"=="" set "SYSTEM_PYTHON=%%Q"
                )
            )
        )
    )
)
goto :eof

rem ════════════════════════════════════════════════════════
:find_venv_python
set "VENV_PYTHON="
if exist "!MAGENT_DIR!\.venv\Scripts\python.exe" (
    set "VENV_PYTHON=!MAGENT_DIR!\.venv\Scripts\python.exe"
) else if exist "!MAGENT_DIR!\.venv\bin\python.exe" (
    set "VENV_PYTHON=!MAGENT_DIR!\.venv\bin\python.exe"
)
goto :eof

rem ════════════════════════════════════════════════════════
:show_status
echo import json, os > "!PY_STATUS!"
echo def chk(p, fmt): >> "!PY_STATUS!"
echo     if not os.path.exists(p): return False >> "!PY_STATUS!"
echo     try: >> "!PY_STATUS!"
echo         with open(p) as f: raw = f.read() >> "!PY_STATUS!"
echo         if fmt == 'toml': return '[mcp_servers.magent]' in raw >> "!PY_STATUS!"
echo         if fmt == 'yaml': return '  magent:' in raw >> "!PY_STATUS!"
echo         return '"magent"' in json.dumps(json.load(open(p))) >> "!PY_STATUS!"
echo     except: return False >> "!PY_STATUS!"
echo rows = [ >> "!PY_STATUS!"
echo     ('claudedesktop        ', r'!DESKTOP_CONFIG!', 'json'), >> "!PY_STATUS!"
echo     ('claude (workspace)   ', r'!CODE_CONFIG!', 'json'), >> "!PY_STATUS!"
echo     ('claude (global)      ', r'!USERPROFILE!\.claude.json', 'json'), >> "!PY_STATUS!"
echo     ('cursor (workspace)   ', r'!_PARENT!\.cursor\mcp.json', 'json'), >> "!PY_STATUS!"
echo     ('cursor (global)      ', r'!USERPROFILE!\.cursor\mcp.json', 'json'), >> "!PY_STATUS!"
echo     ('windsurf             ', r'!WINDSURF_CONFIG!', 'json'), >> "!PY_STATUS!"
echo     ('vscode (workspace)   ', r'!VSCODE_CONFIG!', 'json'), >> "!PY_STATUS!"
echo     ('gemini (workspace)   ', r'!_PARENT!\.gemini\settings.json', 'json'), >> "!PY_STATUS!"
echo     ('gemini (global)      ', r'!USERPROFILE!\.gemini\settings.json', 'json'), >> "!PY_STATUS!"
echo     ('codex (workspace)    ', r'!_PARENT!\.codex\config.toml', 'toml'), >> "!PY_STATUS!"
echo     ('codex (global)       ', r'!USERPROFILE!\.codex\config.toml', 'toml'), >> "!PY_STATUS!"
echo     ('zed                  ', r'!ZED_CONFIG!', 'json'), >> "!PY_STATUS!"
echo     ('kilo                 ', r'!KILO_CONFIG!', 'json'), >> "!PY_STATUS!"
echo     ('opencode (workspace) ', r'!_PARENT!\opencode.json', 'json'), >> "!PY_STATUS!"
echo     ('opencode (global)    ', r'!USERPROFILE!\.config\opencode\opencode.json', 'json'), >> "!PY_STATUS!"
echo     ('goose                ', r'!GOOSE_CONFIG!', 'yaml'), >> "!PY_STATUS!"
echo ] >> "!PY_STATUS!"
echo for lbl, p, fmt in rows: >> "!PY_STATUS!"
echo     if chk(p, fmt): print(f'   {lbl}  YES  {p}') >> "!PY_STATUS!"
echo     else: print(f'   {lbl}  NO') >> "!PY_STATUS!"
echo.
echo   mageNT v!VERSION! -- Status
echo   ------------------------------------------------------------------------
echo   Client               Installed  Config path
echo   ------------------------------------------------------------------------
"!VENV_PYTHON!" "!PY_STATUS!"
echo   ------------------------------------------------------------------------
if not "!INSTALLED_VERSION!"=="" (
    echo   Package: v!INSTALLED_VERSION! installed
) else (
    echo   Package: not installed
)
echo.
goto :eof

rem ════════════════════════════════════════════════════════
:configure_client
set "_ct=%~1"
set "_vp=%~2"
set "_sp=%~3"

if "!_ct!"=="claudedesktop"  goto :cc_desktop
if "!_ct!"=="claude"         goto :cc_code
if "!_ct!"=="cursor"   goto :cc_cursor
if "!_ct!"=="windsurf" goto :cc_windsurf
if "!_ct!"=="vscode"   goto :cc_vscode
if "!_ct!"=="gemini"   goto :cc_gemini
if "!_ct!"=="codex"    goto :cc_codex
if "!_ct!"=="zed"      goto :cc_zed
if "!_ct!"=="kilo"     goto :cc_kilo
if "!_ct!"=="opencode" goto :cc_opencode
if "!_ct!"=="goose"    goto :cc_goose
if "!_ct!"=="pidev"    goto :cc_pidev
if "!_ct!"=="both"     goto :cc_both
if "!_ct!"=="all"      goto :cc_all
echo   ERROR: Unknown client type: !_ct! >&2
goto :eof

:cc_desktop
if not "!UNINSTALL!"=="true" ( echo   Client: Claude Desktop & echo   Config: !DESKTOP_CONFIG! )
call :_configure_one_path "!DESKTOP_CONFIG!" "!_vp!" "!_sp!" "Claude Desktop"
goto :eof

:cc_code
if "!GLOBAL_CONFIG!"=="true" (
    if not "!UNINSTALL!"=="true" echo   Client: Claude Code ^(global^)
    set "_code_cfg=!USERPROFILE!\.claude.json"
    if not "!UNINSTALL!"=="true" echo   Config: !_code_cfg!
    call :_configure_one_path "!_code_cfg!" "!_vp!" "!_sp!" "Claude Code (global)"
) else (
    if not "!UNINSTALL!"=="true" ( echo   Client: Claude Code ^(workspace^) & echo   Config: !CODE_CONFIG! )
    call :_configure_one_path "!CODE_CONFIG!" "!_vp!" "!_sp!" "Claude Code"
)
goto :eof

:cc_cursor
if not "!UNINSTALL!"=="true" ( echo   Client: Cursor & echo   Config: !CURSOR_CONFIG! )
call :_configure_one_path "!CURSOR_CONFIG!" "!_vp!" "!_sp!" "Cursor"
goto :eof

:cc_windsurf
if not "!UNINSTALL!"=="true" ( echo   Client: Windsurf ^(global^) & echo   Config: !WINDSURF_CONFIG! )
call :_configure_one_path "!WINDSURF_CONFIG!" "!_vp!" "!_sp!" "Windsurf"
goto :eof

:cc_vscode
if "!UNINSTALL!"=="true" (
    if exist "!VSCODE_CONFIG!" "!_vp!" "!PY_REMOVE_VSCODE!" "!VSCODE_CONFIG!"
) else (
    echo   Client: VS Code ^(workspace^)
    echo   Config: !VSCODE_CONFIG!
    echo   Note: for global VS Code config, use the VS Code command palette
    if exist "!VSCODE_CONFIG!" (
        for /f "tokens=*" %%T in ('powershell -command "Get-Date -Format yyyyMMddHHmmss"') do set "_ts=%%T"
        copy /y "!VSCODE_CONFIG!" "!VSCODE_CONFIG!.backup.!_ts!" >nul
        echo   Backed up existing config
    )
    "!_vp!" "!PY_MERGE_VSCODE!" "!VSCODE_CONFIG!" "!_sp!"
    echo   OK: MCP config updated
)
goto :eof

:cc_gemini
if not "!UNINSTALL!"=="true" ( echo   Client: Gemini CLI & echo   Config: !GEMINI_CONFIG! )
call :_configure_one_path "!GEMINI_CONFIG!" "!_vp!" "!_sp!" "Gemini CLI"
goto :eof

:cc_codex
if "!UNINSTALL!"=="true" (
    if exist "!CODEX_CONFIG!" "!_vp!" "!PY_REMOVE_CODEX!" "!CODEX_CONFIG!"
) else (
    echo   Client: OpenAI Codex CLI
    echo   Config: !CODEX_CONFIG!
    if exist "!CODEX_CONFIG!" (
        for /f "tokens=*" %%T in ('powershell -command "Get-Date -Format yyyyMMddHHmmss"') do set "_ts=%%T"
        copy /y "!CODEX_CONFIG!" "!CODEX_CONFIG!.backup.!_ts!" >nul
        echo   Backed up existing config
    )
    "!_vp!" "!PY_MERGE_CODEX!" "!CODEX_CONFIG!" "!_sp!"
    echo   OK: MCP config updated
)
goto :eof

:cc_zed
if "!UNINSTALL!"=="true" (
    if exist "!ZED_CONFIG!" "!_vp!" "!PY_REMOVE_ZED!" "!ZED_CONFIG!"
) else (
    echo   Client: Zed ^(global^)
    echo   Config: !ZED_CONFIG!
    if exist "!ZED_CONFIG!" (
        for /f "tokens=*" %%T in ('powershell -command "Get-Date -Format yyyyMMddHHmmss"') do set "_ts=%%T"
        copy /y "!ZED_CONFIG!" "!ZED_CONFIG!.backup.!_ts!" >nul
        echo   Backed up existing config
    )
    "!_vp!" "!PY_MERGE_ZED!" "!ZED_CONFIG!" "!_sp!"
    echo   OK: MCP config updated
)
goto :eof

:cc_kilo
if not "!UNINSTALL!"=="true" ( echo   Client: Kilo Code & echo   Config: !KILO_CONFIG! )
call :_configure_one_path "!KILO_CONFIG!" "!_vp!" "!_sp!" "Kilo Code"
goto :eof

:cc_opencode
if "!UNINSTALL!"=="true" (
    if exist "!OPENCODE_CONFIG!" "!_vp!" "!PY_REMOVE_OPENCODE!" "!OPENCODE_CONFIG!"
) else (
    echo   Client: OpenCode
    echo   Config: !OPENCODE_CONFIG!
    if exist "!OPENCODE_CONFIG!" (
        for /f "tokens=*" %%T in ('powershell -command "Get-Date -Format yyyyMMddHHmmss"') do set "_ts=%%T"
        copy /y "!OPENCODE_CONFIG!" "!OPENCODE_CONFIG!.backup.!_ts!" >nul
        echo   Backed up existing config
    )
    "!_vp!" "!PY_MERGE_OPENCODE!" "!OPENCODE_CONFIG!" "!_sp!"
    echo   OK: MCP config updated
)
goto :eof

:cc_goose
if not "!UNINSTALL!"=="true" ( echo   Client: Goose & echo   Config: !GOOSE_CONFIG! )
if "!UNINSTALL!"=="true" (
    if exist "!GOOSE_CONFIG!" (
        for /f "tokens=*" %%T in ('powershell -command "Get-Date -Format yyyyMMddHHmmss"') do set "_ts=%%T"
        copy /y "!GOOSE_CONFIG!" "!GOOSE_CONFIG!.backup.!_ts!" >nul
        "!_vp!" "!PY_REMOVE_GOOSE!" "!GOOSE_CONFIG!"
    )
) else (
    if exist "!GOOSE_CONFIG!" (
        for /f "tokens=*" %%T in ('powershell -command "Get-Date -Format yyyyMMddHHmmss"') do set "_ts=%%T"
        copy /y "!GOOSE_CONFIG!" "!GOOSE_CONFIG!.backup.!_ts!" >nul
        echo   Backed up existing config
    )
    "!_vp!" "!PY_MERGE_GOOSE!" "!GOOSE_CONFIG!" "!_sp!"
    echo   OK: MCP config updated
)
goto :eof

:cc_pidev
echo   Client: pi.dev
echo.
echo   pi.dev does not support MCP servers natively.
echo   pi.dev uses TypeScript extensions and CLI tools instead.
echo   To use mageNT concepts in pi.dev, see: https://pi.dev/docs/extensions
echo.
goto :eof

:cc_both
call :configure_client "claudedesktop" "!_vp!" "!_sp!"
echo.
call :configure_client "claude" "!_vp!" "!_sp!"
goto :eof

:cc_all
call :configure_client "claudedesktop" "!_vp!" "!_sp!"
echo.
call :configure_client "claude" "!_vp!" "!_sp!"
if "!UNINSTALL!"=="true" (
    echo. & call :configure_client "cursor" "!_vp!" "!_sp!"
    echo. & call :configure_client "windsurf" "!_vp!" "!_sp!"
    echo. & call :configure_client "vscode" "!_vp!" "!_sp!"
    echo. & call :configure_client "gemini" "!_vp!" "!_sp!"
    echo. & call :configure_client "codex" "!_vp!" "!_sp!"
    echo. & call :configure_client "zed" "!_vp!" "!_sp!"
    echo. & call :configure_client "kilo" "!_vp!" "!_sp!"
    echo. & call :configure_client "opencode" "!_vp!" "!_sp!"
    echo. & call :configure_client "goose" "!_vp!" "!_sp!"
) else (
    if exist "!_PARENT!\.cursor\mcp.json" ( echo. & call :configure_client "cursor" "!_vp!" "!_sp!" )
    if exist "!USERPROFILE!\.cursor\mcp.json" ( echo. & call :configure_client "cursor" "!_vp!" "!_sp!" )
    if exist "!WINDSURF_CONFIG!" ( echo. & call :configure_client "windsurf" "!_vp!" "!_sp!" )
    if exist "!VSCODE_CONFIG!" ( echo. & call :configure_client "vscode" "!_vp!" "!_sp!" )
    if exist "!_PARENT!\.gemini\settings.json" ( echo. & call :configure_client "gemini" "!_vp!" "!_sp!" )
    if exist "!USERPROFILE!\.gemini\settings.json" ( echo. & call :configure_client "gemini" "!_vp!" "!_sp!" )
    if exist "!_PARENT!\.codex\config.toml" ( echo. & call :configure_client "codex" "!_vp!" "!_sp!" )
    if exist "!USERPROFILE!\.codex\config.toml" ( echo. & call :configure_client "codex" "!_vp!" "!_sp!" )
    if exist "!ZED_CONFIG!" ( echo. & call :configure_client "zed" "!_vp!" "!_sp!" )
    if exist "!KILO_CONFIG!" ( echo. & call :configure_client "kilo" "!_vp!" "!_sp!" )
    if exist "!OPENCODE_CONFIG!" ( echo. & call :configure_client "opencode" "!_vp!" "!_sp!" )
    if exist "!USERPROFILE!\.config\opencode\opencode.json" ( echo. & call :configure_client "opencode" "!_vp!" "!_sp!" )
    if exist "!GOOSE_CONFIG!" ( echo. & call :configure_client "goose" "!_vp!" "!_sp!" )
)
goto :eof

rem ════════════════════════════════════════════════════════
:_configure_one_path
set "_cfg=%~1"
set "_vp2=%~2"
set "_sp2=%~3"
set "_lbl=%~4"

if "!UNINSTALL!"=="true" (
    if exist "!_cfg!" (
        for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMddHHmmss"`) do set "_ts=%%T"
        copy /y "!_cfg!" "!_cfg!.backup.!_ts!" >nul
        "!_vp2!" "!PY_REMOVE!" "!_cfg!" "!_lbl!"
    )
    goto :eof
)

if exist "!_cfg!" (
    if not "!FORCE!"=="true" (
        for /f "usebackq delims=" %%R in (`"!_vp2!" "!PY_CHECK!" "!_cfg!" "!_vp2!" 2^>nul`) do set "_chk=%%R"
        if "!_chk!"=="uptodate" (
            echo   MCP config already up to date
            goto :eof
        )
        if "!_chk!"=="changed" (
            echo   Updating MCP config ^(python path changed^)
        )
    )
)

if exist "!_cfg!" (
    for /f "tokens=*" %%T in ('powershell -command "Get-Date -Format yyyyMMddHHmmss"') do set "_ts=%%T"
    copy /y "!_cfg!" "!_cfg!.backup.!_ts!" >nul
    echo   Backed up existing config
)

"!_vp2!" "!PY_MERGE!" "!_cfg!" "!_sp2!"
echo   OK: MCP config updated
goto :eof
