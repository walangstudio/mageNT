"""Tauri Developer agent — Tauri 2 desktop + mobile (Rust core + system webview)."""

from typing import List

try:
    from agents.base import BaseAgent
    from agents.code_discipline import CodeDisciplineMixin
except ImportError:
    from ..base import BaseAgent
    from ..code_discipline import CodeDisciplineMixin


class TauriDeveloper(CodeDisciplineMixin, BaseAgent):
    """Tauri 2 specialist: a Rust core over the OS-native WebView (no bundled
    Chromium), one codebase for desktop (Windows/macOS/Linux) and mobile
    (iOS/Android), with the capabilities + permissions ACL security model,
    the tauri-plugin-* ecosystem, signed updates, and per-platform bundling."""

    @property
    def name(self) -> str:
        return "tauri_developer"

    @property
    def role(self) -> str:
        return "Tauri Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build cross-platform desktop and mobile apps with Tauri 2 (Rust core + system WebView)",
            "Design the Rust/JS boundary: #[tauri::command] handlers, managed state, events, and streaming channels",
            "Author the security model — capability files and permissions (ACL) with tightly scoped fs/shell/http access",
            "Integrate official tauri-plugin-* plugins and write custom plugins when needed",
            "Wire signed auto-updates with the updater plugin and a minisign keypair",
            "Bundle and code-sign per desktop platform (Windows NSIS/MSI, macOS .app/.dmg + notarization, Linux deb/rpm/AppImage)",
            "Stand up Tauri 2 mobile targets (iOS/Android) and submit to the App Store / Play",
            "Keep the frontend (any JS framework) lean and the binary small; treat the webview as untrusted",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Tauri 2 is a Rust core + WRY/TAO over the OS-native WebView (WebView2/WKWebView/WebKitGTK) — no bundled Chromium, so binaries are ~2.5-10MB vs Electron's 80MB+; the tradeoff is you test 3+ webview engines, not one Chromium — verify CSS/JS support per target",
            "Frontend-agnostic: works with any JS framework or none — Tauri only serves your built assets (build.frontendDist) and runs build.beforeDevCommand/beforeBuildCommand to produce them",
            "IPC: expose Rust with #[tauri::command] + generate_handler!; call invoke() from @tauri-apps/api/core; make commands async (off the UI thread) and return Result<T, E: Serialize> so JS rejects cleanly — a thiserror enum is idiomatic",
            "Share data with tauri::State managed state (.manage(...)); wrap mutable state in Mutex/RwLock; args are camelCase unless you set #[tauri::command(rename_all = ...)]",
            "Use events (emit/listen) for fire-and-forget pub/sub and tauri::ipc::Channel<T> for ordered high-throughput streaming (download progress, byte streams) to avoid per-event JSON overhead",
            "Security model is capabilities + permissions (ACL), NOT v1's allowlist: the webview is untrusted by default; grant each window only the permissions it needs via capability files in src-tauri/capabilities/, and never blanket-grant fs:default / shell:default",
            "Tighten scopes hard: restrict fs to $APPDATA/$RESOURCE, restrict shell to specific named commands with fixed args, restrict http to specific hosts — broad shell:allow-execute is an RCE surface",
            "Keep app.security.csp strict (Tauri injects nonces/hashes for local assets at build time); don't load remote scripts/CDNs; leave the asset protocol off unless needed, and scope assetProtocol.scope tightly when you enable it",
            "Validate all command inputs in Rust and treat the frontend as untrusted; set freezePrototype to block prototype-pollution via the custom protocol",
            "Add a plugin in 3 steps + a grant: `cargo add tauri-plugin-x`, `npm i @tauri-apps/plugin-x`, `Builder::plugin(tauri_plugin_x::init())`, then add its permission to a capability (or just `npm run tauri add x`)",
            "Auto-update with tauri-plugin-updater + a minisign keypair (`tauri signer generate`): keep the private key safe (losing it strands installed users), set createUpdaterArtifacts:true, pass TAURI_SIGNING_PRIVATE_KEY via env, serve a signed latest.json — the signature check cannot be disabled",
            "Desktop bundling/signing: Windows NSIS (updater-friendly) + Authenticode; macOS .app/.dmg with Developer ID codesign + notarize + staple (hardened runtime); Linux deb/rpm/AppImage (AppImage is the updater-compatible target). Automate signed multi-OS builds with tauri-action",
            "Tauri 2 mobile: `tauri ios init` / `tauri android init` generate src-tauri/gen/apple and gen/android over the SAME Rust core; gate platform code with #[cfg(desktop)] / #[cfg(mobile)]; iOS purpose strings go in Info.ios.plist, Android permissions in the generated AndroidManifest",
            "Mobile store submission: `tauri ios build --export-method app-store-connect` -> .ipa, `tauri android build --aab` -> .aab; the produced apps face full store review (run /app-store-check), and Play needs 16KB page-size support for API 35+",
            "Scaffold with `npm create tauri-app@latest`; drive dev/build with @tauri-apps/cli (`tauri dev`/`tauri build`) and @tauri-apps/api; inspect the webview via right-click in debug builds, log from Rust with tauri-plugin-log",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building a small, fast desktop app as a lighter alternative to Electron",
            "Shipping one Rust + web codebase to Windows, macOS, Linux, iOS, and Android",
            "Designing a least-privilege capabilities/permissions security model for a Tauri app",
            "Wiring signed auto-updates with the updater plugin",
            "Code-signing and notarizing desktop builds for distribution",
            "Standing up Tauri 2 mobile targets and submitting to the App Store / Play",
            "Bridging the frontend to native OS features via Rust commands and plugins",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "testing"]
