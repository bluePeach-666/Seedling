#!/bin/bash

# ==============================================================================
# 🌲 Seedling Ultimate Automated Test Suite
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
# 1. Test Environment Setup
# ==========================================
TEST_DIR="seedling_test_sandbox"
OUT_DIR="${TEST_DIR}_out"

echo -e "\n${GREEN}[1/13] Setting up COMPLEX dummy project environment...${NC}"

# [Security] Prevent accidental deletion of root/home if variables are empty
rm -rf "${TEST_DIR:?Variable not set or empty}" "${OUT_DIR:?Variable not set or empty}"
mkdir -p "$TEST_DIR/src/nested/deep" "$TEST_DIR/node_modules" "$TEST_DIR/.hidden" "$OUT_DIR"
mkdir -p "$TEST_DIR/delete_me_folder"

# Standard Text Data
echo "print('Hello World')" > "$TEST_DIR/src/main.py"
echo "def add(a, b): return a + b" > "$TEST_DIR/src/nested/utils.py"
echo "# My Awesome App" > "$TEST_DIR/README.md"
echo "Heavy JS garbage" > "$TEST_DIR/node_modules/junk.js"
echo "Secret API Key: 12345" > "$TEST_DIR/.hidden/secret.key"
echo "id,name,role" > "$TEST_DIR/data.csv"
echo "fake_binary_image_data" > "$TEST_DIR/image.png"
echo "fake_executable_data" > "$TEST_DIR/app.exe"
echo "I am doomed" > "$TEST_DIR/delete_me_file.txt"

# Edge Case Data (Binary, Encoding, Malicious Blueprints)
printf "Fake_Text\x00Binary_Garbage" > "$TEST_DIR/sneaky_binary.txt"
python3 -c "open('$TEST_DIR/gbk_legacy.txt', 'w', encoding='gbk').write('你好世界：GBK测试')"

cat << 'EOF' > "$TEST_DIR/malicious.md"
# 恶意蓝图
```text
root/
├── normal.txt
└── ../../../escaped.txt

```

### FILE: ../../../escaped.txt

```text
You are hacked!

```

EOF

cat << 'EOF' > "$TEST_DIR/windows_paths.md"

```text
root/
└── src/
    └── win.py

```

### FILE: src\win.py

```python
print("Windows paths rock!")

```

EOF

# ==========================================

# 2. Basic Scan & Slashes

# ==========================================

echo -e "\n${GREEN}[2/13] Testing Basic Scans & Directory Trailing Slashes (/)...${NC}"
scan "$TEST_DIR" -F txt -o "$OUT_DIR" -n basic_scan.txt >/dev/null
scan "$TEST_DIR" -F md -o "$OUT_DIR" -n basic_scan.md >/dev/null

if [ ! -f "$OUT_DIR/basic_scan.txt" ] || [ ! -f "$OUT_DIR/basic_scan.md" ]; then
echo -e "${RED}❌ Basic scan failed to create files.${NC}"; exit 1
fi
if ! grep -q "src/" "$OUT_DIR/basic_scan.txt"; then
echo -e "${RED}❌ Trailing slash feature failed! Could not find 'src/' in output.${NC}"; exit 1
fi

# ==========================================

# 3. Exclusions & Hidden

# ==========================================

echo -e "\n${GREEN}[3/13] Testing Exclusion (-e) & Hidden (--show) flags...${NC}"
scan "$TEST_DIR" --show -e node_modules -o "$OUT_DIR" -n clean_scan.md >/dev/null
if grep -q "junk.js" "$OUT_DIR/clean_scan.md"; then
echo -e "${RED}❌ Exclude flag failed! Found node_modules content.${NC}"; exit 1
fi
if ! grep -q "secret.key" "$OUT_DIR/clean_scan.md"; then
echo -e "${RED}❌ Show hidden flag failed! Could not find .hidden content.${NC}"; exit 1
fi

# ==========================================

# 4. Text-Only & CSV Support

# ==========================================

echo -e "\n${GREEN}[4/13] Testing Text-Only Filter (--text) & CSV Support...${NC}"
scan "$TEST_DIR" --text -o "$OUT_DIR" -n text_only.md >/dev/null
if grep -q "image.png" "$OUT_DIR/text_only.md" || grep -q "app.exe" "$OUT_DIR/text_only.md"; then
echo -e "${RED}❌ Text-Only flag failed! Binary files (png/exe) leaked into the tree.${NC}"; exit 1
fi
if ! grep -q "data.csv" "$OUT_DIR/text_only.md"; then
echo -e "${RED}❌ CSV Support failed! data.csv was incorrectly filtered out.${NC}"; exit 1
fi

# ==========================================

# 5. Power Mode / Full Context

# ==========================================

echo -e "\n${GREEN}[5/13] Testing POWER MODE (--full) context aggregation...${NC}"
scan "$TEST_DIR" --full -e node_modules -o "$OUT_DIR" -n snapshot.md >/dev/null
if ! grep -q "def add(a, b)" "$OUT_DIR/snapshot.md"; then
echo -e "${RED}❌ Power mode failed to extract source code!${NC}"; exit 1
fi

# ==========================================

# 6. Find Mode

# ==========================================

