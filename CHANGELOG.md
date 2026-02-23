# Changelog

All notable changes to mageNT are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.2.0] - 2026-02-23

### Added

#### New Agents (13)

**Development — Frontend**
- `svelte_developer` — Svelte, SvelteKit, Sapper, TypeScript, Vite

**Development — Backend**
- `integration_specialist` — REST/GraphQL APIs, Webhooks, Message Queues, ETL, Third-party SDKs
- `rust_backend` — Rust, Tokio, Axum, Actix-web, Cargo, WebAssembly

**Development — Mobile (4 specialists replacing the generic agent)**
- `flutter_developer` — Flutter, Dart, Riverpod, Bloc, platform channels
- `react_native_developer` — React Native, Expo, EAS Build/Update, Detox, Maestro
- `android_developer` — Kotlin, Java, Jetpack Compose, MVVM, Hilt, Coroutines
- `ios_developer` — Swift, Objective-C, SwiftUI, UIKit, async/await, XCUITest

**Business**
- `delivery_manager` — SDLC completion audits, go/no-go readiness reports, Definition of Done

#### New Workflows (4)

- `new_system` — Full 15-step greenfield project lifecycle (requirements → design → dev → test → docs → deployment → sign-off)
- `add_feature` — 10-step feature addition with impact analysis, QA, and delivery sign-off
- `bug_fix` — 7-step diagnose → fix → regression → sign-off workflow
- `full_audit` — 9-step comprehensive health check across architecture, security, performance, QA, CI/CD, and docs

#### Installer

- Added `--update` flag to `install.sh` — upgrades dependencies and merges new agent/workflow blocks into existing `config.yaml` without overwriting user customizations

### Changed

#### Agent Enhancements

- `java_backend` — added Spring WebFlux, Spring AMQP/Kafka responsibilities; Spring Boot DevTools, Actuator, and profiles best practices; updated specialization to include Spring Framework and Gradle
- `go_backend` — added Tauri desktop app responsibilities and best practices; updated specialization to include Tauri
- `qa_engineer` — significantly expanded to cover manual testing (exploratory, regression, test case authoring), test management tools (TestRail, Xray, Zephyr), BDD (Cucumber, pytest-bdd), API testing (Postman, REST Assured), and explicit tool coverage (Jest, Pytest, JUnit, NUnit, Mocha)
- `automation_qa` — expanded to cover full E2E toolchain (Playwright, Cypress, Selenium, WebdriverIO, TestCafe, Puppeteer), mobile automation (Appium, Detox, Maestro, XCUITest, Espresso), API automation (Newman, REST Assured, Karate, SoapUI), performance testing (k6, Gatling, Locust, Artillery), visual regression (Percy, Chromatic, Applitools), contract testing (Pact, Spring Cloud Contract), BDD (Cucumber, SpecFlow, Behave), and reporting (Allure, ReportPortal)

#### Workflow Improvements

- `full_stack_web` — added UI/UX Designer, Security Engineer, Automation QA, Technical Writer, Delivery Manager steps
- `mobile_app` — added Security Engineer, Automation QA, Technical Writer, Delivery Manager steps
- `saas_platform` — added Product Manager, UI/UX Designer, QA Engineer, Automation QA, Technical Writer, Delivery Manager steps
- `multi_tenant_app` — added QA Engineer, DevOps Engineer, Delivery Manager steps
- `legacy_migration` — added Security Engineer, Technical Writer, Delivery Manager steps

#### Documentation

- `config.example.yaml` — updated to include all new agents and workflows; updated stale specializations
- `README.md` — updated agent count (24 → 32), expanded team table, updated workflow list

---

## [0.1.0] - Initial Release

- 24 specialist agents across business, development, data, infrastructure, and quality domains
- 19 workflow templates
- Rules engine with security, style, testing, git, and performance categories
- Automation hooks (pre-commit, pre-edit, post-edit, session lifecycle)
- Cross-platform installer (`install.sh`) supporting Claude Desktop and Claude Code
