@echo off
setlocal enabledelayedexpansion

rem ── Config ──────────────────────────────────────────────
set "MARKER_FILE=.magent-installed"
set "MAGENT_DIR=%~dp0"
if "!MAGENT_DIR:~-1!"=="\" set "MAGENT_DIR=!MAGENT_DIR:~0,-1!"

rem ── Defaults ────────────────────────────────────────────
set "FORCE=false"
set "UNINSTALL=false"
set "UPDATE=false"
set "CLIENT=desktop"
set "SKIP_TEST=false"
set "GLOBAL_CONFIG=false"
set "CLIENT_EXPLICIT=false"

goto :parse_args

rem ════════════════════════════════════════════════════════
:show_help
echo Usage: install.bat [options]
echo.
echo Options:
echo   -c, --client TYPE   MCP client: desktop, code, both (default: desktop)
echo   -f, --force         Skip prompts, overwrite existing config
echo   -u, --uninstall     Remove mageNT from MCP client config
echo       --update        Upgrade deps and merge new agents into existing config.yaml
echo       --global        Write Claude Code config to %%USERPROFILE%%\.claude\mcp.json
echo                       Default (no --global): writes to parent workspace dir
echo       --skip-test     Skip test_server.py validation
echo   -h, --help          Show this help
echo.
echo Examples:
echo   install.bat                    Install for Claude Desktop
echo   install.bat -c code            Install for Claude Code (workspace-local)
echo   install.bat -c code --global   Install for Claude Code (global config)
echo   install.bat -c both            Install for both
echo   install.bat --update           Upgrade deps ^& config
echo   install.bat --update -c code   Upgrade + reconfigure Claude Code MCP path
echo   install.bat -u                 Uninstall
echo   install.bat -u --global        Uninstall from global Claude Code config
echo   install.bat -f --skip-test     Force install, skip tests
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

