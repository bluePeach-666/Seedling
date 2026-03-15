# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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