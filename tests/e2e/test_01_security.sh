#!/bin/bash
# Seedling-tools E2E Tests
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/common.sh"
set -e

echo -e "  -> Testing SECURITY: Dangerous Deletion TTY Interception..."
set +e
OUTPUT=$(echo "CONFIRM DELETE" | scan "$TEST_DIR" -f "none" --delete 2>&1)
set -e
if [[ "$OUTPUT" != *"interactive terminal"* ]]; then
    echo -e "${RED}Security Bypass! TTY check failed.${NC}"
    exit 1
fi

echo -e "  -> Testing SECURITY: Path Traversal Interception..."
cat << 'EOF' > "$TEST_DIR/malicious.md"
# 恶意蓝图
```text
root/
└── ../../../escaped.txt
```
EOF
set +e
build "$TEST_DIR/malicious.md" "$OUT_DIR/safe_build" --force >/dev/null 2>&1
set -e
if [ -f "$OUT_DIR/escaped.txt" ] || [ -f "escaped.txt" ]; then
    echo -e "${RED}CRITICAL: Security Bypass! Path traversal succeeded.${NC}"
    exit 1
fi

echo -e "  -> Testing SECURITY: Image Memory Bomb Limit..."
mkdir -p "$TEST_DIR/huge_dir"
seq 1 1505 | xargs -I {} touch "$TEST_DIR/huge_dir/file_{}.txt"
set +e
OUTPUT=$(scan "$TEST_DIR/huge_dir" -F image -o "$OUT_DIR" -n "huge.png" 2>&1)
set -e

if [[ "$OUTPUT" == *"'Pillow' is required"* ]]; then
    echo -e "${YELLOW}     Skipping Image memory bomb check: Pillow not installed.${NC}"
else
    if [[ "$OUTPUT" != *"memory overflow"* ]]; then
        echo -e "${RED}Image memory bomb check failed! Output was: $OUTPUT${NC}"
        exit 1
    fi
fi