#!/bin/bash
# Seedling-tools Ultimate Automated Test Suite
# Copyright (c) 2026 Kaelen Chow. All rights reserved.  

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

export PATH="$HOME/.local/bin:$USERPROFILE/.local/bin:$PATH"
TEST_DIR="$HOME/tmp/seedling_test_sandbox"
OUT_DIR="$HOME/tmp/seedling_test_out"

echo -e "${BLUE}   Starting Seedling ULTIMATE E2E Test Suite... ${NC}"
echo -e "\n${GREEN}Executing Seedling Unified E2E Tests...${NC}"
echo -e "  -> [Setup] Creating COMPLEX dummy project in $HOME/tmp..."
if [[ "$TEST_DIR" != "$HOME/tmp/"* || "$OUT_DIR" != "$HOME/tmp/"* ]]; then
    echo -e "${RED}CRITICAL: Invalid test directory path detected!${NC}"
    exit 1
fi

rm -rf "$TEST_DIR" "$OUT_DIR"
mkdir -p "$TEST_DIR/src/nested/deep" "$TEST_DIR/node_modules" "$TEST_DIR/.hidden" "$OUT_DIR"
mkdir -p "$TEST_DIR/build/logs" "$TEST_DIR/src/build"

# Standard Data
echo "print('Hello World')" > "$TEST_DIR/src/main.py"
echo "def add(a, b): return a + b" > "$TEST_DIR/src/nested/utils.py"
echo "# My Awesome App" > "$TEST_DIR/README.md"
echo "fake_binary" > "$TEST_DIR/image.png"

# Real Binary File with Null Bytes
printf "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" > "$TEST_DIR/real_binary.png"

# Broken Symlink
ln -s "$TEST_DIR/nowhere.txt" "$TEST_DIR/broken_link.txt" 2>/dev/null || true

# Malicious Blueprints for Path Traversal Test
cat << 'EOF' > "$TEST_DIR/malicious.md"
# 恶意蓝图
```text
root/
└── ../../../escaped.txt
```
EOF

cat << 'EOF' > "$TEST_DIR/valid_blueprint.md"
```text
root/
├── fileA.txt
└── folderB/
```
### FILE: fileA.txt
```text
Hello Build!
```
EOF

cat << 'EOF' > "$TEST_DIR/src/config.py"
# Configuration file
DEBUG = True
VERSION = "1.0.0"
def get_config():
    return {"debug": DEBUG}
EOF

cat << 'EOF' > "$TEST_DIR/src/app.js"
// Main application
const express = require('express');
function main() {
    console.log('Hello JS');
}
EOF

echo "node_modules content" > "$TEST_DIR/node_modules/package.js"

cat << 'EOF' > "$TEST_DIR/src/case_test.py"
# Test file for case sensitivity
def TODO():
    pass
def todo():
    pass
EOF

echo -e "  -> Testing SECURITY: Dangerous Deletion TTY Interception..."
OUTPUT=$(echo "CONFIRM DELETE" | scan "$TEST_DIR" -f "none" --delete 2>&1 || true)
if [[ ! "$OUTPUT" == *"interactive terminal"* ]]; then
    echo -e "${RED}Security Bypass! TTY check failed.${NC}"
    echo -e "${YELLOW}Actual output was: \n${OUTPUT}${NC}"
    exit 1
fi

echo -e "  -> Testing SECURITY: Path Traversal Interception..."
build "$TEST_DIR/malicious.md" "$OUT_DIR/safe_build" --force >/dev/null 2>&1 || true
if [ -f "$OUT_DIR/escaped.txt" ] || [ -f "escaped.txt" ]; then
    echo -e "${RED}CRITICAL: Security Bypass! Path traversal succeeded.${NC}"; exit 1
fi

echo -e "  -> Testing SECURITY: Image Memory Bomb Limit..."
mkdir -p "$TEST_DIR/huge_dir"
seq 1 1505 | xargs -I {} touch "$TEST_DIR/huge_dir/file_{}.txt"
OUTPUT=$(scan "$TEST_DIR/huge_dir" -F image -o "$OUT_DIR" -n "huge.png" 2>&1 || true)

if [[ "$OUTPUT" == *"'Pillow' is required"* ]]; then
    echo -e "${YELLOW}     Skipping Image memory bomb check: Pillow not installed.${NC}"
elif [[ ! "$OUTPUT" == *"memory overflow"* ]]; then
    echo -e "${RED}Image memory bomb check failed! Output was: $OUTPUT${NC}"; exit 1
else
    echo "     Image memory bomb intercepted successfully."
