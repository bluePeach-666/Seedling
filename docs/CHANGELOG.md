# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.1] - 2026-03-21

### Architecture Refactoring

This release includes significant architectural improvements and performance optimizations.

### Performance Improvements

- **Single-Pass Traversal Engine**: Introduced unified `traverse_directory()` function with content caching. The `scan -f keyword --full` workflow now uses a single filesystem pass instead of three separate traversals.
- **Content Caching**: File contents are now cached during traversal, preventing redundant file reads when generating reports.

### Architecture Changes

- **Module Restructuring**: Split `filesystem.py` (368 lines) into focused modules for better maintainability:
  - `config.py`: Configuration classes and constants
  - `detection.py`: File type detection utilities
  - `patterns.py`: Pattern matching functions
  - `traversal.py`: Unified traversal engine with caching
- **Backward Compatibility**: All existing imports from `filesystem.py` continue to work via re-exports.

### CLI Improvements

- **Grep Case Sensitivity**: Added `-i` / `--ignore-case` flag for content search. Default is now **case-sensitive** for more predictable behavior.
  ```bash
  scan . -g "TODO"              # Case-sensitive (new default)
  scan . -g "todo" -i           # Case-insensitive
  ```
- **Enhanced Font Discovery**: Expanded Linux font path coverage (Noto CJK, WenQuanYi, Source Han, Droid) and added fontconfig dynamic discovery for better CJK support on headless servers.

### Compatibility Fixes

- **Python Version Check for `--skeleton`**: Added early CLI-level version check for `--skeleton` mode which requires Python 3.9+ (depends on `ast.unparse`). Users on Python 3.8 now receive a clear error message with upgrade instructions instead of a crash.
- **Pillow as Optional Dependency**: Moved `Pillow` from required to optional dependencies (`[project.optional-dependencies] image`). Users who don't need image export no longer need to install Pillow. Install with `pip install Seedling-tools[image]` for image support.

### Security Improvements

- **`--dry-run` Mode for `--delete`**: Added `--dry-run` flag to preview deletions before executing. Shows a detailed list of files/directories that would be deleted without actually performing the deletion.
  ```bash
  scan . -f "temp_*" --delete --dry-run
  ```

### Bug Fixes

- **Accurate Memory Calculation**: Fixed memory limit calculation in `get_full_context()` to use `sys.getsizeof()` instead of UTF-8 encoded size. This provides more accurate memory tracking and prevents OOM crashes when processing files with high Unicode character density.
- **Conservative Memory Threshold**: Reduced memory threshold from 100% to 80% of system limit for additional safety margin.

## [2.4.0] - 2026-03-21

### Agent Tools Enhancement Update

This release transforms Seedling into a powerful alternative to built-in tools like Glob, Grep, and Explore agents, making it the go-to choice for AI-assisted development workflows.

### New Features

- **JSON Output Mode (`-F json`)**: Export directory structures as structured JSON for programmatic consumption by AI agents and automation tools. Includes `meta`, `stats`, and nested `tree` with file extensions.
- **File Type Filter (`--type` / `-t`)**: Filter scans by file type with support for `py`, `js`, `ts`, `cpp`, `go`, `java`, `rs`, `web`, `json`, `yaml`, `md`, `shell`, and `all`.
- **Include Filter (`--include`)**: Specify glob patterns to include only matching files (e.g., `--include "*.py"`).
- **Regex Search Mode (`--regex`)**: Treat search patterns as regular expressions instead of simple substrings.
- **Content Search / Grep Mode (`--grep` / `-g`)**: Search inside file contents with optional context lines (`-C N`).
- **Project Analysis Mode (`--analyze`)**: Intelligently analyze project structure, detect project type, language, entry points, dependencies, and architecture patterns.

### Architecture Changes

- **Extended `ScanConfig`**: Added `includes`, `file_type`, and `use_regex` fields to the configuration dataclass.
- **New `FILE_TYPE_MAP`**: Centralized file type to extension mapping for consistent filtering.
- **New `matches_include_pattern()`**: Pattern matching function for include filters.
- **New Modules**:
  - `json_output.py`: JSON serialization for directory trees
  - `grep.py`: Content search engine with context support
  - `analyzer.py`: Project analysis and detection

