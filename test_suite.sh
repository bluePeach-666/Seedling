#!/bin/bash

# ==============================================================================
# 🌲 Seedling Ultimate Automated Test Suite (v2.2.0)
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   🚀 Starting Seedling ULTIMATE E2E Test Suite... ${NC}"
echo -e "${BLUE}======================================================${NC}"

# ==========================================
# Test Environment Setup
# ==========================================
TEST_DIR="seedling_test_sandbox"
OUT_DIR="${TEST_DIR}_out"

echo -e "\n${GREEN}[1/9] Setting up COMPLEX dummy project environment...${NC}"
rm -rf $TEST_DIR $OUT_DIR
mkdir -p $TEST_DIR/src/nested/deep $TEST_DIR/node_modules $TEST_DIR/.hidden $OUT_DIR
mkdir -p $TEST_DIR/delete_me_folder

# 标准文本
echo "print('Hello World')" > $TEST_DIR/src/main.py
echo "def add(a, b): return a + b" > $TEST_DIR/src/nested/utils.py
echo "# My Awesome App" > $TEST_DIR/README.md
echo "Heavy JS garbage" > $TEST_DIR/node_modules/junk.js
echo "Secret API Key: 12345" > $TEST_DIR/.hidden/secret.key
echo "id,name,role" > $TEST_DIR/data.csv
echo "fake_binary_image_data" > $TEST_DIR/image.png
echo "fake_executable_data" > $TEST_DIR/app.exe
echo "I am doomed" > $TEST_DIR/delete_me_file.txt

# 2. Basic Scan & Slashes
echo -e "\n${GREEN}[2/9] Testing Basic Scans & Directory Trailing Slashes (/)...${NC}"
scan $TEST_DIR -F txt -o $OUT_DIR -n basic_scan.txt
scan $TEST_DIR -F md -o $OUT_DIR -n basic_scan.md

if [ ! -f "$OUT_DIR/basic_scan.txt" ] || [ ! -f "$OUT_DIR/basic_scan.md" ]; then
    echo -e "${RED}❌ Basic scan failed to create files.${NC}"; exit 1
fi
if ! grep -q "src/" "$OUT_DIR/basic_scan.txt"; then
    echo -e "${RED}❌ Trailing slash feature failed! Could not find 'src/' in output.${NC}"; exit 1
fi

# 3. Exclusions & Hidden
echo -e "\n${GREEN}[3/9] Testing Exclusion (-e) & Hidden (--show) flags...${NC}"
scan $TEST_DIR --show -e node_modules -o $OUT_DIR -n clean_scan.md
if grep -q "junk.js" "$OUT_DIR/clean_scan.md"; then
    echo -e "${RED}❌ Exclude flag failed! Found node_modules content.${NC}"; exit 1
fi
if ! grep -q "secret.key" "$OUT_DIR/clean_scan.md"; then
    echo -e "${RED}❌ Show hidden flag failed! Could not find .hidden content.${NC}"; exit 1
fi

# 4. Text-Only & CSV Support
echo -e "\n${GREEN}[4/9] Testing Text-Only Filter (--text) & CSV Support...${NC}"
scan $TEST_DIR --text -o $OUT_DIR -n text_only.md
if grep -q "image.png" "$OUT_DIR/text_only.md" || grep -q "app.exe" "$OUT_DIR/text_only.md"; then
    echo -e "${RED}❌ Text-Only flag failed! Binary files (png/exe) leaked into the tree.${NC}"; exit 1
fi
if ! grep -q "data.csv" "$OUT_DIR/text_only.md"; then
    echo -e "${RED}❌ CSV Support failed! data.csv was incorrectly filtered out.${NC}"; exit 1
fi

# 5. Power Mode / Full Context
echo -e "\n${GREEN}[5/9] Testing POWER MODE (--full) context aggregation...${NC}"
scan $TEST_DIR --full -e node_modules -o $OUT_DIR -n snapshot.md
if ! grep -q "def add(a, b)" "$OUT_DIR/snapshot.md"; then
    echo -e "${RED}❌ Power mode failed to extract source code!${NC}"; exit 1
fi

# 6. Find Mode
echo -e "\n${GREEN}[6/9] Testing Find Mode (Exact & Fuzzy & Highlighting)...${NC}"
scan $TEST_DIR -f "main" -o $OUT_DIR -n search_exact.md
scan $TEST_DIR -f "util" -o $OUT_DIR -n search_fuzzy.md
if ! grep -q "MATCHED" "$OUT_DIR/search_exact.md"; then
    echo -e "${RED}❌ Search mode failed to generate highlighted 🎯 tree.${NC}"; exit 1
fi

# 7. Search & Delete (DANGEROUS)
echo -e "\n${YELLOW}[7/9] Testing Dangerous Deletion (--delete) with Safety Prompt bypass...${NC}"
echo "y" | scan $TEST_DIR -f "delete_me" --delete
if [ -f "$TEST_DIR/delete_me_file.txt" ] || [ -d "$TEST_DIR/delete_me_folder" ]; then
    echo -e "${RED}❌ Dangerous deletion failed! Target files/folders still exist.${NC}"; exit 1
fi

# 8. Direct Build
echo -e "\n${GREEN}[8/9] Testing Build - Direct Mode (-d)...${NC}"
build -d $OUT_DIR/direct_folder
build -d $OUT_DIR/direct_file.txt
if [ ! -d "$OUT_DIR/direct_folder" ] || [ ! -f "$OUT_DIR/direct_file.txt" ]; then
    echo -e "${RED}❌ Build direct mode failed to create files/folders.${NC}"; exit 1
fi

# 9. Context Rehydration (Reverse Scaffolding)
echo -e "\n${GREEN}[9/9] Testing EPISODIC MAGIC: Context Rehydration...${NC}"
build $OUT_DIR/snapshot.md $OUT_DIR/restored_project --force

if [ ! -f "$OUT_DIR/restored_project/src/main.py" ]; then
    echo -e "${RED}❌ Rehydration failed to build directory structure.${NC}"; exit 1
fi
if ! grep -q "Hello World" "$OUT_DIR/restored_project/src/main.py"; then
    echo -e "${RED}❌ Rehydration failed to inject source code back into files!${NC}"; exit 1
fi

echo -e "\n${BLUE}======================================================${NC}"
echo -e "${GREEN}  🏆 ALL 9 ULTIMATE TESTS PASSED! Seedling is UNBREAKABLE! ${NC}"
echo -e "${BLUE}======================================================${NC}"

# Clean up
rm -rf $TEST_DIR $OUT_DIR