# 🌲 Seedling (v2.3.0)

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling** is a high-performance, 3-in-1 CLI toolkit designed for developers to explore, search, and reconstruct directory structures. Whether you need a beautiful image of your project architecture, a way to spawn a project from a text blueprint, or a context-optimized codebase skeleton for LLMs, Seedling has you covered.

---

## 🚀 Key Features

* **LLM-Optimized Code Skeletons (`--skeleton`)**: Harnesses Python's AST (Abstract Syntax Tree) to strip away complex logic while perfectly preserving classes, functions, and docstrings. Instantly generate a "birds-eye view" of your codebase that drastically saves LLM context window tokens.
* **Smart Exclusions**: The `--exclude` flag is now context-aware! Pass a file like `.gitignore` and Seedling will automatically read and apply its rules line-by-line. Features intelligent typo-detection and interactive prompts.
* **Streamlined Search & True Power Mode**: `find` now directly outputs exact and fuzzy matches to the terminal for blazing-fast navigation. Combine it with `--full` to bypass prompts and instantly generate a comprehensive Markdown report containing the directory tree 🎯 highlights and full source code.
* **True OOM Protection**: Intelligently probes your host's physical RAM and calculates precise decoded UTF-8 memory allocation. The `--full` context aggregator enforces a strict 10% memory ceiling, preventing system crashes when parsing massive monorepos.
* **Cross-Platform Rehydration**: Generate a project snapshot on Windows (with `\` paths), and flawlessly restore the *entire* directory structure and source code on a Mac or Linux machine.
* **Public Python API (True Quiet Mode)**: Seedling is a library! You can `import seedling` in your scripts to use its powerful engines programmatically. With the new centralized logger, `quiet=True` ensures absolute zero stdout pollution.
* **Smart Text Filter & Magic Number Check**: Strictly ignore binary and media files during tree scanning. Features an advanced **Heuristic Binary Check** that scans for Magic Numbers (PNG, ELF, ZIP, PDF, etc.) to dynamically block disguised non-text files.
* **Dangerous Deletion (`--delete`)**: Search for files or folders and permanently wipe them out with a built-in TTY interactive lock requiring explicit confirmation. Now features secondary safety locks for fuzzy matches and symlinks.

---

## 🛠️ Installation

Seedling is designed to be installed globally via `pipx` for a clean, isolated environment.

### One-Click Setup

* **Windows**: Run `./install.bat`
* **macOS / Linux**: Run `bash install.sh`

### Developer / Manual Install

If you are modifying the source code, use **Editable Mode**:

```bash
pipx install -e . --force
```

---

## 🐍 Python Library Usage

You can now use Seedling's core features directly in your Python code:

```python
import seedling

# Generate directory tree lines (Use quiet=True to suppress all console logs)
lines = seedling.scan_dir_lines("./src", max_depth=2, quiet=True)
print("\n".join(lines))

# Search for specific items
exact, fuzzy = seedling.search_items(".", keyword="utils", quiet=True)

# Reconstruct a project from a blueprint
seedling.build_structure_from_file("blueprint.md", "./new_project")
```

---

## 📖 CLI Reference

Seedling 2.3.0 uses a clean, explicit argument system. All commands now support unified logging controls (`-v` / `-q`).

### 1. `scan` - The Explorer

Used for scanning directories, extracting code skeletons, or searching for items.

| Argument | Description |
| --- | --- |
| `target` | Target directory for scanning or searching (Defaults to `.`). |
| `--version` | Show program's version number and exit. |
| `--find`, `-f` | **Search Mode**. Fast CLI search (Exact & Fuzzy). Combine with `--full` to export a code report. |
| `--format`, `-F` | Output format: `md` (default), `txt`, or `image`. |
| `--name`, `-n` | Custom output filename. |
| `--outdir`, `-o` | Where to save the result. |
| `--showhidden` | Include hidden files in the scan. |
| `--depth`, `-d` | Maximum recursion depth. |
| `--exclude`, `-e` | List of items to ignore. **Smart parse: auto-reads `.gitignore` files or accepts globs**. |
| `--full` | **Power Mode**. Appends the full text content of all scanned source files. |
| `--skeleton` | **[Experimental]** AST Code Skeleton extraction. Strips logic, retains classes/defs/docstrings. |
| `--text` | **Smart Filter**. Only scan text-based files (ignores binary/media). |
| `--delete` | **Cleanup Mode**. Permanently delete items matched by `--find` (Interactive TTY only). |
| `--verbose`, `-v` | Enable debug logging. |
| `--quiet`, `-q` | Silent mode. Only show critical errors. |
| `--noemoji` | Disable emojis for cleaner rendering on legacy/simple terminals. |

### 2. `build` - The Architect

Turn a text-based tree into a real file system, or restore a project from a snapshot.

| Argument | Description |
| --- | --- |
| `file` | The source tree blueprint file (`.txt` or `.md`). |
| `target` | Where to build the structure (Defaults to current directory). |
| `--version` | Show program's version number and exit. |
| `--direct`, `-d` | **Direct Mode**. Bypass prompts to instantly create a specific path. |
| `--check` | **Dry-Run**. Simulate the build and report missing/existing items. |
| `--force` | **Force Mode**. Overwrite existing files without skipping. |
| `--verbose`, `-v` | Enable debug logging. |
| `--quiet`, `-q` | Silent mode. Only show critical errors. |

---

## 📂 Project Structure (v2.3.0)

```text
Seedling/
├── seedling/                  # Core Package
│   ├── commands/              # CLI Command Routers
│   │   ├── scan/              # Scan logic
│   │   │   ├── explorer.py    # Standard directory traversal
│   │   │   ├── search.py      # Search engine & highlight reports
│   │   │   ├── full.py        # Context aggregator
│   │   │   ├── skeleton.py    # Python AST skeleton extractor
│   │   │   └── exclude_parser.py # Smart ignore-file parser
│   │   └── build/             # Build logic (architect)
│   ├── core/                  # Shared Engines
│   │   ├── filesystem.py      # Iterative Traversal, Text verification & DFS limits
│   │   ├── io.py              # File R/W, Fence Collision parsing & Image limits
│   │   ├── logger.py          # Centralized CLI Formatter
│   │   ├── sysinfo.py         # Hardware Probe (Precise RAM constraints)
│   │   └── ui.py              # Animations, Progress bars & CI/CD checks
│   ├── __init__.py            # Public API & Metadata
│   └── main.py                # Entry Point Router
├── pyproject.toml             # Build configuration
├── install.sh/bat             # One-click installers
└── test_suite.sh              # Ultimate E2E tests
```

---

## 🛡️ Stability & Hardening (The Ironclad Sandbox)

Seedling v2.3.0 has been fortified to survive extreme edge cases and chaotic inputs:

* **Recursion & Mount Loop Defense**: Directory traversal uses an iterative Stack-DFS tracking resolved physical paths. It mathematically eliminates `RecursionError` and instantly blocks infinite OS-level bind mount or hard link loops.
* **Markdown Fence Collision Immunity**: The parser calculates dynamic backtick boundaries, allowing Seedling to flawlessly bundle and reconstruct documents containing nested code blocks (like its own source code) without truncation.
* **AST Graceful Degradation**: The `skeleton` extractor uses Python's `ast` engine. If it encounters syntax errors in legacy/broken code, it safely falls back to returning the raw text rather than crashing the pipeline.
* **Symlink Deletion Safety**: Search and delete operations explicitly sever symbolic links without following them, protecting host systems from catastrophic cascade deletions.
* **Pre-Processing Sandbox**: The `build` engine executes a Phase 1 simulation resolving virtual paths. It intercepts zero-day path traversal attacks (e.g., `../../../`) *before* any disk operations occur.

---

## 📜 Changelog

Detailed changes for each release are documented in the [CHANGELOG.md](CHANGELOG.md) file.

### Latest Update: v2.3.0 (The "LLM Context" Update)

* **AST Code Skeleton Extraction (`--skeleton`)**: Introduced a powerful AST parsing engine for Python files. Strips out complex implementation logic while perfectly preserving class structures, function signatures, and docstrings. Drastically reduces LLM context window consumption.
* **Smart Rule File Parsing (`--exclude`)**: The `-e` flag is now context-aware. Passing a file (like `.gitignore`) will automatically read and parse its contents line-by-line. Includes intelligent typo detection (e.g., typing `gitignore` without the dot) and interactive prompts.
* **Streamlined CLI Search**: The `scan -f` command now prints exact and fuzzy matches directly to the terminal and exits, keeping your disk clean.
* **True Power Mode for Search**: Combining `--find` with `--full` now safely bypasses interactive prompts and instantly generates a comprehensive Markdown report pairing the highlighted directory tree with the complete source code of matched files.