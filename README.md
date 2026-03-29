# Seedling-tools

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling-tools** is a high-performance CLI toolkit designed for codebase exploration, intelligent analysis, and LLM context aggregation.

Core Capabilities:
1. SCAN: Export directory trees to Markdown, TXT, JSON, or Images.
2. FIND & GREP: Perform exact/fuzzy file searches and regex-based content matching.
3. ANALYZE: Auto-detect project architecture, dependencies, and entry points.
4. SKELETON: Extract Python AST structures (stripping implementation logic).
5. POWER MODE: Aggregate full repository source code for LLM prompts.
6. BUILD: Reconstruct physical file systems from text-based blueprints.

Powered by a unified, single-pass caching traversal engine.

Read this document in other languages: [简体中文](https://github.com/bbpeaches/Seedling/blob/main/docs/README_zh.md)

---

## Installation

Seedling-tools is designed to be installed globally via `pipx` for a clean, isolated environment.
```bash
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

## Python Library Usage

You can now use Seedling's core features directly in your Python code via the `ScanConfig` engine:

```python
import seedlingtools
from pathlib import Path
from seedlingtools.core import ScanConfig, DepthFirstTraverser, StandardTreeRenderer

# Initialize Configuration
config = ScanConfig(max_depth=2, quiet=True)

# Taking Memory Snapshots
traverser = DepthFirstTraverser()
result = traverser.traverse(Path("./src"), config)

# Render tree lines
renderer = StandardTreeRenderer()
lines = renderer.render(result, config)
print("\n".join(lines))
```

---

## CLI Reference

Seedling-tools uses a clean, explicit argument system.

### 1. `scan` - The Explorer

Used for scanning directories, extracting code skeletons, or searching for items. Note: `--full` and `--skeleton` are mutually exclusive.

| Argument | Description |
| --- | --- |
| `target` | Target directory for scanning or searching (Defaults to `.`). |
| `--find`, `-f` | **Search Mode**. Fast CLI search (Exact & Fuzzy). Combine with `--full` to export a code report. |
| `--format`, `-F` | Output format: `md` (default), `txt`, `json`, or `image`. |
| `--name`, `-n` | Custom output filename. |
| `--outdir`, `-o` | Where to save the result. |
| `--showhidden` | Include hidden files in the scan. |
| `--depth`, `-d` | Maximum recursion depth. |
| `--exclude`, `-e` | List of items to ignore. **Smart parse: auto-reads `.gitignore` files or accepts globs**. |
| `--include` | Only include files/directories matching patterns (e.g., `--include "*.py"`). |
| `--type`, `-t` | Filter by file type: `py`, `js`, `ts`, `cpp`, `go`, `java`, `rs`, `web`, `json`, `yaml`, `md`, `shell`, `all`. |
| `--regex` | Treat `-f` pattern as regular expression. |
| `--grep`, `-g` | Search inside file contents (Content Search Mode). |
| `-C`, `--context` | Show N lines of context around grep matches. |
| `--analyze` | Analyze project structure, type, dependencies, and architecture. |
| `--full` | **Power Mode**. Appends the full text content of all scanned source files. |
| `--skeleton` | **[Experimental]** AST Code Skeleton extraction. Strips logic, retains signatures. |
| `--text` | **Smart Filter**. Only scan text-based files (ignores binary/media). |
| `--delete` | **Cleanup Mode**. Permanently delete items matched by `--find` (Interactive TTY only). |
| `--dry-run` | Preview deletions without executing (use with `--delete`). |
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

## New in v2.5

### Modular Plugin & Orchestration System
- **Scan Pipeline**: Advanced scanning modes (`--analyze`, `--grep`, `--skeleton`, `--find`) are now fully modularized via the `ScanOrchestrator` engine.
- **Build Pipeline**: The reverse-build mode has been upgraded to a symmetrical `BuildOrchestrator` architecture. This completely decouples topology parsing (`parsers`), pre-flight interception (`plugins`, e.g., `--check`), and physical disk operations (`executors`).

### Unified Infrastructure
- Centralized low-level file I/O, security boundary validation, and system interactions into robust global singletons (`logger`, `terminal`, `io_processor`, `image_renderer`).
- Introduced a unified exception hierarchy (`SeedlingToolsError` and its derivatives) for precise, context-aware domain error reporting.

### Future-Proofing & Roadmap
- v2.5.1 Architectural Hooks: The core layer is now pre-wired with logical hooks for Token estimation, Structured XML export, and Remote repository scanning, laying a solid foundation for the LLM-centric enhancements in the next release.

---

## Project Structure (v2.5)

```text
Seedling/
├── docs/                      # Documentation & Changelogs        
├── seedlingtools/            # Core Package
│   ├── commands/              # CLI Command Routers
│   │   ├── build/             # Build logic
│   │   └── scan/              # Scan logic
│   ├── core/                  # Shared Core Engines
│   ├── utils/                 # Unified Infrastructure & Constants
│   ├── __init__.py            # Public API & Metadata exposure
│   └── main.py                # CLI Entry Point Dispatcher
├── tests/                     # Unit Test      
├── install.bat                
├── install.sh                 
├── LICENSE                    
├── pyproject.toml             
├── pytest.ini                 
├── README.md                  
└── test_suite.sh              # E2E Automated Checks
```

---

## Changelog

Detailed changes for each release are documented in the [docs/CHANGELOG.md](https://github.com/bbpeaches/Seedling/blob/main/docs/CHANGELOG.md) file.