fi

echo -e "  -> Testing ENGINE: Build Engine Blueprint Reconstruction..."
build "$TEST_DIR/valid_blueprint.md" "$OUT_DIR/valid_build" >/dev/null 2>&1 || true
if [ ! -d "$OUT_DIR/valid_build/folderB" ] || ! grep -q "Hello Build!" "$OUT_DIR/valid_build/fileA.txt"; then
    echo -e "${RED}Build engine failed to reconstruct blueprint!${NC}"; exit 1
fi

echo -e "  -> Testing ENGINE: Complex Markdown Fence & Smart Path Recognition..."
cat << 'EOF' > "$TEST_DIR/complex_fence_blueprint.md"
```text
root/
└── tests/
    └── __init__.py
```
### FILE: __init__.py
````python
"""
This is a nested docstring containing markdown blocks.
```text
I am nested and should not break the parser!
```
"""
def init_test(): pass
````
EOF

build "$TEST_DIR/complex_fence_blueprint.md" "$OUT_DIR/smart_build" >/dev/null 2>&1 || true

if [ -f "$OUT_DIR/smart_build/__init__.py" ]; then
    echo -e "${RED}Smart path recognition failed! Created __init__.py at root instead of tests/.${NC}"; exit 1
fi
if [ ! -f "$OUT_DIR/smart_build/tests/__init__.py" ]; then
    echo -e "${RED}Smart path recognition failed! tests/__init__.py was not created.${NC}"; exit 1
fi
if ! grep -q "I am nested" "$OUT_DIR/smart_build/tests/__init__.py"; then
    echo -e "${RED}Complex fence parsing failed! Nested backticks truncated the file.${NC}"; exit 1
fi
echo "     Complex fence and smart path recognition working."

echo -e "  -> Testing ENGINE: Direct Creation Flag (-d)..."
build -d "$OUT_DIR/direct_create_file.py" >/dev/null 2>&1 || true
if [ ! -f "$OUT_DIR/direct_create_file.py" ]; then
    echo -e "${RED}Direct creation flag (-d) failed to create file!${NC}"; exit 1
fi

echo -e "  -> Testing ENGINE: Binary Detection & Skipping (--full)..."
scan "$TEST_DIR" --full -o "$OUT_DIR" -n "binary_test.md" >/dev/null 2>&1
if grep -q "IHDR" "$OUT_DIR/binary_test.md"; then
    echo -e "${RED}Binary detection failed! Binary content leaked into text report.${NC}"; exit 1
fi

echo -e "  -> Testing ENGINE: Broken Symlink Resilience..."
scan "$TEST_DIR" -o "$OUT_DIR" -n "symlink_test.md" >/dev/null 2>&1 || true
if [ ! -f "$OUT_DIR/symlink_test.md" ]; then
     echo -e "${RED}Scan crashed upon encountering a broken symlink!${NC}"; exit 1
fi

echo -e "  -> Testing ENGINE: Basic Scans & Directory Trailing Slashes (/)..."
scan "$TEST_DIR" -F txt -o "$OUT_DIR" -n basic_scan.txt >/dev/null
if ! grep -q "src/" "$OUT_DIR/basic_scan.txt"; then
    echo -e "${RED}Trailing slash feature failed!${NC}"; exit 1
fi

echo -e "  -> Testing ENGINE: Smart Exclude with Root Path Anchoring (/build/)..."
cat << 'EOF' > "$TEST_DIR/.myignore"
/build/
*.log
EOF
echo "y" | scan "$TEST_DIR" -e "$TEST_DIR/.myignore" -o "$OUT_DIR" -n "anchoring_test.md" >/dev/null
if grep -q "build/logs" "$OUT_DIR/anchoring_test.md"; then
    echo -e "${RED}Anchoring failed! /build/ should have ignored the root build directory.${NC}"; exit 1
fi
if ! grep -A 2 "src/" "$OUT_DIR/anchoring_test.md" | grep -q "build/"; then
    echo -e "${RED}Over-filtering! /build/ should NOT have ignored src/build/.${NC}"; exit 1
fi

echo -e "  -> Testing UX: Smart Exclude Fuzzy Matching (Typo correction)..."
echo "*.tmp" > "$TEST_DIR/.gitignore"
OUTPUT=$(scan "$TEST_DIR" -e "./gitignore" < /dev/null 2>&1 || true)
if [[ "$OUTPUT" != *"Could not find './gitignore'"* ]] || [[ "$OUTPUT" != *"found '.gitignore'"* ]]; then
    echo -e "${RED}Fuzzy matching prompt failed! Output was: $OUTPUT${NC}"; exit 1
