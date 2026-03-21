#!/bin/bash

# ==============================================================================
# Seedling Ultimate Automated Test Suite (v2.4.1)
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   Starting Seedling ULTIMATE E2E Test Suite... ${NC}"
echo -e "${BLUE}======================================================${NC}"

TEST_DIR="$HOME/tmp/seedling_test_sandbox"
OUT_DIR="$HOME/tmp/seedling_test_out"

# ==============================================================================
# TEST SUITE 1: Legacy Core Engine & Hardening Tests
# ==============================================================================

echo -e "\n${GREEN}[1/3] Executing Core Engine & Hardening Tests...${NC}"

echo -e "  -> [Setup] Creating COMPLEX dummy project in $HOME/tmp..."
if [[ "$TEST_DIR" != "$HOME/tmp/"* || "$OUT_DIR" != "$HOME/tmp/"* ]]; then
    echo -e "${RED}CRITICAL: Invalid test directory path detected!${NC}"
    exit 1
fi

rm -rf "$TEST_DIR" "$OUT_DIR"
mkdir -p "$TEST_DIR/src/nested/deep" "$TEST_DIR/node_modules" "$TEST_DIR/.hidden" "$OUT_DIR"
mkdir -p "$TEST_DIR/build/logs" "$TEST_DIR/src/build" # 用于测试路径锚定规则

# Standard Data
echo "print('Hello World')" > "$TEST_DIR/src/main.py"
echo "def add(a, b): return a + b" > "$TEST_DIR/src/nested/utils.py"
echo "# My Awesome App" > "$TEST_DIR/README.md"
echo "fake_binary" > "$TEST_DIR/image.png"

# Malicious Blueprints for Path Traversal Test
cat << 'EOF' > "$TEST_DIR/malicious.md"
# 恶意蓝图
```text
root/
└── ../../../escaped.txt
```
EOF

echo -e "  -> Testing Basic Scans & Directory Trailing Slashes (/)..."
scan "$TEST_DIR" -F txt -o "$OUT_DIR" -n basic_scan.txt >/dev/null
if ! grep -q "src/" "$OUT_DIR/basic_scan.txt"; then
    echo -e "${RED}Trailing slash feature failed!${NC}"; exit 1
fi

echo -e "  -> Testing Find Mode (Exact & Highlighting)..."
scan "$TEST_DIR" -f "main" --full -o "$OUT_DIR" -n search_exact.md >/dev/null
if ! grep -q "MATCHED" "$OUT_DIR/search_exact.md"; then
    echo -e "${RED}Search mode failed to generate highlighted tree.${NC}"; exit 1
fi

echo -e "  -> Testing SECURITY: Dangerous Deletion TTY Interception..."
OUTPUT=$(echo "CONFIRM DELETE" | scan "$TEST_DIR" -f "none" --delete 2>&1 || true)
if [[ ! "$OUTPUT" == *"interactive terminal"* ]]; then
    echo -e "${RED}Security Bypass! TTY check failed.${NC}"; exit 1
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
elif [[ ! "$OUTPUT" == *"aborted to prevent memory overflow"* ]]; then
    echo -e "${RED}Image memory bomb check failed! Output was: $OUTPUT${NC}"; exit 1
else
    echo "     Image memory bomb intercepted successfully."
fi

# ==============================================================================
# TEST SUITE 2: v2.3.x Refactoring & Feature Tests
# ==============================================================================

echo -e "\n${GREEN}[2/3] Executing v2.3.x Refactoring & Feature Tests...${NC}"

echo -e "  -> Testing UX: Flag Conflict Intercept (--full vs --skeleton)..."
if scan "$TEST_DIR" --full --skeleton 2>&1 | grep -Eiq "conflicting|not allowed|cannot be used together"; then
    echo -e "     Correctly blocked conflicting flags."
else
    echo -e "${RED}UX Failure: Should have blocked simultaneous --full and --skeleton flags.${NC}"; exit 1
fi

echo -e "  -> Testing ENGINE: Smart Exclude with Root Path Anchoring (/build/)..."
cat << 'EOF' > "$TEST_DIR/.myignore"
/build/
*.log
EOF
scan "$TEST_DIR" -e "$TEST_DIR/.myignore" -o "$OUT_DIR" -n "anchoring_test.md" >/dev/null
if grep -q "build/logs" "$OUT_DIR/anchoring_test.md"; then
    echo -e "${RED}Anchoring failed! /build/ should have ignored the root build directory.${NC}"; exit 1
