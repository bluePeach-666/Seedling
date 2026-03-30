# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.1] - 2026-03-29

### Added
- Adds a smart garbage file interceptor (`intercept_garbage_files`) to automatically detect project noise like `node_modules`, `.DS_Store`, and `__pycache__`.
- Adds an intent-aware state machine that silences warnings for power users (who use `-e` or `--nohidden`) and safely downgrades warnings during simple `-f` searches to prevent workflow interruptions.
- Adds fully realized `XmlExporter` and `JsonExporter` that support deep context data (`EstimatedTokens` and `SourceContents`).
- Adds a heuristic Token estimation engine, calculating and displaying `estimated_tokens` based on character weight across all output formats.
- Adds the `--nohidden` flag; hidden files (e.g., `.env`, `.gitignore`) are now scanned by default and are only excluded when this flag is explicitly declared.
- Adds remote repository sandbox routing for `http/https/git@` protocols to instantly clone, scan, and clean up remote codebases.
- Adds an ultimate E2E automated test suite covering 20+ core scenarios with millisecond-level execution and system environment auditing.

### Changed
- Enhances the garbage interceptor with look-ahead filter logic; it now pre-simulates type (`-t`) and exclusion (`-e`) filters and only warns if noise actually penetrates into the final report.
- Refactors `BuildOrchestrator` with explicit boolean logic and improved plugin observability, automatically recording and reporting the names of plugins that intercept builds.
- Unifies the `AbstractExporter` interface to ensure strict structural symmetry across Markdown, JSON, and XML metadata handling.
- Enhances `SkeletonPlugin` robustness by adding strict suffix pre-checks to prevent the AST parser from hanging on non-code or binary files.

### Fixed
- Fixes a logic redundancy where the system would still warn about garbage files that had already been successfully blocked by `-t` or `-e` flags.
- Fixes a type contract error (`reportCallIssue` in Pylance) in the build engine by properly aligning keyword arguments between the orchestrator and physical executor.
- Fixes an interactive deadlock that caused headless/CI environments (non-TTY) to hang while waiting for `stdin`.
- Fixes a search mode interference UX bug where searching for dot-prefixed keywords (e.g., `-f .gitignore`) triggered false-positive garbage warnings.
- Fixes a potential path traversal vulnerability by enforcing strict `resolve()` consistency on `target_path` within `BuildOrchestrator`, fully securing the I/O pipeline.

## [2.5.0] - 2026-03-28

*Note: This is a major architectural refactor, transitioning to a symmetrical orchestrator-based design with unified infrastructure and centralized pattern matching.*

### Added
- Adds `ScanOrchestrator` and a new symmetrical `BuildOrchestrator` to manage advanced modes as modular plugins (completely decoupling parsers, middlewares/plugins, and physical executors).
- Centralizes system interactions into robust global singletons (`logger`, `terminal`, `io_processor`, `image_renderer`).
- Introduces a unified pattern matching engine in `core.patterns` (`fuzzy_match_candidates`, `evaluate_regex_rule`, `evaluate_exact_rule`) serving as a single source of truth for Glob, Regex, and Levenshtein fuzzy logic across the entire codebase.
- Introduces a unified exception hierarchy (`SeedlingToolsError` and derivatives) for precise, context-aware domain error reporting.
- Adds architectural hooks for **v2.5.1 roadmap features**, including a placeholder `XmlExporter`, `estimated_tokens` API in `TraversalResult`, and remote repository detection in the CLI entry point.
- Adds a standardized E2E test suite with 10+ specialized test files to ensure stability across OS environments.
- Adds automatic filename suffixes (e.g., `_analysis.md`, `_grep.md`) when output names are not specified.

### Changed
- Refactors core logic to use Abstract Base Classes (ABCs) for strict domain boundaries and better future extensibility.
- Centralizes all file I/O operations (reading, writing, deleting, and binary signature probing) into `io_processor`, providing global encoding resilience (UTF-8/GBK/UTF-16 fallbacks) and unified exception interception.
- Extracts Markdown tree topology parsing (`parse_tree_topology`) and content comparison logic into `io_processor`, stripping `ProjectArchitect` down to a pure orchestration engine.
- Optimizes path resolution to support non-existent paths during the build process.
- Refactors `main.py` into a thin dispatcher for specialized command modules.
- Optimizes the `--exclude` logic in the `scan` command to support fuzzy matching, improving overall user experience.

### Fixed
- Fixes a critical CLI bug where `scan .` would incorrectly trigger the banner instead of scanning the current directory.
- Fixes the search engine's "directory-blindness" in `SearchPlugin`, now allowing `--find` to correctly match both files and folders (e.g., `__pycache__`).
- Fixes search usability by automatically enabling hidden file scanning if the search keyword starts with a dot (e.g., `scan . -f .gitignore`).
- Fixes `UnicodeDecodeError` crashes during the `build` process by delegating all file content verification to the unified, encoding-safe `io_processor`.
- Fixes `--check` mode flow where it failed to start building after user confirmation.
- Fixes `Build` engine noise by silencing identical files and batching overwrite prompts at the end.
- Fixes `ModuleNotFoundError` by correcting relative imports within the package.
- Fixes a security gap where automated `--delete` could bypass TTY interactive checks.
- Fixes the Markdown fence parsing logic in the `build` command to intelligently resolve file paths (e.g., matching `tests/__init__.py` to `__init__.py`) and prevent the creation of orphaned files not declared in the tree blueprint.

