# 🌲 Seedling (v2.2.3)

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling** is a high-performance, 3-in-1 CLI toolkit designed for developers to explore, search, and reconstruct directory structures. Whether you need a beautiful image of your project architecture or a way to spawn a project from a text blueprint, Seedling has you covered.

---

## 🚀 Key Features

* **Modular Architecture**: A completely rebuilt core engine, separating commands and core logic for infinite scaling and professional maintenance.
* **True OOM Protection**: Intelligently probes your host's physical RAM and calculates precise decoded UTF-8 memory allocation. The `--full` context aggregator enforces a strict 10% memory ceiling, preventing system crashes when parsing massive monorepos.
* **Cross-Platform Rehydration**: Generate a project snapshot on Windows (with `\` paths), and flawlessly restore the *entire* directory structure and source code on a Mac or Linux machine.
* **Public Python API (True Quiet Mode)**: Seedling is a library! You can `import seedling` in your scripts to use its powerful engines programmatically. With the new centralized logger, `quiet=True` ensures absolute zero stdout pollution.
* **Smart Text Filter & Magic Number Check**: Strictly ignore binary and media files during tree scanning. Features an advanced **Heuristic Binary Check** that scans for Magic Numbers (PNG, ELF, ZIP, PDF, etc.) to dynamically block disguised non-text files.
* **Dangerous Deletion (`--delete`)**: Search for files or folders and permanently wipe them out with a built-in TTY interactive lock requiring explicit confirmation. Now features secondary safety locks for fuzzy matches and symlinks.
* **CI/CD & Automation Ready**: Built-in TTY detection ensures Seedling will safely default to "No" instead of hanging infinitely when executed in headless server pipelines or piped commands.

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

Seedling 2.2.3 uses a clean, explicit argument system. All commands now support unified logging controls (`-v` / `-q`).

### 1. `scan` - The Explorer

Used for scanning directories or searching for items.

| Argument | Description |
| --- | --- |
| `target` | Target directory for scanning or searching (Defaults to `.`). |
| `--version` | Show program's version number and exit. |
| `--find`, `-f` | **Search Mode**. Returns exact and fuzzy matches + a saved report. |
| `--format`, `-F` | Output format: `md` (default), `txt`, or `image`. |
| `--name`, `-n` | Custom output filename. |
| `--outdir`, `-o` | Where to save the result. |
| `--show-hidden` | Include hidden files in the scan. |
| `--depth`, `-d` | Maximum recursion depth. |
| `--exclude`, `-e` | List of items to ignore. **Supports globs (e.g., `*.pyc`, `__pycache__`)**. |
| `--full` | **Power Mode**. Appends the full text content of all scanned source files. |
| `--text` | **Smart Filter**. Only scan text-based files (ignores binary/media). |
| `--delete` | **Cleanup Mode**. Permanently delete items matched by `--find` (Interactive TTY only). |
| `--verbose`, `-v` | Enable debug logging. |
| `--quiet`, `-q` | Silent mode. Only show critical errors. |

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

## 📂 Project Structure (v2.2.3)

```text
Seedling/
├── seedling/                  # Core Package
│   ├── commands/              # CLI Command Routers
│   │   ├── scan/              # Scan logic (explorer, search, full)
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

Seedling v2.2.3 has been fortified to survive extreme edge cases and chaotic inputs:

* **Recursion & Mount Loop Defense**: Directory traversal uses an iterative Stack-DFS tracking resolved physical paths. It mathematically eliminates `RecursionError` and instantly blocks infinite OS-level bind mount or hard link loops.
* **Markdown Fence Collision Immunity**: The parser calculates dynamic backtick boundaries, allowing Seedling to flawlessly bundle and reconstruct documents containing nested code blocks (like its own source code) without truncation.
* **Symlink Deletion Safety**: Search and delete operations explicitly sever symbolic links without following them, protecting host systems from catastrophic cascade deletions.
* **Pre-Processing Sandbox**: The `build` engine executes a Phase 1 simulation resolving virtual paths. It intercepts zero-day path traversal attacks (e.g., `../../../`) *before* any disk operations occur.
* **Image Bomb Prevention**: Restricts visual exports to a safe 1500-line limit to prevent Pillow rendering crashes.
* **Smart Encoding Fallback**: Safely reads legacy codebases using an automated fallback chain (`UTF-8 -> GBK -> Big5 -> UTF-16 -> Latin-1`).

---

## 📜 Changelog

Detailed changes for each release are documented in the [CHANGELOG.md](CHANGELOG.md) file.

### Latest Update: v2.2.3 (The Ironclad Sandbox Update)

* **Dynamic Markdown Fencing**: Completely resolved Markdown "Inception" bugs. Seedling now dynamically calculates the necessary backtick fences to safely wrap and restore nested code blocks.
* **Wildcard Exclusions**: Upgraded `--exclude` to support `fnmatch` globs (e.g., `*.js`, `secret.*`), making filtering vastly more powerful.
* **Magic Number Detection**: Replaced the basic null-byte check with strict file signature matching (PNG, JPEG, ELF, ZIP, PDF) to definitively block binary files masquerading as text.
* **CI/CD TTY Enforcement**: The UI engine now actively detects headless pipelines and safely defaults to "No" on destructive prompts to prevent hanging servers.
* **Symlink & Fuzzy Deletion Locks**: Severely restricted `--delete` to physically unlink symlinks instead of traversing them, and added a secondary confirmation prompt for fuzzy matches.
* **True Memory Bounds**: Fixed physical RAM calculations to strictly account for UTF-8 decoded string inflation, fully preventing Out-Of-Memory kills on embedded devices.