rem ── Validate --global ────────────────────────────────────
if "!GLOBAL_CONFIG!"=="true" (
    if not "!CLIENT!"=="code" (
        if not "!CLIENT!"=="both" (
            echo   ERROR: --global is only valid with -c code or -c both >&2
            exit /b 1
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

if "!GLOBAL_CONFIG!"=="true" (
    set "CODE_CONFIG=!USERPROFILE!\.claude\mcp.json"
) else (
    for %%I in ("!MAGENT_DIR!") do set "_PARENT=%%~dpI"
    if "!_PARENT:~-1!"=="\" set "_PARENT=!_PARENT:~0,-1!"
    set "CODE_CONFIG=!_PARENT!\.mcp.json"
)

rem ── Write Python helpers to temp files ───────────────────
set "PY_MERGE=!TEMP!\magent_merge.py"
set "PY_REMOVE=!TEMP!\magent_remove.py"
set "PY_CHECK=!TEMP!\magent_check.py"
set "PY_MIGRATE=!TEMP!\magent_migrate.py"

echo import json, sys, os > "!PY_MERGE!"
echo config_path = os.path.abspath(sys.argv[1]) >> "!PY_MERGE!"
echo python_path = sys.executable >> "!PY_MERGE!"
echo server_py = os.path.abspath(sys.argv[2]) >> "!PY_MERGE!"
echo try: >> "!PY_MERGE!"
echo     with open(config_path) as f: >> "!PY_MERGE!"
echo         config = json.load(f) >> "!PY_MERGE!"
echo except (FileNotFoundError, json.JSONDecodeError): >> "!PY_MERGE!"
echo     config = {} >> "!PY_MERGE!"
echo config.setdefault('mcpServers', {}) >> "!PY_MERGE!"
echo config['mcpServers']['magent'] = {'command': python_path, 'args': [server_py]} >> "!PY_MERGE!"
echo d = os.path.dirname(os.path.abspath(config_path)) >> "!PY_MERGE!"
echo if d: os.makedirs(d, exist_ok=True) >> "!PY_MERGE!"
echo with open(config_path, 'w') as f: >> "!PY_MERGE!"
echo     json.dump(config, f, indent=2) >> "!PY_MERGE!"
echo     f.write('\n') >> "!PY_MERGE!"

echo import json, sys, os > "!PY_REMOVE!"
echo config_path = sys.argv[1] >> "!PY_REMOVE!"
echo if not os.path.exists(config_path): sys.exit(0) >> "!PY_REMOVE!"
echo try: >> "!PY_REMOVE!"
echo     with open(config_path) as f: >> "!PY_REMOVE!"
echo         config = json.load(f) >> "!PY_REMOVE!"
echo except (FileNotFoundError, json.JSONDecodeError): sys.exit(0) >> "!PY_REMOVE!"
echo servers = config.get('mcpServers', {}) >> "!PY_REMOVE!"
echo if 'magent' in servers: >> "!PY_REMOVE!"
echo     del servers['magent'] >> "!PY_REMOVE!"
echo     with open(config_path, 'w') as f: >> "!PY_REMOVE!"
echo         json.dump(config, f, indent=2) >> "!PY_REMOVE!"
echo         f.write('\n') >> "!PY_REMOVE!"
echo     print('  Removed magent from config') >> "!PY_REMOVE!"
echo else: print('  magent not found in config') >> "!PY_REMOVE!"

echo import json, sys, os > "!PY_CHECK!"
echo config_path = sys.argv[1] >> "!PY_CHECK!"
echo venv_python = sys.argv[2] >> "!PY_CHECK!"
echo try: >> "!PY_CHECK!"
echo     with open(config_path) as f: >> "!PY_CHECK!"
echo         c = json.load(f) >> "!PY_CHECK!"
echo     entry = c.get('mcpServers', {}).get('magent', {}) >> "!PY_CHECK!"
echo     cmd = entry.get('command', '') >> "!PY_CHECK!"
echo     if cmd == venv_python: print('uptodate') >> "!PY_CHECK!"
echo     elif cmd: print('changed') >> "!PY_CHECK!"
echo     else: print('missing') >> "!PY_CHECK!"
echo except: print('missing') >> "!PY_CHECK!"

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

rem ── Banner ───────────────────────────────────────────────
echo.
echo   mageNT v!VERSION!
if "!UPDATE!"=="true" (
    if not "!INSTALLED_VERSION!"=="" (
        if not "!INSTALLED_VERSION!"=="!VERSION!" (
            echo   Upgrading from v!INSTALLED_VERSION!
        )
    )
)
if "!UNINSTALL!"=="true" (
    echo   Mode: uninstall
) else if "!UPDATE!"=="true" (
    echo   Mode: update
) else (
    echo   Mode: install ^(client: !CLIENT!^)
)
echo   -----------------------------
echo.

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

if "!CLIENT!"=="both" (
    call :configure_client "desktop" "!VENV_PYTHON!" ""
    call :configure_client "code" "!VENV_PYTHON!" ""
) else (
    call :configure_client "!CLIENT!" "!VENV_PYTHON!" ""
)

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
                echo   Use --update -c code^|both to also reconfigure MCP client.
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

rem 2b. Reconfigure MCP client if -c was explicit
if "!CLIENT_EXPLICIT!"=="true" (
    echo   Reconfiguring MCP client ^(!CLIENT!^)...
    set "SERVER_PY=!MAGENT_DIR!\server.py"
    if "!CLIENT!"=="both" (
        call :configure_client "desktop" "!VENV_PYTHON!" "!SERVER_PY!"
        echo.
        call :configure_client "code" "!VENV_PYTHON!" "!SERVER_PY!"
    ) else (
        call :configure_client "!CLIENT!" "!VENV_PYTHON!" "!SERVER_PY!"
    )
    echo.
)

rem 3. Run tests
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

rem 4. Update marker
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

rem Early exit if already at this version
if not "!INSTALLED_VERSION!"=="" (
    if "!INSTALLED_VERSION!"=="!VERSION!" (
        if not "!FORCE!"=="true" (
            echo   Already at v!VERSION!. Nothing to do.
            echo   Use --update to upgrade dependencies, or -f to force reinstall.
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
if "!CLIENT!"=="both" (
    call :configure_client "desktop" "!VENV_PYTHON!" "!SERVER_PY!"
    echo.
    call :configure_client "code" "!VENV_PYTHON!" "!SERVER_PY!"
) else (
    call :configure_client "!CLIENT!" "!VENV_PYTHON!" "!SERVER_PY!"
)
echo.

rem 7. Write marker
echo !VERSION!> "!MAGENT_DIR!\!MARKER_FILE!"

rem ── Done ─────────────────────────────────────────────────
echo   -----------------------------
echo   mageNT installed successfully!
echo.
echo   Next steps:
if "!CLIENT!"=="code" (
    echo   1. Open the workspace in Claude Code
    echo   2. Try: "List the available agents"
) else (
    echo   1. Restart Claude Desktop (quit fully, then reopen)
    echo   2. Try: "List the available agents"
)
echo.

:cleanup
rem Clean up temp files
del /f /q "!PY_MERGE!" "!PY_REMOVE!" "!PY_CHECK!" "!PY_MIGRATE!" 2>nul
endlocal
exit /b 0

rem ════════════════════════════════════════════════════════
rem Subroutine: find_python
rem Sets SYSTEM_PYTHON to first Python 3.10+ found
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
rem Subroutine: find_venv_python
rem Sets VENV_PYTHON if venv exists
:find_venv_python
set "VENV_PYTHON="
if exist "!MAGENT_DIR!\.venv\Scripts\python.exe" (
    set "VENV_PYTHON=!MAGENT_DIR!\.venv\Scripts\python.exe"
) else if exist "!MAGENT_DIR!\.venv\bin\python.exe" (
    set "VENV_PYTHON=!MAGENT_DIR!\.venv\bin\python.exe"
)
goto :eof

rem ════════════════════════════════════════════════════════
rem Subroutine: configure_client <client_type> <venv_python> <server_py>
:configure_client
set "_ct=%~1"
set "_vp=%~2"
set "_sp=%~3"

if "!_ct!"=="desktop" (
    set "_cfg=!DESKTOP_CONFIG!"
    echo   Client: Claude Desktop
) else (
    set "_cfg=!CODE_CONFIG!"
    echo   Client: Claude Code
)
echo   Config: !_cfg!

if "!UNINSTALL!"=="true" (
    if exist "!_cfg!" (
        for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMddHHmmss"`) do set "_ts=%%T"
        copy /y "!_cfg!" "!_cfg!.backup.!_ts!" >nul
        "!_vp!" "!PY_REMOVE!" "!_cfg!"
    ) else (
        echo   Config not found, nothing to remove
    )
    goto :eof
)

rem Check if up to date
if exist "!_cfg!" (
    if not "!FORCE!"=="true" (
        for /f "usebackq delims=" %%R in (`"!_vp!" "!PY_CHECK!" "!_cfg!" "!_vp!" 2^>nul`) do set "_chk=%%R"
        if "!_chk!"=="uptodate" (
            echo   MCP config already up to date
            goto :eof
        )
        if "!_chk!"=="changed" (
            echo   Updating MCP config ^(python path changed^)
        )
    )
)

rem Backup if exists
if exist "!_cfg!" (
    for /f "tokens=*" %%T in ('powershell -command "Get-Date -Format 'yyyyMMddHHmmss'"') do set "_ts=%%T"
    copy /y "!_cfg!" "!_cfg!.backup.!_ts!" >nul
    echo   Backed up existing config
)

"!_vp!" "!PY_MERGE!" "!_cfg!" "!_sp!"
echo   OK: MCP config updated
goto :eof