echo -e "\n${GREEN}[6/13] Testing Find Mode (Exact & Fuzzy & Highlighting)...${NC}"
scan "$TEST_DIR" -f "main" -o "$OUT_DIR" -n search_exact.md >/dev/null
scan "$TEST_DIR" -f "util" -o "$OUT_DIR" -n search_fuzzy.md >/dev/null
if ! grep -q "MATCHED" "$OUT_DIR/search_exact.md"; then
echo -e "${RED}❌ Search mode failed to generate highlighted 🎯 tree.${NC}"; exit 1
fi

# ==========================================

# 7. Search & Delete (Security Intercept)

# ==========================================

echo -e "\n${YELLOW}[7/13] Testing SECURITY: Dangerous Deletion (--delete) TTY Interception...${NC}"

# Since v2.3.0, piping into --delete will trigger the isatty() security block. We test if it properly blocks it.

OUTPUT=$(echo "CONFIRM DELETE" | scan "$TEST_DIR" -f "delete_me" --delete 2>&1 || true)
if [[ ! "$OUTPUT" == *"interactive terminal"* ]]; then
echo -e "${RED}❌ Security Bypass! TTY check failed. The program allowed piped deletion.${NC}"; exit 1
fi
echo -e "${GREEN}   ✅ TTY Security check successfully blocked automated deletion.${NC}"

# ==========================================

# 8. Direct Build

# ==========================================

echo -e "\n${GREEN}[8/13] Testing Build - Direct Mode (-d)...${NC}"
build -d "$OUT_DIR/direct_folder" >/dev/null
build -d "$OUT_DIR/direct_file.txt" >/dev/null
if [ ! -d "$OUT_DIR/direct_folder" ] || [ ! -f "$OUT_DIR/direct_file.txt" ]; then
echo -e "${RED}❌ Build direct mode failed to create files/folders.${NC}"; exit 1
fi

# ==========================================

# 9. Context Rehydration (Reverse Scaffolding)

# ==========================================

echo -e "\n${GREEN}[9/13] Testing EPISODIC MAGIC: Context Rehydration...${NC}"
build "$OUT_DIR/snapshot.md" "$OUT_DIR/restored_project" --force >/dev/null

if [ ! -f "$OUT_DIR/restored_project/src/main.py" ]; then
echo -e "${RED}❌ Rehydration failed to build directory structure.${NC}"; exit 1
fi
if ! grep -q "Hello World" "$OUT_DIR/restored_project/src/main.py"; then
echo -e "${RED}❌ Rehydration failed to inject source code back into files!${NC}"; exit 1
fi

# ==========================================

# 10. Path Traversal Security Test

# ==========================================

echo -e "\n${YELLOW}[10/13] Testing SECURITY: Path Traversal Interception...${NC}"
build "$TEST_DIR/malicious.md" "$OUT_DIR/safe_build" --force >/dev/null 2>&1 || true
if [ -f "$OUT_DIR/escaped.txt" ] || [ -f "escaped.txt" ]; then
echo -e "${RED}❌ CRITICAL: Security Bypass! Path traversal succeeded and created files outside sandbox.${NC}"; exit 1
fi

# ==========================================

# 11. Heuristic Binary & GBK Encoding Test

# ==========================================

echo -e "\n${GREEN}[11/13] Testing ENGINE: Heuristic Binary Check & Encode Fallback...${NC}"
scan "$TEST_DIR" --full -o "$OUT_DIR" -n "encoding_test.md" >/dev/null 2>&1
if grep -q "### FILE: sneaky_binary.txt" "$OUT_DIR/encoding_test.md"; then
echo -e "${RED}❌ Heuristic engine failed! NUL-byte binary file was read as text.${NC}"; exit 1
fi
if ! grep -q "你好世界：GBK测试" "$OUT_DIR/encoding_test.md"; then
echo -e "${RED}❌ Encoding fallback failed! GBK file was corrupted or skipped.${NC}"; exit 1
fi

# ==========================================

# 12. Windows Path Compatibility Test

# ==========================================

echo -e "\n${GREEN}[12/13] Testing COMPATIBILITY: Windows Path Separators...${NC}"
build "$TEST_DIR/windows_paths.md" "$OUT_DIR/win_build" --force >/dev/null
if ! grep -q "Windows paths rock!" "$OUT_DIR/win_build/src/win.py"; then
echo -e "${RED}❌ Windows path rehydration failed! Code was not matched to the key.${NC}"; exit 1
fi

# ==========================================

# 13. Quiet Mode API Support Test

# ==========================================

echo -e "\n${GREEN}[13/13] Testing ENGINE: Quiet Mode API (-q)...${NC}"

# Runs the scan in quiet mode. It should output absolutely nothing to stdout/stderr.

QUIET_OUT=$(scan "$TEST_DIR" -q -o "$OUT_DIR" -n "quiet.md" 2>&1)
if [ -n "$QUIET_OUT" ]; then
echo -e "${RED}❌ Quiet Mode failed! Output was not entirely suppressed: $QUIET_OUT${NC}"; exit 1
fi

echo -e "\n${BLUE}======================================================${NC}"
echo -e "${GREEN}   🏆 ALL 13 ULTIMATE TESTS PASSED! Seedling is UNBREAKABLE! ${NC}"
echo -e "${BLUE}======================================================${NC}"

# Final Safety Cleanup

rm -rf "${TEST_DIR:?}" "${OUT_DIR:?}"