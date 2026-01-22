"""Version Provider - Fetch latest stable versions from package registries."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


class VersionCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[str]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        """Set cache value with current timestamp."""
        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


class VersionProvider:
    """Fetch latest stable package versions from various registries."""

    # Registry base URLs
    REGISTRIES = {
        "npm": "https://registry.npmjs.org",
        "pypi": "https://pypi.org/pypi",
        "maven": "https://search.maven.org/solrsearch/select",
        "nuget": "https://api.nuget.org/v3-flatcontainer",
        "go": "https://proxy.golang.org",
        "cargo": "https://crates.io/api/v1/crates",
        "rubygems": "https://rubygems.org/api/v1/gems",
    }

    def __init__(self, cache_ttl: int = 3600):
        """Initialize the version provider.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 1 hour)
        """
        self._cache = VersionCache(cache_ttl)
        self._timeout = 10  # Request timeout in seconds

    def _make_request(self, url: str, headers: Optional[Dict] = None) -> Optional[str]:
        """Make HTTP request and return response body."""
        try:
            req = Request(url)
            req.add_header("User-Agent", "mageNT-VersionProvider/1.0")
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)

            with urlopen(req, timeout=self._timeout) as response:
                return response.read().decode("utf-8")
        except (URLError, HTTPError, TimeoutError) as e:
            print(f"Request failed for {url}: {e}")
            return None

    def get_npm_version(self, package: str) -> Optional[str]:
        """Get latest version from npm registry."""
        cache_key = f"npm:{package}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.REGISTRIES['npm']}/{package}/latest"
        response = self._make_request(url)

        if response:
            try:
                data = json.loads(response)
                version = data.get("version")
                if version:
                    self._cache.set(cache_key, version)
                    return version
            except json.JSONDecodeError:
                pass
        return None

    def get_pypi_version(self, package: str) -> Optional[str]:
        """Get latest version from PyPI."""
        cache_key = f"pypi:{package}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.REGISTRIES['pypi']}/{package}/json"
        response = self._make_request(url)

        if response:
            try:
                data = json.loads(response)
                version = data.get("info", {}).get("version")
                if version:
                    self._cache.set(cache_key, version)
                    return version
            except json.JSONDecodeError:
                pass
        return None

    def get_maven_version(self, group: str, artifact: str) -> Optional[str]:
        """Get latest version from Maven Central.

        Args:
            group: Maven group ID (e.g., 'org.springframework.boot')
            artifact: Maven artifact ID (e.g., 'spring-boot-starter')
        """
        cache_key = f"maven:{group}:{artifact}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.REGISTRIES['maven']}?q=g:{group}+AND+a:{artifact}&rows=1&wt=json"
        response = self._make_request(url)

        if response:
            try:
                data = json.loads(response)
                docs = data.get("response", {}).get("docs", [])
                if docs:
                    version = docs[0].get("latestVersion")
                    if version:
                        self._cache.set(cache_key, version)
                        return version
            except json.JSONDecodeError:
                pass
        return None

    def get_nuget_version(self, package: str) -> Optional[str]:
        """Get latest version from NuGet."""
        cache_key = f"nuget:{package}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        # First get the list of versions
        url = f"{self.REGISTRIES['nuget']}/{package.lower()}/index.json"
        response = self._make_request(url)

        if response:
            try:
                data = json.loads(response)
                versions = data.get("versions", [])
                if versions:
                    # Filter out pre-release versions
                    stable_versions = [
                        v for v in versions
                        if "-" not in v  # Pre-release versions contain hyphen
                    ]
                    if stable_versions:
                        version = stable_versions[-1]  # Latest stable
                        self._cache.set(cache_key, version)
                        return version
            except json.JSONDecodeError:
                pass
        return None

    def get_go_version(self, module: str) -> Optional[str]:
        """Get latest version from Go proxy.

        Args:
            module: Go module path (e.g., 'github.com/gin-gonic/gin')
        """
        cache_key = f"go:{module}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.REGISTRIES['go']}/{module}/@latest"
        response = self._make_request(url)

        if response:
            try:
                data = json.loads(response)
                version = data.get("Version")
                if version:
                    self._cache.set(cache_key, version)
                    return version
            except json.JSONDecodeError:
                pass
        return None

    def get_cargo_version(self, crate: str) -> Optional[str]:
        """Get latest version from crates.io."""
        cache_key = f"cargo:{crate}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.REGISTRIES['cargo']}/{crate}"
        response = self._make_request(url)

        if response:
            try:
                data = json.loads(response)
                version = data.get("crate", {}).get("newest_version")
                if version:
                    self._cache.set(cache_key, version)
                    return version
            except json.JSONDecodeError:
                pass
        return None

    def get_rubygems_version(self, gem: str) -> Optional[str]:
        """Get latest version from RubyGems."""
        cache_key = f"rubygems:{gem}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        url = f"{self.REGISTRIES['rubygems']}/{gem}.json"
        response = self._make_request(url)

        if response:
            try:
                data = json.loads(response)
                version = data.get("version")
                if version:
                    self._cache.set(cache_key, version)
                    return version
            except json.JSONDecodeError:
                pass
        return None

    def get_latest_version(self, registry: str, package: str) -> Optional[str]:
        """Get latest version from specified registry.

        Args:
            registry: One of 'npm', 'pypi', 'maven', 'nuget', 'go', 'cargo', 'rubygems'
            package: Package name (for maven, use 'group:artifact' format)
        """
        registry = registry.lower()

        if registry == "npm":
            return self.get_npm_version(package)
        elif registry == "pypi":
            return self.get_pypi_version(package)
        elif registry == "maven":
            parts = package.split(":")
            if len(parts) == 2:
                return self.get_maven_version(parts[0], parts[1])
            return None
        elif registry == "nuget":
            return self.get_nuget_version(package)
        elif registry == "go":
            return self.get_go_version(package)
        elif registry == "cargo":
            return self.get_cargo_version(package)
        elif registry == "rubygems":
            return self.get_rubygems_version(package)
        else:
            print(f"Unknown registry: {registry}")
            return None

    def get_multiple_versions(
        self, packages: List[Dict[str, str]]
    ) -> Dict[str, Optional[str]]:
        """Get versions for multiple packages.

        Args:
            packages: List of dicts with 'registry' and 'package' keys

        Returns:
            Dict mapping package names to versions
        """
        results = {}
        for pkg in packages:
            registry = pkg.get("registry", "npm")
            package = pkg.get("package", "")
            if package:
                key = f"{registry}:{package}"
                results[key] = self.get_latest_version(registry, package)
        return results

    def get_common_versions(self) -> Dict[str, Dict[str, Optional[str]]]:
        """Get versions for commonly used packages across registries."""
        common_packages = {
            "npm": [
                "react", "next", "vue", "express", "fastify",
                "typescript", "vite", "vitest", "prisma"
            ],
            "pypi": [
                "fastapi", "django", "flask", "sqlalchemy",
                "pydantic", "pytest", "httpx"
            ],
        }

        results = {}
        for registry, packages in common_packages.items():
            results[registry] = {}
            for package in packages:
                results[registry][package] = self.get_latest_version(registry, package)

        return results


# Convenience function for direct usage
def get_version(registry: str, package: str) -> Optional[str]:
    """Quick helper to get a package version."""
    provider = VersionProvider()
    return provider.get_latest_version(registry, package)


if __name__ == "__main__":
    # Test the version provider
    provider = VersionProvider()

    print("Testing npm:")
    print(f"  react: {provider.get_npm_version('react')}")
    print(f"  express: {provider.get_npm_version('express')}")

    print("\nTesting PyPI:")
    print(f"  fastapi: {provider.get_pypi_version('fastapi')}")
    print(f"  django: {provider.get_pypi_version('django')}")

    print("\nTesting cargo:")
    print(f"  tokio: {provider.get_cargo_version('tokio')}")

    print("\nTesting RubyGems:")
    print(f"  rails: {provider.get_rubygems_version('rails')}")
