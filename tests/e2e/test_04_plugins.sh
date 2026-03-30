#!/bin/bash
# Seedling-tools E2E Tests
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/common.sh"
set -e

cat << 'EOF' > "$TEST_DIR/src/case_test.py"
def TODO(): pass
def todo(): pass
EOF

cat << 'EOF' > "$TEST_DIR/src/config.py"
# Configuration file
DEBUG = True
VERSION = "1.0.0"
def get_config():
    return {"debug": DEBUG}
EOF

echo -e "  -> Testing PLUGIN: Find Mode (Exact & Highlighting)..."
set +e
scan "$TEST_DIR" -f "main" --full -o "$OUT_DIR" -n search_exact.md >/dev/null
set -e
if ! grep -q "MATCHED" "$OUT_DIR/search_exact.md"; then
    echo -e "${RED}Search mode failed to generate highlighted tree.${NC}"
    exit 1
fi

echo -e "  -> Testing PLUGIN: Regex Search Mode (--regex)..."
set +e
OUTPUT=$(scan "$TEST_DIR" -f ".*\.py" --regex -d 2 2>&1)
set -e
if [[ "$OUTPUT" != *"main.py"* ]]; then
    echo -e "${RED}Regex search failed! Pattern .*\.py should match main.py.${NC}"
    exit 1
fi

echo -e "  -> Testing PLUGIN: Grep Mode & Context & Case (-C 2, -i)..."
set +e
scan "$TEST_DIR" --grep "DEBUG" --type py -o "$OUT_DIR" -n "grep_results.md" >/dev/null 2>&1
CTX_OUT=$(scan "$TEST_DIR" --grep "def get_config" --type py -C 2 2>&1)
CASE_OUT1=$(scan "$TEST_DIR" --grep "todo" --type py 2>&1)
CASE_OUT2=$(scan "$TEST_DIR" --grep "todo" --type py -i 2>&1)
set -e

if ! grep -q "DEBUG" "$OUT_DIR/grep_results.md" || [[ "$CTX_OUT" != *"DEBUG"* ]]; then
    echo -e "${RED}Grep mode or context matching failed!${NC}"
    exit 1
fi
if [[ "$CASE_OUT1" == *"TODO()"* ]] || [[ "$CASE_OUT2" != *"TODO()"* ]]; then
    echo -e "${RED}Case sensitivity (-i) logic failed!${NC}"
    exit 1
fi

echo -e "  -> Testing PLUGIN: Analyze Mode (--analyze)..."
set +e
scan "$TEST_DIR" --analyze -o "$OUT_DIR" >/dev/null 2>&1
set -e
if ! grep -q "\*\*Type\*\*:" "$OUT_DIR/seedling_test_sandbox_analysis.md"; then
    echo -e "${RED}Analyze output missing project metadata!${NC}"
    exit 1
fi

echo -e "  -> Testing PLUGIN: AST Code Skeleton Extraction (--skeleton)..."
set +e
python3 -c "import ast; hasattr(ast, 'unparse') or exit(1)" 2>/dev/null
PYTHON_CHECK=$?
set -e
if [ $PYTHON_CHECK -eq 0 ]; then
    cat << 'EOF' > "$TEST_DIR/src/ast_complex.py"
class DataModel:
    """This is the core data model."""
    def compute(self):
        print("Complex logic here")
        return 42
EOF
    set +e
    scan "$TEST_DIR" --skeleton -o "$OUT_DIR" -n "skeleton.md" >/dev/null
    set -e
    if ! grep -q "class DataModel:" "$OUT_DIR/skeleton.md" || grep -q "Complex logic" "$OUT_DIR/skeleton.md"; then
        echo -e "${RED}Skeleton extraction failed (either lost class or kept implementation).${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}     Skipping AST test: Python < 3.9.${NC}"
fi