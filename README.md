# Seedling-tools

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling-tools** is a high-performance CLI toolkit designed for codebase exploration, intelligent analysis, and LLM context aggregation.

Core Capabilities:
1.  **SCAN**: Serialize and export directory tree structures to Markdown, TXT, JSON, XML, or high-definition image formats.
2.  **FIND & GREP**: Perform exact or fuzzy filename searches, as well as cross-file full-text content matching based on regular expressions.
3.  **ANALYZE**: Automatically detect project architecture patterns, core dependency package matrices, and program command entry points.
4.  **SKELETON**: Extract Python code skeletons based on AST, automatically stripping underlying implementation logic to retain only the top-level signatures of classes and functions.
5.  **POWER MODE**: Fully aggregate the source code of the target codebase, with a built-in heuristic Token consumption estimation engine to provide an extremely pure context for LLMs.
6.  **TEMPLATE**: Prompt template engine, enabling automated context assembly and LLM review instruction injection via the `{{SEEDLING_CONTEXT}}` placeholder.
7.  **REMOTE**: Supports remote Git URLs, instantly completing repository cloning, parsing, and secure destruction in an independent sandbox.
8.  **BUILD**: Parse plaintext topology blueprints, perform conflict-free pre-checks, and reverse-engineer/build a real physical file system with one click.