## [2.4.3] - 2026-03-26

*Note: This is a maintenance release focused entirely on internal refactoring and stability. No new features have been added.*

### Fixed
- Fixes several known issues.

## [2.4.2] - 2026-03-26

*Note: This is a maintenance release focused entirely on internal refactoring and stability. No new features have been added.*

### Changed
- Optimizes internal code architecture for better performance and maintainability.
- Adds comprehensive comments to core logic for improved readability.

### Fixed
- Fixes several known issues.

## [2.4.1] - 2026-03-21

*Note: This release includes significant architectural improvements and performance optimizations.*

### Added
- Adds `--ignore-case` flag for grep mode.
- Adds `--dry-run` flag to preview deletions safely.

### Changed
- Refactors traversal engine to a single-pass design with content caching.
- Restructures core modules for better maintainability.
- Makes `Pillow` an optional dependency.

### Fixed
- Fixes memory calculation limits for accurate OOM prevention.
- Fixes Python version verification for `--skeleton` mode.

## [2.4.0] - 2026-03-21

*Note: This release introduces advanced agent tools and intelligent project analysis capabilities.*

### Added
- Adds JSON output mode (`-F json`).
- Adds file type filter (`--type`) and include filter (`--include`).
- Adds Regex search mode (`--regex`) and content search (`--grep`).
- Adds Project Analysis mode (`--analyze`) to detect architecture and dependencies.

### Changed
- Extends `ScanConfig` to support complex routing and filtering.

## [2.3.1] - 2026-03-19

*Note: This release focuses on architectural improvements, security hardening, and bug fixes.*

### Changed
- Simplifies `ScanConfig` dataclass and decouples core IO logic.
- Enhances edge-case resilience for broken symlinks and locked directories.
- Adds strict conflict interception for mutually exclusive CLI flags.

### Fixed
- Patches deep-nesting pattern matching and root-path anchoring rules.
- Fixes build depth calculation bug and headless server output crashes.

## [2.3.0] - 2026-03-19

*Note: This release introduces features optimized for LLM context generation.*

### Added
- Adds AST Code Skeleton extraction (`--skeleton`).
- Adds smart rule parsing for `.gitignore` files (`--exclude`).

### Changed
- Streamlines CLI search output and Power Mode generation.

### Fixed
- Fixes dynamic markdown fence collisions in search reports.

## [2.2.3] - 2026-03-15

*Note: This release focuses on security hardening and core engine optimizations.*

### Added
- Adds wildcard glob support for exclusions.
- Adds interactive TTY environment probing.

### Changed
- Enhances path traversal sandbox and binary detection heuristics.

### Fixed
- Patches symlink cascade deletion vulnerability.
- Fixes hardware memory probe calculations to prevent OOM kills.

## [2.2.2] - 2026-03-14

*Note: This release introduces robust security measures and performance upgrades.*

### Added
- Adds heuristic binary detection and smart encoding fallback chains.

### Changed
- Migrates traversal engine to iterative DFS to prevent recursion errors.
- Centralizes logging and UI interactive prompts.

### Fixed
- Patches cross-platform path injection vulnerabilities.
- Fixes headless server font loading issues during image export.

## [2.2.1] - 2026-03-13

*Note: This release provides critical security hotfixes and API enhancements.*

### Added
- Adds API quiet mode for library imports.
- Expands default text-file whitelist for C++/CUDA projects.

### Changed
- Optimizes garbage collection performance for massive repositories.

### Fixed
- Patches path traversal vulnerability in the build engine.
- Fixes fuzzy search completeness and tree UI rendering glitches.

## [2.2.0] - 2026-03-13

*Note: This major update introduces a public Python API and core engine overhaul.*

### Added
- Adds smart text filtering and CSV native support.
- Adds dangerous deletion mode (`--delete`).

### Changed
- Restructures the project into a scalable Python package for public API usage.
- Refines CLI arguments to prefer explicit long flags.

### Fixed
- Fixes memory overflow and strict depth enforcement during full scans.
- Hardens engine against infinite symlink loops.

## [2.1.0] - 2026-03-12

*Note: This release improves the build command and search UX.*

### Added
- Adds context rehydration for reverse building source code from reports.
- Adds direct creation flags (`-d`) to bypass prompts.

### Changed
- Updates search highlighting tags and default output filenames.

### Fixed
- Fixes path misalignment issues in source code blocks.

## [2.0.0] - 2026-03-11

*Note: This release introduces project scaffolding functionality.*

### Added
- Splits the tool into dual commands: `scan` and `build`.
- Adds the ability to physically construct folders and files from text blueprints.

## [1.0.0] - 2026-03-10

*Note: Initial public release.*

### Added
- Adds directory explorer and multi-format export (`.md`, `.txt`, `.png`).
- Adds dual-mode find engine (exact and fuzzy).
- Adds Power Mode (`--full`) for LLM context aggregation.