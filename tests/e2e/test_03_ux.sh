#!/bin/bash
# Seedling-tools E2E Tests
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/common.sh"
set -e

CONFIG_HOME="$HOME/seedling_ux_home"
rm -rf "$CONFIG_HOME"
mkdir -p "$CONFIG_HOME"
export HOME="$CONFIG_HOME"
export USERPROFILE="$CONFIG_HOME"
export TEST_DIR="$HOME/tmp/seedling_test_sandbox"
export OUT_DIR="$HOME/tmp/seedling_test_out"

setup_sandbox

echo -e "  -> Testing UX: Smart Garbage Interception (v2.5.1 New Feature)..."
set +e
OUTPUT=$(scan "$TEST_DIR" < /dev/null 2>&1)
set -e
if [[ "$OUTPUT" != *"Project clutter detected"* ]] || [[ "$OUTPUT" != *"node_modules"* ]]; then
    echo -e "${RED}Garbage interception failed to warn about node_modules!${NC}"
    exit 1
fi

echo -e "  -> Testing UX: Hidden Files Visibility (--nohidden)..."
set +e
scan "$TEST_DIR" -o "$OUT_DIR" -n "hidden_default.md" >/dev/null 2>&1
scan "$TEST_DIR" --nohidden -o "$OUT_DIR" -n "nohidden_flag.md" >/dev/null 2>&1
set -e
if ! grep -q ".hidden" "$OUT_DIR/hidden_default.md"; then
    echo -e "${RED}Hidden files should be visible by default!${NC}"
    exit 1
fi
if grep -q ".hidden" "$OUT_DIR/nohidden_flag.md"; then
    echo -e "${RED}--nohidden flag failed to hide '.hidden' dir!${NC}"
    exit 1
fi

echo -e "  -> Testing UX: Smart Exclude Fuzzy Matching (Typo correction)..."
echo "*.tmp" > "$TEST_DIR/.gitignore"
set +e
OUTPUT=$(scan "$TEST_DIR" -e "./gitignore" < /dev/null 2>&1)
set -e
if [[ "$OUTPUT" != *"Could not find './gitignore'"* ]] && [[ "$OUTPUT" != *"found '.gitignore'"* ]]; then
    echo -e "${RED}Fuzzy matching prompt failed!${NC}"
    exit 1
fi

echo -e "  -> Testing UX: File Type & Include Filter..."
set +e
scan "$TEST_DIR" --type py -d 2 -o "$OUT_DIR" -n "type_py.md" >/dev/null
scan "$TEST_DIR" --include "*.py" -d 2 -o "$OUT_DIR" -n "include_py.md" >/dev/null
set -e
if grep -q "README.md" "$OUT_DIR/type_py.md" || grep -q "README.md" "$OUT_DIR/include_py.md"; then
    echo -e "${RED}Filters leaked non-matching files!${NC}"
    exit 1
fi

echo -e "  -> Testing UX: Flag Conflict Intercept (--full vs --skeleton)..."
set +e
CONFLICT_OUTPUT=$(scan "$TEST_DIR" --full --skeleton 2>&1)
set -e
if ! echo "$CONFLICT_OUTPUT" | grep -Eiq "conflicting|not allowed|cannot be used together"; then
    echo -e "${RED}UX Failure: Should have blocked simultaneous --full and --skeleton flags.${NC}"
    exit 1
fi

echo -e "  -> Testing UX: Quiet Mode (-q)..."
set +e
OUTPUT=$(scan "$TEST_DIR" -q -o "$OUT_DIR" -n "quiet_test.md" 2>&1)
set -e
if [[ -n "$OUTPUT" ]]; then
    echo -e "${RED}Quiet mode failed! Expected no stdout.${NC}"
    exit 1
fi

echo -e "  -> Testing UX: Strip Comments Scan Mode..."
cat << 'EOF' > "$TEST_DIR/comment_sample.py"
"""module doc"""
value = '# keep'
# remove line
EOF
cat << EOF > "$TEST_DIR/.seedling.json"
{"scan":{"strip_comments":true}}
EOF
set +e
scan "$TEST_DIR" --full -o "$OUT_DIR" -n "strip_comments.md" >/dev/null 2>&1
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Scan --strip-comments failed.${NC}"
    exit 1
fi
if grep -q "module doc" "$OUT_DIR/strip_comments.md" || grep -q "^# remove line$" "$OUT_DIR/strip_comments.md"; then
    echo -e "${RED}Strip comments mode failed to remove Python comments/docstrings.${NC}"
    exit 1
fi
if ! grep -q "# keep" "$OUT_DIR/strip_comments.md"; then
    echo -e "${RED}Strip comments mode removed string literals unexpectedly.${NC}"
    exit 1
fi

echo -e "  -> Testing UX: Root strip-comments Command..."
set +e
OUTPUT=$(seedling strip-comments "$TEST_DIR/comment_sample.py" --check 2>&1)
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}seedling strip-comments --check failed.${NC}"
    exit 1
fi
if [[ "$OUTPUT" != *"saved_tokens"* ]]; then
    echo -e "${RED}strip-comments check did not report token savings.${NC}"
    exit 1
fi