### CLI Improvements

- **Format option extended**: `-F` now accepts `json` in addition to `md`, `txt`, `image`
- **New argument group**: Grep Mode arguments (`-g`, `-C`) grouped in help output
- **Smart routing**: `handle_scan()` now routes to specialized handlers for `--analyze` and `--grep` modes

### Usage Examples

```bash
# JSON output for AI consumption
scan . -F json -o structure.json

# Filter by file type
scan . --type py -d 3

# Regex search
scan . -f "test_.*\.py" --regex

# Content search with context
scan . --grep "TODO" -C 3 --type py

# Project analysis
scan . --analyze

# Combined filters
scan . --type py --grep "def main" -C 2
```

## [2.3.1] - 2026-03-19

### 🚀 Architectural Overhaul & API (The "Precision & Architecture" Update)
- **Configuration Dataclass (`ScanConfig`)**: Solved parameter bloat by introducing the `ScanConfig` dataclass. Core engine functions like `scan_dir_lines` and `search_items` have been drastically simplified (from 9 parameters down to 3), vastly improving programmatic API usage and IDE intellisense.
- **DRY Logic Decoupling**: Extracted redundant dynamic markdown fence calculations and path traversal safety checks into unified, global utility functions within `core/io.py`, ensuring consistent behavior across all CLI commands.

### 🛡️ Security & Hardening
- **Secondary OOM Defense (Unicode Bomb Protection)**: Upgraded the memory safety limit. The text reader now performs a secondary `sys.getsizeof()` inspection *after* decoding a file. This instantly intercepts "memory bombs" where specific files (e.g., CJK-heavy or zero-padded) explode in RAM usage once converted to Python Unicode strings, preventing silent kernel kills.
- **Unified Boundary Sandbox**: Centralized the `is_safe_path` engine. Both the exclusion file parser (`-e`) and the `build` architect now share the exact same strict boundary validation, preventing arbitrary file reads/writes via `../../../` path traversal attacks.
- **Edge-Case Resilience**: The filesystem traversal engine now gracefully intercepts `PermissionError` (locked system directories) and broken symlinks without crashing the pipeline, explicitly tagging them in the generated visual tree.

### 🐛 Bug Fixes & Refinement
- **Root-Path Anchoring Fix**: Fixed a critical logic gap where `.gitignore` rules starting with a slash (e.g., `/build/`) failed to properly intercept root-level directories. Internal relative paths are now POSIX-normalized with a leading `/` to perfectly align with native Git behavior.
- **Deep-Nesting Pattern Matching**: Optimized the global filtering engine to ensure non-anchored rules (like `__pycache__` or `node_modules`) are accurately intercepted at any directory depth, eliminating deep-level context pollution.
- **Strict Directory-Only Rules**: Hardened trailing slash rules. A rule ending in `/` will now strictly apply *only* to directories, preventing the accidental exclusion of identically named text files.
- **Windows Headless Crash Fix**: Fixed a fatal `AttributeError` on Windows when executed in non-interactive terminals (like CI/CD pipelines) where `sys.stderr` lacks a `buffer` attribute. Output stream UTF-8 encapsulation is now safely fault-tolerant.
- **Build Depth Calculation Fix**: Fixed a critical bug in the `build` engine where tree depth was incorrectly calculated using raw string length instead of actual indentation space. The architect engine can now flawlessly rehydrate deeply nested, complex blueprints.

### ✨ UX & CLI Polish
- **Mutually Exclusive Flags**: The CLI router now actively intercepts conflicting arguments. Attempting to pass both `--full` (source code aggregation) and `--skeleton` (AST extraction) simultaneously will trigger a fail-fast error, preventing silent overrides and user confusion.
- **Interactive Security First**: In `search` mode, the TTY safety check for `--delete` has been moved to the absolute top of the execution chain, immediately blocking automated deletion attempts regardless of whether matches are found.

### 🧪 Testing & Maintenance
- **Expanded Edge-Case Coverage**: Added a comprehensive suite of unit tests specifically targeting filesystem edge cases, including broken symlinks, circular symlink protections, empty directories, and permission denials.
- **E2E Synchronization**: Hardened the automated `test_suite.sh` with strict validation for mutually exclusive parameter conflicts and precise root-path anchoring rules.