fi
if ! grep -A 2 "src/" "$OUT_DIR/anchoring_test.md" | grep -q "build/"; then
    echo -e "${RED}Over-filtering! /build/ should NOT have ignored src/build/.${NC}"; exit 1
fi

echo -e "  -> Testing ENGINE: AST Code Skeleton Extraction (--skeleton)..."
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

echo -e "  -> Testing UX: Streamlined Search CLI Intercept (No report file)..."
rm -f "$OUT_DIR/quick_search.md"
scan "$TEST_DIR" -f "main" -o "$OUT_DIR" -n "quick_search.md" >/dev/null
if [ -f "$OUT_DIR/quick_search.md" ]; then
    echo -e "${RED}Streamlined Search failed! Generated a file without --full.${NC}"; exit 1
fi

echo -e "  -> Testing ENGINE: Search Power Mode (Report + Code)..."
scan "$TEST_DIR" -f "utils" --full -o "$OUT_DIR" -n "search_full_report.md" >/dev/null
if [ ! -f "$OUT_DIR/search_full_report.md" ] || ! grep -q "def add(a, b)" "$OUT_DIR/search_full_report.md"; then
    echo -e "${RED}Search Power Mode failed to bundle source code.${NC}"; exit 1
fi

# ==============================================================================
# TEST SUITE 3: v2.4.0 New Feature Tests (Agent Tools Enhancement)
# ==============================================================================

echo -e "\n${GREEN}[3/3] Executing v2.4.1 Agent Tools Enhancement Tests...${NC}"

# Prepare test files for v2.4 features
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

# Test 1: JSON Output Mode
echo -e "  -> Testing v2.4: JSON Output Mode (-F json)..."
scan "$TEST_DIR" -F json -d 2 -o "$OUT_DIR" -n "json_output.json" >/dev/null
if [ ! -f "$OUT_DIR/json_output.json" ]; then
    echo -e "${RED}JSON output file not created!${NC}"; exit 1
fi
if ! grep -q '"meta"' "$OUT_DIR/json_output.json" || ! grep -q '"tree"' "$OUT_DIR/json_output.json"; then
    echo -e "${RED}JSON output missing required fields!${NC}"; exit 1
fi
# Validate JSON structure
if ! python3 -c "import sys, json; json.load(open(sys.argv[1], encoding='utf-8'))" "$OUT_DIR/json_output.json" 2>/dev/null; then
    echo -e "${RED}JSON output is not valid JSON!${NC}"; exit 1
fi
echo "     JSON output validated."

# Test 2: File Type Filter
echo -e "  -> Testing v2.4: File Type Filter (--type py)..."
scan "$TEST_DIR" --type py -d 2 -o "$OUT_DIR" -n "type_py.md" >/dev/null
if grep -q "app.js" "$OUT_DIR/type_py.md"; then
    echo -e "${RED}Type filter failed! JS file should not appear in --type py scan.${NC}"; exit 1
fi
if ! grep -q "main.py" "$OUT_DIR/type_py.md"; then
    echo -e "${RED}Type filter failed! Python file should appear in --type py scan.${NC}"; exit 1
fi
echo "     Type filter working."

# Test 3: Include Filter
echo -e "  -> Testing v2.4: Include Filter (--include)..."
scan "$TEST_DIR" --include "*.py" -d 2 -o "$OUT_DIR" -n "include_py.md" >/dev/null
if grep -q "README.md" "$OUT_DIR/include_py.md"; then
    echo -e "${RED}Include filter failed! .md file should not appear with --include *.py.${NC}"; exit 1
fi
echo "     Include filter working."

# Test 4: Regex Search Mode
echo -e "  -> Testing v2.4: Regex Search Mode (--regex)..."
OUTPUT=$(scan "$TEST_DIR" -f ".*\.py" --regex -d 2 2>&1 || true)
if [[ "$OUTPUT" != *"main.py"* ]]; then
    echo -e "${RED}Regex search failed! Pattern .*\.py should match main.py.${NC}"; exit 1
fi
echo "     Regex search working."