fi
echo "     Fuzzy matching prompted correctly."

echo -e "  -> Testing ENGINE: File Type Filter (--type py)..."
scan "$TEST_DIR" --type py -d 2 -o "$OUT_DIR" -n "type_py.md" >/dev/null
if grep -q "app.js" "$OUT_DIR/type_py.md"; then
    echo -e "${RED}Type filter failed! JS file should not appear in --type py scan.${NC}"; exit 1
fi
if ! grep -q "main.py" "$OUT_DIR/type_py.md"; then
    echo -e "${RED}Type filter failed! Python file should appear in --type py scan.${NC}"; exit 1
fi
echo "     Type filter working."

echo -e "  -> Testing ENGINE: Include Filter (--include)..."
scan "$TEST_DIR" --include "*.py" -d 2 -o "$OUT_DIR" -n "include_py.md" >/dev/null
if grep -q "README.md" "$OUT_DIR/include_py.md"; then
    echo -e "${RED}Include filter failed! .md file should not appear with --include *.py.${NC}"; exit 1
fi
echo "     Include filter working."

echo -e "  -> Testing UX: Flag Conflict Intercept (--full vs --skeleton)..."
if scan "$TEST_DIR" --full --skeleton 2>&1 | grep -Eiq "conflicting|not allowed|cannot be used together"; then
    echo -e "     Correctly blocked conflicting flags."
else
    echo -e "${RED}UX Failure: Should have blocked simultaneous --full and --skeleton flags.${NC}"; exit 1
fi

echo -e "  -> Testing UX: Quiet Mode (-q)..."
OUTPUT=$(scan "$TEST_DIR" -q -o "$OUT_DIR" -n "quiet_test.md" 2>&1 || true)
if [[ -n "$OUTPUT" ]]; then
    echo -e "${RED}Quiet mode failed! Expected no stdout, got: $OUTPUT${NC}"; exit 1
fi

echo -e "  -> Testing PLUGIN: Find Mode (Exact & Highlighting)..."
scan "$TEST_DIR" -f "main" --full -o "$OUT_DIR" -n search_exact.md >/dev/null
if ! grep -q "MATCHED" "$OUT_DIR/search_exact.md"; then
    echo -e "${RED}Search mode failed to generate highlighted tree.${NC}"; exit 1
fi

echo -e "  -> Testing PLUGIN: Regex Search Mode (--regex)..."
OUTPUT=$(scan "$TEST_DIR" -f ".*\.py" --regex -d 2 2>&1 || true)
if [[ "$OUTPUT" != *"main.py"* ]]; then
    echo -e "${RED}Regex search failed! Pattern .*\.py should match main.py.${NC}"; exit 1
fi
echo "     Regex search working."

echo -e "  -> Testing PLUGIN: Search Power Mode (Report + Code)..."
scan "$TEST_DIR" -f "utils" --full -o "$OUT_DIR" -n "search_full_report.md" >/dev/null
if [ ! -f "$OUT_DIR/search_full_report.md" ] || ! grep -q "def add(a, b)" "$OUT_DIR/search_full_report.md"; then
    echo -e "${RED}Search Power Mode failed to bundle source code.${NC}"; exit 1
fi

echo -e "  -> Testing PLUGIN: Grep Mode (--grep)..."
scan "$TEST_DIR" --grep "DEBUG" --type py -o "$OUT_DIR" -n "grep_results.md" >/dev/null 2>&1 || true
if [ -f "$OUT_DIR/grep_results.md" ]; then
    if ! grep -q "DEBUG" "$OUT_DIR/grep_results.md"; then
        echo -e "${RED}Grep mode failed! Should find DEBUG in config.py.${NC}"; exit 1
    fi
fi
echo "     Grep mode working."

echo -e "  -> Testing PLUGIN: Grep Mode with Context (-C 2)..."
OUTPUT=$(scan "$TEST_DIR" --grep "def get_config" --type py -C 2 2>&1 || true)
if [[ "$OUTPUT" != *"DEBUG"* ]] || [[ "$OUTPUT" != *"return"* ]]; then
    echo -e "${RED}Grep context failed! Should show surrounding lines.${NC}"; exit 1
fi
echo "     Grep with context working."

echo -e "  -> Testing PLUGIN: Grep Case Sensitivity (-i flag)..."
OUTPUT=$(scan "$TEST_DIR" --grep "todo" --type py 2>&1 || true)
if [[ "$OUTPUT" == *"TODO()"* ]]; then
    echo -e "${RED}Case-sensitive grep failed! Should NOT find 'TODO' when searching 'todo'.${NC}"; exit 1