## [2.3.0] - 2026-03-19

### ✨ New Features (The "LLM Context" Update)
- **AST Code Skeleton Extraction (`--skeleton`)**: Introduced a powerful AST (Abstract Syntax Tree) parsing engine for Python (`.py`) files. This mode strips out complex implementation logic while perfectly preserving class structures, function signatures, and docstrings. It drastically reduces LLM context window consumption while providing a perfect "birds-eye view" of a codebase.
- **Smart Rule File Parsing (`--exclude`)**: The `-e` flag is now context-aware. Passing a file (like `.gitignore` or `.dockerignore`) will automatically read and parse its contents line-by-line as exclusion rules. It includes smart fallbacks, typo detection (e.g., typing `gitignore` without the dot), and interactive prompts to seamlessly guess the user's intent without needing any additional flags.

### 🚀 UX & CLI Polish
- **Streamlined CLI Search**: The `scan -f` (find) command has been overhauled for speed and cleanliness. By default, it now prints exact and fuzzy matches directly to the terminal and exits, keeping your disk clean of unwanted report files.
- **True Power Mode for Search**: When appending `--full` to a search query, Seedling now safely bypasses interactive prompts and instantly generates a comprehensive Markdown report. This report perfectly pairs the 🎯 highlighted directory tree with the complete source code of all matched files.

### 🐛 Bug Fixes & Refactoring
- **Search Report Fence Collision Fix**: Ported the dynamic backtick calculation algorithm from the main explorer into the search report engine. Extracting source files that contain nested markdown blocks will no longer truncate or break the generated search report.
- **Parser Decoupling**: Extracted the complex exclusion logic into a dedicated `exclude_parser.py` module, keeping the core CLI router perfectly clean and maintainable.

## [2.2.3] - 2026-03-15

### 🛡️ Security & Hardening (The "Ironclad Sandbox" Update)
- **Symlink Cascade Deletion Fix**: Patched a critical vulnerability in `search --delete` where symbolic links pointing to system directories were followed rather than unlinked, preventing catastrophic data loss.
- **Path Traversal Sandbox Enhancement**: Upgraded the `is_safe_path` engine. It now resolves virtual/symlinked paths completely before boundary validation, flawlessly intercepting `../../../` escapes even when the target build directory doesn't physically exist yet.
- **Test Suite Containment**: Hardened `test_suite.sh` by strictly confining all automated destructive operations (`rm -rf`) to a verified `$HOME/tmp/` sandbox, eliminating the risk of accidental root directory wipes.

### 🚀 Core Engine & Parsing (The "Inception" Fix)
- **Dynamic Markdown Fencing (Fence Collision Fix)**: The `--full` context aggregator now dynamically scans source code for backticks and mathematically calculates the exact fence size needed (e.g., ` ```` ` ) to safely wrap nested markdown files without breaking the blueprint.
- **Parser "Focus Mode"**: Fixed a severe logic bug where `build` would mistakenly execute fake `### FILE:` directives embedded inside source code (like test scripts). The parser now completely ignores structural commands while inside an active code block.
- **Magic Number Binary Detection**: Upgraded the `is_binary_content` heuristic probe. It no longer relies solely on null bytes (`\x00`), but now actively checks file signatures (Magic Numbers) to instantly block disguised PNGs, JPEGs, ZIPs, PDFs, and ELFs from polluting the LLM context.
- **True OOM Protection Calculation**: Fixed a fatal flaw in the hardware memory probe where systems with low RAM were forcefully assigned a 512MB limit, causing kernel OOM kills. The text reader now also strictly calculates the *decoded UTF-8 string size* in memory, rather than relying on the raw disk file size.
- **Directory Loop / Bind Mount Prevention**: The DFS traversal engine now tracks resolved physical paths (`seen_real_paths`). It instantly detects and blocks infinite file system loops caused by bind mounts or hard link storms, printing a clean `🔄 [Recursion Blocked]` tag.