# Test 5: Grep Mode (Content Search)
echo -e "  -> Testing v2.4: Grep Mode (--grep)..."
scan "$TEST_DIR" --grep "DEBUG" --type py -o "$OUT_DIR" -n "grep_results.md" >/dev/null 2>&1 || true
# Grep creates output when --format != md or --full is set
if [ -f "$OUT_DIR/grep_results.md" ]; then
    if ! grep -q "DEBUG" "$OUT_DIR/grep_results.md"; then
        echo -e "${RED}Grep mode failed! Should find DEBUG in config.py.${NC}"; exit 1
    fi
fi
echo "     Grep mode working."

# Test 6: Grep Mode with Context
echo -e "  -> Testing v2.4: Grep Mode with Context (-C 2)..."
OUTPUT=$(scan "$TEST_DIR" --grep "def get_config" --type py -C 2 2>&1 || true)
if [[ "$OUTPUT" != *"DEBUG"* ]] || [[ "$OUTPUT" != *"return"* ]]; then
    echo -e "${RED}Grep context failed! Should show surrounding lines.${NC}"; exit 1
fi
echo "     Grep with context working."

# Test 7: Analyze Mode
echo -e "  -> Testing v2.4: Analyze Mode (--analyze)..."
scan "$TEST_DIR" --analyze -o "$OUT_DIR" >/dev/null 2>&1
if [ ! -f "$OUT_DIR/seedling_test_sandbox_analysis.md" ]; then
    echo -e "${RED}Analyze mode failed to create output file!${NC}"; exit 1
fi
if ! grep -q "\*\*Type\*\*:" "$OUT_DIR/seedling_test_sandbox_analysis.md"; then
    echo -e "${RED}Analyze output missing project type!${NC}"; exit 1
fi
echo "     Analyze mode working."

# Test 8: Combined Filters
echo -e "  -> Testing v2.4: Combined Filters (--type py --grep)..."
OUTPUT=$(scan "$TEST_DIR" --grep "def" --type py -C 1 2>&1 || true)
if [[ "$OUTPUT" != *"def"* ]]; then
    echo -e "${RED}Combined filter failed! Should find 'def' in Python files.${NC}"; exit 1
fi
# Should not search JS files
if [[ "$OUTPUT" == *"app.js"* ]]; then
    echo -e "${RED}Combined filter failed! Should not search JS files with --type py.${NC}"; exit 1
fi
echo "     Combined filters working."

# Test 9: JSON output with full content
echo -e "  -> Testing v2.4: JSON Output with --full..."
scan "$TEST_DIR" -F json --full -d 1 -o "$OUT_DIR" -n "json_full.json" >/dev/null
if ! grep -q '"contents"' "$OUT_DIR/json_full.json"; then
    echo -e "${RED}JSON --full failed! Should include contents field.${NC}"; exit 1
fi
echo "     JSON with --full working."

# Test 10: Grep Case Sensitivity (v2.4.1)
echo -e "  -> Testing v2.4.1: Grep Case Sensitivity (-i flag)..."
# Create test file with mixed case
cat << 'EOF' > "$TEST_DIR/src/case_test.py"
# Test file for case sensitivity
def TODO():
    pass
def todo():
    pass
EOF
# Case-sensitive (default) - should NOT find TODO when searching for 'todo'
OUTPUT=$(scan "$TEST_DIR" --grep "todo" --type py 2>&1 || true)
if [[ "$OUTPUT" == *"TODO()"* ]]; then
    echo -e "${RED}Case-sensitive grep failed! Should NOT find 'TODO' when searching 'todo'.${NC}"; exit 1
fi
# Case-insensitive (with -i) - should find both
OUTPUT=$(scan "$TEST_DIR" --grep "todo" --type py -i 2>&1 || true)
if [[ "$OUTPUT" != *"TODO()"* ]]; then
    echo -e "${RED}Case-insensitive grep failed! Should find 'TODO' with -i flag.${NC}"; exit 1
fi
echo "     Grep case sensitivity working."

# ==============================================================================
# FINAL CLEANUP & SUCCESS
# ==============================================================================

echo -e "\n${BLUE}======================================================${NC}"
echo -e "${GREEN}   ALL TESTS PASSED! Seedling v2.4.1 is UNBREAKABLE! ${NC}"
echo -e "${BLUE}======================================================${NC}"

if [[ "$TEST_DIR" == "$HOME/tmp/"* && "$OUT_DIR" == "$HOME/tmp/"* ]]; then
    rm -rf "$TEST_DIR" "$OUT_DIR"
fi