fi
OUTPUT=$(scan "$TEST_DIR" --grep "todo" --type py -i 2>&1 || true)
if [[ "$OUTPUT" != *"TODO()"* ]]; then
    echo -e "${RED}Case-insensitive grep failed! Should find 'TODO' with -i flag.${NC}"; exit 1
fi
echo "     Grep case sensitivity working."

echo -e "  -> Testing PLUGIN: Combined Filters (--type py --grep)..."
OUTPUT=$(scan "$TEST_DIR" --grep "def" --type py -C 1 2>&1 || true)
if [[ "$OUTPUT" != *"def"* ]]; then
    echo -e "${RED}Combined filter failed! Should find 'def' in Python files.${NC}"; exit 1
fi
if [[ "$OUTPUT" == *"app.js"* ]]; then
    echo -e "${RED}Combined filter failed! Should not search JS files with --type py.${NC}"; exit 1
fi
echo "     Combined filters working."

echo -e "  -> Testing PLUGIN: Analyze Mode (--analyze)..."
scan "$TEST_DIR" --analyze -o "$OUT_DIR" >/dev/null 2>&1
if [ ! -f "$OUT_DIR/seedling_test_sandbox_analysis.md" ]; then
    echo -e "${RED}Analyze mode failed to create output file!${NC}"; exit 1
fi
if ! grep -q "\*\*Type\*\*:" "$OUT_DIR/seedling_test_sandbox_analysis.md"; then
    echo -e "${RED}Analyze output missing project type!${NC}"; exit 1
fi
echo "     Analyze mode working."

echo -e "  -> Testing PLUGIN: AST Code Skeleton Extraction (--skeleton)..."
if python3 -c "import ast; hasattr(ast, 'unparse') or exit(1)" 2>/dev/null; then
    cat << 'EOF' > "$TEST_DIR/src/ast_complex.py"
class DataModel:
    """This is the core data model."""
    def compute(self):
        print("Complex logic here")
        return 42
EOF
    scan "$TEST_DIR" --skeleton -o "$OUT_DIR" -n "skeleton.md" >/dev/null
    if ! grep -q "class DataModel:" "$OUT_DIR/skeleton.md"; then
        echo -e "${RED}Skeleton extraction failed to preserve class structure.${NC}"; exit 1
    fi
    if grep -q "Complex logic" "$OUT_DIR/skeleton.md"; then
        echo -e "${RED}Skeleton extraction failed to strip implementation logic.${NC}"; exit 1
    fi
else
    echo -e "${YELLOW}     Skipping AST test: Python < 3.9.${NC}"
fi

echo -e "  -> Testing EXPORTER: JSON Output Mode (-F json)..."
scan "$TEST_DIR" -F json -d 2 -o "$OUT_DIR" -n "json_output.json" >/dev/null
if [ ! -f "$OUT_DIR/json_output.json" ]; then
    echo -e "${RED}JSON output file not created!${NC}"; exit 1
fi
if ! grep -q '"meta"' "$OUT_DIR/json_output.json" || ! grep -q '"tree"' "$OUT_DIR/json_output.json"; then
    echo -e "${RED}JSON output missing required fields!${NC}"; exit 1
fi
if ! python3 -c "import sys, json; json.load(open(sys.argv[1], encoding='utf-8'))" "$OUT_DIR/json_output.json" 2>/dev/null; then
    echo -e "${RED}JSON output is not valid JSON!${NC}"; exit 1
fi
echo "     JSON output validated."

echo -e "  -> Testing EXPORTER: JSON Output with --full..."
scan "$TEST_DIR" -F json --full -d 1 -o "$OUT_DIR" -n "json_full.json" >/dev/null
if ! grep -q '"contents"' "$OUT_DIR/json_full.json"; then
    echo -e "${RED}JSON --full failed! Should include contents field.${NC}"; exit 1
fi
echo "     JSON with --full working."

echo -e "${GREEN}   ALL TESTS PASSED! ${NC}"

if [[ "$TEST_DIR" == "$HOME/tmp/"* && "$OUT_DIR" == "$HOME/tmp/"* ]]; then
    rm -rf "$TEST_DIR" "$OUT_DIR"
    rm -f seedling_test_sandbox*.md \
          seedling_test_sandbox*.txt \
          seedling_test_sandbox*.json \
          seedling_test_sandbox*.png
    echo -e "${BLUE}   Cleaned up all temporary files and test artifacts. ${NC}"
fi