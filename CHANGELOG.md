# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [1.0.0] - Initial Release

### 🎉 First Public Release
- **Directory Explorer (`scan`)**: The core functionality to traverse directories and generate visual tree representations.
- **Multi-Format Export**: Support for exporting the directory tree to Markdown (`.md`), Plain Text (`.txt`), and visually appealing Images (`.png`).
- **Find Engine**: Dual-mode search featuring Exact Match and Fuzzy Suggestions (powered by Levenshtein distance).
- **Power Mode (`--full`)**: The ability to aggregate and bundle the entire source code of a project into a single Markdown file, optimized for LLM context feeding.