### ✨ UX, API & Polish
- **CI/CD Pipeline Compatibility**: The `ask_yes_no` interactive prompt now actively probes for a TTY environment. In non-interactive environments (like GitHub Actions or piped output), it gracefully defaults to "Safe/No" instead of hanging the process infinitely.
- **Wildcard Exclusion Support**: The `--exclude` flag now fully supports `fnmatch` globs. Users can now easily ignore patterns like `*.pyc`, `__pycache__`, or `*-lock.json`.
- **Fuzzy Deletion Safety Lock**: Increased the `difflib` search cutoff threshold from 0.4 to 0.6 for higher accuracy. Furthermore, `--delete` now explicitly separates fuzzy matches from exact matches, requiring a secondary explicit `[y/n]` confirmation before purging them.
- **Image Bomb Interception**: Hard-capped the `image` export format. Directories exceeding 1500 lines will now trigger a hard error and abort instead of attempting to render a gigabyte-sized image that crashes the Pillow library.

## [2.2.2] - 2026-03-14

### 🛡️ Security & Safety
- **Path Traversal Prevention (Phase 1 Sandbox)**: Completely restructured the `build` engine to include a dedicated pre-processing phase. It now strictly enforces absolute path resolution and `.is_relative_to()` boundary checks *before* any disk operations occur. Maliciously crafted tree diagrams attempting to escape the target directory (e.g., via `../../../etc/passwd`) are instantly blocked.
- **`--delete` TTY Safety Lock**: Hardened the dangerous deletion mode in `search`. It now strictly checks for an interactive terminal (`sys.stdin.isatty()`) to block piped/automated deletions (e.g., `echo "y" | scan ...`). Furthermore, it requires the user to explicitly type `"CONFIRM DELETE"` instead of a simple `y/n`, preventing catastrophic accidents in CI/CD pipelines.
- **Fail-Safe Test Suite**: Upgraded the `test_suite.sh` cleanup procedures. Replaced risky removal commands with strict bash parameter expansions (`rm -rf "${DIR:?Variable not set}"`) to ensure a missing environment variable never results in a wiped root or home directory.

### 🚀 Core Engine & Performance (The "Unbreakable" Engine)
- **Recursion DoS Prevention**: Completely rewrote the directory traversal engine in `filesystem.py`. It has been migrated from a recursive approach to a **Stack-based Iterative Depth-First Search (DFS)**. Paired with a hardcoded `MAX_ITERATION_DEPTH = 1000`, Seedling is now immune to `RecursionError` and stack overflow crashes, even when scanning maliciously deep nested directories.
- **Auto OOM Protection (Hardware Probe)**: Deprecated manual memory limits. Introduced `sysinfo.py` to dynamically probe the host's physical RAM across Mac, Linux, and Windows. The `--full` context aggregator now enforces a strict 10% physical RAM ceiling (with a 512MB fallback). If the threshold is breached, Seedling instantly trips the circuit breaker to protect the host machine from Out-Of-Memory (OOM) kills.
- **Heuristic Binary Detection**: Added a pre-read scanner (`is_binary_content`) that checks the first 1024 bytes of a file for null bytes (`\x00`). This silently detects and ejects extension-less binaries masquerading as text, preventing thousands of lines of garbage from polluting LLM context windows.
- **Smart Encoding Fallback Chain**: Replaced brute-force `errors='strict'` with an intelligent fallback chain (`UTF-8 -> GBK -> Big5 -> UTF-16 -> Latin-1`). This guarantees flawless reading of legacy codebases without producing `\ufffd` corruption.