Read this document in other languages: [简体中文](https://github.com/bbpeaches/Seedling/blob/main/docs/README_zh.md)

-----

## Installation
Seedling-tools is recommended to be installed globally via `pipx` to ensure a clean, isolated environment.
```bash
pipx install Seedling-tools
```

### One-Click Setup
  * **Windows**: Run `./install.bat`
  * **macOS / Linux**: Run `bash install.sh`

### Developer / Manual Install
If you need to modify the source code, please use **Editable Mode**:
```bash
pipx install -e . --force
```

-----

## Python Library Usage
You can now use Seedling's core features directly in your Python code:
```python
import seedlingtools
from pathlib import Path
from seedlingtools.core import ScanConfig, DepthFirstTraverser, StandardTreeRenderer

# Initialize configuration
config = ScanConfig(max_depth=2, quiet=True)

# Take memory snapshot
traverser = DepthFirstTraverser()
result = traverser.traverse(Path("./src"), config)

# Render tree lines
renderer = StandardTreeRenderer()
lines = renderer.render(result, config)
print("\n".join(lines))
```

-----

## Command Line Usage
The core advantage of Seedling-tools is its ability to cleanly and efficiently aggregate complex codebases into structured text that LLMs can directly digest.

### Scenario 1: Providing the Entire Backend Context to an LLM
If you are a Python developer and need an LLM to help you review or refactor backend business logic, you can use a combined command to accurately grab all Python files, excluding unnecessary cache and test files:
```bash
scan . -t py -e .gitignore --full
```
This generates a Markdown file with the directory tree and full source code, while automatically filtering out multimedia files and non-Python code, saving valuable Tokens.

### Scenario 2: Automated Review Based on Prompt Templates
You can write a prompt file in advance. Leave a `{{SEEDLING_CONTEXT}}` placeholder in the template, and Seedling will automatically inject the generated context into that position after the scan is complete. For example, using the official example template provided in this project [docs/prompt\_example.md](https://github.com/bbpeaches/Seedling/blob/main/docs/prompt_example.md):
```bash
scan . --full --template docs/prompt_example.md -o ./reports -n output_report.md -e ".gitignore"
```

### Scenario 3: Instant Scanning of Open-Source Projects
No need to manually clone the entire repository. Pass the remote Git URL directly to Seedling, and it will clone, analyze, and aggregate the context in a temporary directory, automatically destroying and cleaning it up when finished:
```bash
scan https://github.com/bbpeaches/Seedling.git -t py --analyze --full
```

-----

## CLI Reference
Seedling-tools uses a clean, explicit argument system.

### 1. `scan`  
Used for scanning directories, extracting code skeletons, or searching for items. Note: `--full` and `--skeleton` are mutually exclusive parameters.

| Argument | Description |
| --- | --- |
| `target` | Target directory to scan or search, **or a remote Git repository URL**. |
| `--find`, `-f` | **Search Mode**. Fast CLI search (Exact & Fuzzy). Combine with `--full` to export code reports. |
| `--format`, `-F` | Output format: `md` (default), `txt`, `json`, `xml` or `image`. |
| `--name`, `-n` | Custom output filename. |
| `--outdir`, `-o` | Target directory path to save the results. |
| `--nohidden` | Exclude hidden files. (v2.5.1+ scans hidden files by default; explicitly declare this parameter to block them). |
| `--depth`, `-d` | Maximum recursion depth. |
| `--exclude`, `-e` | List of items to exclude. **Smart parse: auto-reads `.gitignore` files or accepts Globs**. |
| `--include` | Only include files/directories matching patterns (e.g., `--include "*.py"`). |
| `--type`, `-t` | Filter by file type: `py`, `js`, `ts`, `cpp`, `go`, `java`, `rs`, `web`, `json`, `yaml`, `md`, `shell`, `all`. |
| `--regex` | Treat `-f` or `-g` search patterns as regular expressions. |
| `--grep`, `-g` | Perform matching searches inside file contents. |
| `-C`, `--context` | Show N lines of context around grep matches. |
| `--analyze` | Analyze project macro-structure, type, dependencies, and architecture (combine with `--full` to append micro-source code at the end of the report). |
| `--template` | **Prompt Template Engine**. Pass a file path containing the `{{SEEDLING_CONTEXT}}` placeholder to automatically perform context injection assembly. |
| `--full` | **Power Mode**. Append the full text content of all scanned source files and automatically estimate total Token consumption. |
| `--skeleton` | **[Experimental]** AST Code Skeleton extraction. Automatically strips internal implementation logic, retaining only class and function signatures. |
| `--text` | **Smart Filter**. Force scanning of text-format files only (the underlying engine will automatically intercept and ignore binary/media files). |
| `--delete` | **Cleanup Mode**. Permanently delete items matched by `--find` (has security intercepts, only available in interactive TTY terminals). |
| `--dry-run` | Preview deletion operations without actually executing physical deletion (use with `--delete`). |
| `--verbose` / `-q`| Enable debug logging mode (`-v`) or quiet mode (`-q`). |

### 2. `build`
Turn a text-based tree blueprint into a real file system, or restore a project from a snapshot.

| Argument | Description |
| --- | --- |
| `file` | The source tree blueprint file (`.txt` or `.md`). |
| `target` | Storage location for the built structure (Defaults to the current execution directory). |
| `--direct`, `-d` | **Direct Mode**. Skip interactive prompts and immediately create the specified single file or folder path on disk. |
| `--check` | **Dry-Run Mode**. Perform a conflict-free simulated build and report missing, existing, or content-mismatched items. |
| `--force` | **Force Mode**. Directly overwrite files that already exist on the physical disk and have conflicting content without prompting to skip. |

-----

## v2.5 Core Features

### Smart Interaction & Filtering
  - **Smart Garbage File Interceptor**: Introduced heuristic detection logic to automatically identify and intercept project noise like `node_modules`, `.DS_Store`, `__pycache__`, etc.
  - **Intent-Aware & Interactive Downgrade**: The system can automatically distinguish between "expert mode" and "normal mode". In single search modes or non-interactive environments, it automatically downgrades to silent warnings without blocking the core workflow.

### Modular Plugins & Symmetrical Orchestration System
  - **Scan Pipeline**: Advanced scanning modes are now fully modularized via the `ScanOrchestrator` engine.
  - **Build Pipeline**: The reverse-build mode has been comprehensively upgraded to the `BuildOrchestrator` symmetrical orchestration architecture, completely decoupling topology parsing, pre-flight interception, and physical writing.

### LLM Enhanced Context Engine
  - **Structured XML Export**: Added `-F xml` format support.
  - **Token Estimation**: After each full scan and aggregation, automatically appends a heuristic algorithm-based Token consumption estimate to the terminal and the top of the output report, helping developers accurately control the context window limits of LLMs.
  - **Prompt Templates**: Added the `--template` parameter. Allows developers to pass in a custom review prompt file; Seedling will automatically and accurately inject the full code context into the `{{SEEDLING_CONTEXT}}` placeholder after scanning, generating a Prompt ready to be fed directly.
  - **Remote Repository Scanning**: CLI supports passing in Git HTTPS/SSH links directly.

### Unified Infrastructure
  - Centralized low-level file I/O, security boundary validation, Git lifecycle scheduling, and system interactions into robust global singleton instances.
  - Introduced a unified exception hierarchy, providing more precise domain-level error report interception containing debugging context.

-----

## Project Structure (v2.5)
```text
Seedling/
├── docs/                      # Documentation & Changelogs     
├── seedlingtools/             # Core Package
│   ├── commands/              # CLI Command Routers
│   │   ├── build/             # Reverse build pipeline
│   │   └── scan/              # Scan & analyze pipeline
│   ├── core/                  # Shared Core Engines     
│   ├── utils/                 # Global Infrastructure   
│   ├── __init__.py            # API & Package Metadata
│   └── main.py                # CLI Entry Dispatcher
├── tests/                     # Unit Test & E2E Automated Tests 
├── install.bat                
├── install.sh                 
├── LICENSE                    
├── pyproject.toml             
├── pytest.ini                 
├── README.md                  
└── run.sh                     # UT + E2E Automated Test Suite Entrypoint
```

-----

## Changelog

Detailed change history for each release is documented in the [docs/CHANGELOG.md](https://github.com/bbpeaches/Seedling/blob/main/docs/CHANGELOG.md) file.