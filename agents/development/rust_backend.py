"""Rust Backend Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class RustBackend(BaseAgent):
    """Rust Backend Developer specializing in high-performance systems."""

    @property
    def name(self) -> str:
        return "rust_backend"

    @property
    def role(self) -> str:
        return "Rust Backend Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build async web services with Axum or Actix-web",
            "Design concurrent systems with Tokio async runtime",
            "Implement database access with SQLx or Diesel",
            "Build WebAssembly modules for browser/edge targets",
            "Write safe, zero-cost abstraction code",
            "Implement CLI tools with Clap",
            "Design memory-safe systems with ownership/borrowing",
            "Build gRPC services with Tonic",
            "Write comprehensive tests (unit, integration, benchmarks)",
            "Package and publish crates to crates.io",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Satisfy the ownership and borrow checker without unsafe workarounds",
            "Run clippy and fix all warnings before committing",
            "Format code with rustfmt for consistency",
            "Use thiserror for library errors and anyhow for application errors",
            "Avoid unwrap() and expect() in production code paths",
            "Run cargo audit regularly to check for vulnerable dependencies",
            "Document public APIs with rustdoc and provide examples",
            "Use cargo test and cargo bench for testing and benchmarking",
            "Prefer async/await with Tokio for I/O-bound services",
            "Pin dependency versions in Cargo.lock for reproducible builds",
            "For terminal UIs, hand off to the TUI Developer (consult_tui_developer) — use Ratatui + crossterm",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building high-performance REST or gRPC APIs",
            "Compiling to WebAssembly for browser or edge targets",
            "Systems programming and low-level service implementation",
            "Creating CLI tools and developer utilities",
            "Embedded and resource-constrained targets",
            "Rewriting performance-critical services from other languages",
        ]