### 🐛 Compatibility & Bug Fixes
- **Cross-Platform Path Injection (The `PureWindowsPath` Magic)**: Fixed a severe `KeyError` bug where blueprint text generated on Windows (containing `\` separators) would fail to restore code blocks when `build` was executed on macOS/Linux. By replacing manual `.replace('\\', '/')` with Python's native `PureWindowsPath` engine, Seedling now flawlessly understands and converts Windows paths regardless of the host OS.
- **Headless Server Font Fallback**: Fixed a crash in the `image` export mode when executed on headless Linux servers (e.g., AWS/Aliyun) lacking CJK fonts. The engine now gracefully falls back to Pillow's default built-in font rather than throwing a fatal error.

### ✨ UX & Code Refactoring
- **Centralized Logging & True Quiet API**: Completely decoupled console output from the core business logic. Replaced hundreds of scattered `print()` statements with a centralized `logger.py` featuring a custom `CLIFormatter`. When used as a Python package with `quiet=True` (or `-q` in CLI), Seedling is now completely silent, ensuring zero stdout pollution for host applications.
- **Global Filter Deduplication**: Abstracted all exclusion logic (hidden files, `--exclude` lists, `--text` filtering) into a single, unified `is_valid_item()` function. This massive refactor wiped out hundreds of lines of redundant checks across the scan, search, and context aggregation engines.
- **Export Overwrite Protection**: The `scan` and `search` file generation routines now verify if the output file already exists, prompting users with a `[y/n]` safety check before overwriting historical snapshots.
- **Interactive Easter Egg Cooling**: Modified the aggressive `rm -rf /` visual joke triggered by empty `scan` calls. It is now safely locked behind an opt-in "Chaos Mode" confirmation, defaulting to a harmless "brewing coffee" animation for startled users.

## [2.2.1] - 2026-03-13

### 🚨 Security Hotfixes
- **Path Traversal Prevention (Build Engine)**: Patched a critical zero-day vulnerability in `architect.py` where maliciously crafted or malformed markdown blueprints could write files outside the intended target directory (e.g., overwriting system files via `../../../`). Strict `.is_relative_to()` absolute path boundary checks are now enforced during all raw source code restorations.

### 🐛 Bug Fixes
- **Windows Startup Crash**: Fixed a fatal `NameError` caused by a missing `import io` in the terminal UTF-8 initialization block. Windows users can now run `scan` and `build` commands without instantly crashing.
- **Fuzzy Search Completeness**: Rewrote the internal dictionary memory into a list-tuple structure for the `find` engine. Fixed a severe bug where files sharing the exact same name across different nested folders (e.g., multiple `utils.py`) would silently overwrite each other in the search index.
- **Tree UI Rendering**: Fixed a visual formatting bug where encountering a `PermissionError` on a locked directory would break the tree drawing with a disjointed, hardcoded `└──` branch.

### ✨ Enhancements & API Polish
- **API Quiet Mode (`quiet=True`)**: Core functions (`scan_dir_lines`, `search_items`, `get_full_context`) now fully support a `quiet` parameter. When Seedling is imported as a Python library, this prevents progress bars, emojis, and CLI logs from polluting the host server's standard output.
- **Smarter Text Filter (`--text`)**: The engine now intelligently recognizes and whitelists extension-less core configuration files (e.g., `Makefile`, `Dockerfile`, `LICENSE`) and hidden dotfiles (e.g., `.gitignore`, `.env`) that were previously skipped.
- **Expanded C++ & CUDA Support**: Massively expanded the default text-file whitelist to include C/C++ variants (`.cc`, `.cxx`, `.hpp`, `.inl`, etc.), CUDA files (`.cu`, `.cuh`), and C# (`.cs`), ensuring zero code loss during `--full` aggregation on complex low-level engineering projects.
- **GC Performance Boost**: Extracted high-frequency set allocations in the file-checking loop into module-level global constants, noticeably reducing memory overhead and Garbage Collection lag when scanning massive repositories (50,000+ files).

## [2.2.0] - 2026-03-13

### 🚀 Architectural Overhaul & API
- **Modular Redesign**: The monolithic `scan_tool` folder has been completely retired and replaced by a highly scalable `seedling` package. Logic is now cleanly separated into `commands/` (CLI routing) and `core/` (business engines).
- **Public Python API**: Seedling is no longer just a CLI tool! Developers can now `import seedling` in their own Python projects to directly utilize core functions like `scan_dir_lines`, `search_items`, and `build_structure_from_file`.

### ✨ New Features
- **Smart Text Filter (`--text`)**: Added a strict filter to ignore all non-text (binary/media) files during tree scanning and searching, keeping outputs clean.
- **Dangerous Deletion (`--delete`)**: Search mode now features a highly-requested deletion tool. It allows users to permanently wipe out matched files/folders (both exact and fuzzy) with a built-in `[y/n]` safety lock.
- **Trailing Slashes**: Directories generated in the tree output now automatically append a `/` (e.g., `src/`), vastly improving visual parsing between files and folders.
- **CSV Native Support**: The context aggregation engine now officially recognizes and extracts data from `.csv` files.
- **Placeholder Feature**: Reserved architecture and argument space for the upcoming `--skeleton` (Code Skeleton Extraction) mode.

### 🛡️ Hardening & Bug Fixes (The "Unbreakable" Update)
- **Memory Overflow Protection**: Added a `2MB` hard limit per file in Power Mode (`--full`). Seedling will now smartly skip ultra-large files to prevent RAM exhaustion and terminal freezes on massive workspaces.
- **Graceful Interruptions**: Pressing `Ctrl+C` during a massive `--full` scan no longer crashes the program. It now intercepts the signal and safely exports the context aggregated up to that exact moment.
- **Strict Depth Enforcement**: Fixed a critical bug where `--full` mode would ignore the `--depth` limit and recursively read the entire disk.
- **Directory Interception in Build**: Fixed `[Errno 13] Permission denied` on Windows by actively checking and rejecting directories if passed as a blueprint file to the `build` command.
- **Symlink Blackhole Defense**: Strengthened the filesystem engine to survive infinite symlink loops without throwing `RecursionError`.
- **Chaos Engineering Tested**: Passed the Ultimate Chaos Test Suite, proving robust against path traversal attacks, emoji/invisible filenames, and 10,000+ deep file structures.

### 🕹️ CLI Tweaks
- **Cleaner Arguments**: Deprecated ambiguous short flags (such as `-s`, `-t`, `-c`, `-v`) in favor of explicit, readable long flags (`--show-hidden`, `--text`, `--check`, `--version`). Keep the interface pure and readable.
- **Enhanced `.gitignore`**: Provided a foolproof template to strictly block `__pycache__`, `*.egg-info`, and nested test sandbox outputs from VCS.

## [2.1.0] - 2026-03-12

### ✨ Added
- **Context Rehydration (Reverse Build)**: The `build` command can now parse `--full` generated markdown files and intelligently inject source code back into the newly created files. 
- **Smart Fallback for Build**: When a blueprint is not found, `build` smoothly prompts to create a direct file or folder instead of crashing.
- **Direct Creation Flag**: Added the `-d` (or `--direct`) flag to bypass prompts and instantly create files or directories.
- **Search Highlighting**: The generated tree document in `find` mode now places a `🎯 [MATCHED]` tag next to matched files.
- **Combo System & Easter Eggs**: Added a time-based combo system for consecutive `scan` commands with hidden terminal animations (Mac/Linux exclusive).

### 🚀 Changed
- **Output Filename**: Removed the redundant `_tree` suffix from default scan outputs.
- **Strict User Prompts**: Refactored all `[y/n]` interactions to safely catch invalid keystrokes.
- **Root Node Stripping**: The build engine now smartly strips redundant outer wrapper folders from markdown blueprints.

### 🛠 Fixed
- Fixed an issue where `build` would mistakenly create duplicate files due to path misalignment in source code blocks.

## [2.0.0] - 2026-03-11

### 🚀 Major Feature Update (The "Architect" Update)
- **Dual Command System**: Evolved from a single-command utility into a versatile toolkit by officially splitting the tool into two distinct commands: `scan` (for exploring) and `build` (for constructing).
- **Project Scaffolding (`build`)**: Introduced the ability to read a text-based tree diagram (from a `.txt` or `.md` blueprint) and physically create the corresponding folders and files on the local file system.

## [1.0.0] - 2026-03-10 - Initial Release

### 🎉 First Public Release
- **Directory Explorer (`scan`)**: The core functionality to traverse directories and generate visual tree representations.
- **Multi-Format Export**: Support for exporting the directory tree to Markdown (`.md`), Plain Text (`.txt`), and visually appealing Images (`.png`).
- **Find Engine**: Dual-mode search featuring Exact Match and Fuzzy Suggestions (powered by Levenshtein distance).
- **Power Mode (`--full`)**: The ability to aggregate and bundle the entire source code of a project into a single Markdown file, optimized for LLM context feeding.