# 🌲 Seedling (v2.2.2)

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling** is a high-performance, 3-in-1 CLI toolkit designed for developers to explore, search, and reconstruct directory structures. Whether you need a beautiful image of your project architecture or a way to spawn a project from a text blueprint, Seedling has you covered.

---

## 🚀 Key Features

* **Modular Architecture**: A completely rebuilt core engine, separating commands and core logic for infinite scaling and professional maintenance.
* **Auto OOM Protection [NEW]**: Intelligently probes your host's physical RAM. The `--full` context aggregator enforces a strict 10% memory ceiling, preventing system crashes when parsing massive monorepos.
* **Cross-Platform Rehydration [NEW]**: Generate a project snapshot on Windows (with `\` paths), and flawlessly restore the *entire* directory structure and source code on a Mac or Linux machine.
* **Public Python API (True Quiet Mode)**: Seedling is a library! You can `import seedling` in your scripts to use its powerful engines programmatically. With the new centralized logger, `quiet=True` ensures absolute zero stdout pollution.
* **Smart Text Filter (`--text`)**: Strictly ignore binary and media files during tree scanning. Features a **Heuristic Binary Check** that peeks at file headers to dynamically block disguised non-text files.
* **Dangerous Deletion (`--delete`)**: Search for files or folders and permanently wipe them out with a built-in TTY interactive lock requiring explicit confirmation.
* **Scan & Export**: Export directory trees to `Markdown`, `Plain Text`, or high-fidelity `PNG` images with full Chinese character support and automatic trailing slashes for directories.

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

Seedling 2.2.2 uses a clean, explicit argument system. All commands now support unified logging controls (`-v` / `-q`).

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
| `--exclude`, `-e` | List of files/directories to ignore. |
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

## 📂 Project Structure (v2.2.2)

```text
Seedling/
├── seedling/                  # Core Package
│   ├── commands/              # CLI Command Routers
│   │   ├── scan/              # Scan logic (explorer, search, full)
│   │   └── build/             # Build logic (architect)
│   ├── core/                  # Shared Engines
│   │   ├── filesystem.py      # Iterative Traversal & Text verification
│   │   ├── io.py              # File R/W, Paths & Image rendering
│   │   ├── logger.py          # Centralized CLI Formatter
│   │   ├── sysinfo.py         # Hardware Probe (RAM & Depth constraints)
│   │   └── ui.py              # Animations & Progress bars
│   ├── __init__.py            # Public API & Metadata
│   └── main.py                # Entry Point Router
├── pyproject.toml             # Build configuration
├── install.sh/bat             # One-click installers
└── test_suite.sh              # Ultimate E2E tests
```

---

## 🛡️ Stability & Hardening (The Unbreakable Engine)

Seedling v2.2.2 has been rewritten from the ground up to survive extreme edge cases:

* **Recursion DoS Prevention**: Directory traversal uses an iterative Stack-DFS (Depth-First Search) with a hard-capped limit of 1000 layers. Seedling will never crash from `RecursionError` on infinitely nested malicious structures.
* **Pre-Processing Sandbox**: The `build` engine executes a Phase 1 simulation, intercepting and blocking zero-day path traversal attacks (e.g., `../../../`) *before* any disk operations occur.
* **Smart Encoding Fallback**: Safely reads legacy codebases using an automated fallback chain (`UTF-8 -> GBK -> Big5 -> UTF-16 -> Latin-1`) to prevent corrupted text restoration.
* **TTY Delete Lock**: The `--delete` operation strictly verifies an interactive terminal and requires explicit `CONFIRM DELETE` typing, protecting CI/CD pipelines from automated destruction.
* **Symlink Loop Defense**: Detects and cleanly bypasses infinite directory loops.

---

## 📜 Changelog

Detailed changes for each release are documented in the [CHANGELOG.md](CHANGELOG.md) file.

### Latest Update: v2.2.2 (The Unbreakable Engine Update)

* **Auto OOM Protection**: Introduced hardware probing (`sysinfo.py`) to restrict file aggregation to 10% of physical RAM, preventing system-wide OOM crashes.
* **Cross-Platform Magic**: Replaced manual path handling with `PureWindowsPath`, allowing Mac/Linux users to flawlessly restore codebase snapshots generated on Windows machines.
* **Centralized Logging**: Stripped all raw `print()` statements for a customized `logger.py`, granting true silent execution (`quiet=True`) for API integrations.
* **Recursion Elimination**: Refactored the core file engine from recursive to iterative stack traversal, making it mathematically immune to stack overflow.
* **Heuristic Binary Blocking**: The file engine now peeks at the first 1024 bytes of unknown files to intercept and block disguised binaries containing null bytes.