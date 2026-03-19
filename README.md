# 🌲 Seedling (v2.3.1)

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling** is a high-performance, 3-in-1 CLI toolkit designed for developers to explore, search, and reconstruct directory structures. Whether you need a beautiful image of your project architecture, a way to spawn a project from a text blueprint, or a context-optimized codebase skeleton for LLMs, Seedling has you covered.

Read this document in other languages: [简体中文](docs/README_zh.md)

---

## 🛠️ Installation

Seedling is designed to be installed globally via `pipx` for a clean, isolated environment.
```
pipx install Seedling-tools
```

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

You can now use Seedling's core features directly in your Python code via the `ScanConfig` engine:

```python
import seedling
from seedling.core.filesystem import ScanConfig

# 1. Initialize configuration (Set quiet=True to suppress CLI progress bars)
config = ScanConfig(max_depth=2, quiet=True)

# 2. Generate directory tree lines
stats = {"dirs": 0, "files": 0}
lines = seedling.scan_dir_lines("./src", config, stats)
print("\n".join(lines))

# 3. Search for specific items programmatically
exact, fuzzy = seedling.search_items(".", keyword="utils", config=config)

# 4. Reconstruct a project from a blueprint
seedling.build_structure_from_file("blueprint.md", "./new_project")
```

---

## 📖 CLI Reference

Seedling 2.3.1 uses a clean, explicit argument system. 

### 1. `scan` - The Explorer

Used for scanning directories, extracting code skeletons, or searching for items. Note: `--full` and `--skeleton` are mutually exclusive.

| Argument | Description |
| --- | --- |
| `target` | Target directory for scanning or searching (Defaults to `.`). |
| `--find`, `-f` | **Search Mode**. Fast CLI search (Exact & Fuzzy). Combine with `--full` to export a code report. |
| `--format`, `-F` | Output format: `md` (default), `txt`, or `image`. |
| `--name`, `-n` | Custom output filename. |
| `--outdir`, `-o` | Where to save the result. |
| `--showhidden` | Include hidden files in the scan. |
| `--depth`, `-d` | Maximum recursion depth. |
| `--exclude`, `-e` | List of items to ignore. **Smart parse: auto-reads `.gitignore` files or accepts globs**. |
| `--full` | **Power Mode**. Appends the full text content of all scanned source files. |
| `--skeleton` | **[Experimental]** AST Code Skeleton extraction. Strips logic, retains signatures. |
| `--text` | **Smart Filter**. Only scan text-based files (ignores binary/media). |
| `--delete` | **Cleanup Mode**. Permanently delete items matched by `--find` (Interactive TTY only). |
| `--verbose` / `-q`| Verbose mode (`-v`) or Quiet mode (`-q`). |

### 2. `build` - The Architect

Turn a text-based tree into a real file system, or restore a project from a snapshot.

| Argument | Description |
| --- | --- |
| `file` | The source tree blueprint file (`.txt` or `.md`). |
| `target` | Where to build the structure (Defaults to current directory). |
| `--direct`, `-d` | **Direct Mode**. Bypass prompts to instantly create a specific path. |
| `--check` | **Dry-Run**. Simulate the build and report missing/existing items. |
| `--force` | **Force Mode**. Overwrite existing files without skipping. |

---

## 📂 Project Structure (v2.3.1)

```text
Seedling/
├── docs/                      # Documentation & Changelogs
│   ├── CHANGELOG.md           # English version history
│   ├── CHANGELOG_zh.md        # Chinese version history
│   └── README_zh.md           # Chinese documentation
├── seedling/                  # Core Package 
│   ├── commands/              # CLI Command Routers
│   │   ├── build/             # Build logic
│   │   └── scan/              # Scan logic
│   ├── core/                  # Shared Engines
│   │   ├── filesystem.py      # Iterative DFS, ScanConfig & Filtering
│   │   ├── io.py              # File R/W, Fence Collision & Path Safety
│   │   ├── logger.py          # Centralized CLI Formatter
│   │   ├── sysinfo.py         # Hardware Probe
│   │   └── ui.py              # Animations & CI/CD checks
│   ├── __init__.py            # Public API & Metadata
│   └── main.py                # CLI Entry Point Router
├── tests/                     # Unit Tests (Core, Edge Cases & IO)
├── install.bat                # Windows one-click installer
├── install.sh                 # Linux/macOS one-click installer
├── LICENSE                    # MIT License
├── pyproject.toml             # Build configuration & Package metadata
├── pytest.ini                 # Pytest configuration file
├── README.md                  # Main documentation
└── test_suite.sh              # Automated E2E tests
```

---

## 📜 Changelog

Detailed changes for each release are documented in the [docs/CHANGELOG.md](docs/CHANGELOG.md) file.