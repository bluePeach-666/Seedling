#!/bin/bash
# Seedling-tools E2E Tests
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/common.sh"
set -e

echo -e "  -> Testing ENGINE: Build Engine Blueprint Reconstruction..."
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
set +e
build "$TEST_DIR/valid_blueprint.md" "$OUT_DIR/valid_build" >/dev/null 2>&1
set -e
if [ ! -d "$OUT_DIR/valid_build/folderB" ] || ! grep -q "Hello Build!" "$OUT_DIR/valid_build/fileA.txt"; then
    echo -e "${RED}Build engine failed to reconstruct directory or file!${NC}"
    exit 1
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
```text
I am nested and should not break the parser!
```
"""
````
EOF
set +e
build "$TEST_DIR/complex_fence_blueprint.md" "$OUT_DIR/smart_build" >/dev/null 2>&1
set -e
if [ -f "$OUT_DIR/smart_build/__init__.py" ] || ! grep -q "I am nested" "$OUT_DIR/smart_build/tests/__init__.py"; then
    echo -e "${RED}Smart path recognition or complex fence parsing failed!${NC}"
    exit 1
fi

echo -e "  -> Testing ENGINE: Visual Tree Noise Sanitization..."
cat << 'EOF' > "$TEST_DIR/glyph_noise_blueprint.md"
```text
root/
├── src/
│
│   ├── │literal.txt
│   └── normal.txt
│
└── glyph│name.txt
```
### FILE: src/│literal.txt
```text
leading glyph kept
```
### FILE: glyph│name.txt
```text
embedded glyph kept
```
EOF
set +e
build "$TEST_DIR/glyph_noise_blueprint.md" "$OUT_DIR/glyph_noise_build" >/dev/null 2>&1
set -e
if [ -e "$OUT_DIR/glyph_noise_build/│" ] || [ -e "$OUT_DIR/glyph_noise_build/src/│" ]; then
    echo -e "${RED}Visual connector noise was materialized as a filesystem node.${NC}"
    exit 1
fi
if [ ! -f "$OUT_DIR/glyph_noise_build/src/│literal.txt" ] || [ ! -f "$OUT_DIR/glyph_noise_build/glyph│name.txt" ]; then
    echo -e "${RED}Valid glyph-bearing filenames were not reconstructed.${NC}"
    exit 1
fi
if ! grep -q "leading glyph kept" "$OUT_DIR/glyph_noise_build/src/│literal.txt"; then
    echo -e "${RED}Glyph-leading file content was not aligned.${NC}"
    exit 1
fi
if ! grep -q "embedded glyph kept" "$OUT_DIR/glyph_noise_build/glyph│name.txt"; then
    echo -e "${RED}Embedded glyph file content was not aligned.${NC}"
    exit 1
fi

echo -e "  -> Testing ENGINE: Direct Creation Flag (-d)..."
set +e
build -d "$OUT_DIR/direct_create_file.py" >/dev/null 2>&1
set -e
if [ ! -f "$OUT_DIR/direct_create_file.py" ]; then
    echo -e "${RED}Direct creation flag (-d) failed to create file!${NC}"
    exit 1
fi

echo -e "  -> Testing ENGINE: Binary Detection & Broken Symlink Resilience..."
set +e
scan "$TEST_DIR" --full -o "$OUT_DIR" -n "binary_symlink_test.md" >/dev/null 2>&1
set -e
if [ ! -f "$OUT_DIR/binary_symlink_test.md" ] || grep -q "IHDR" "$OUT_DIR/binary_symlink_test.md"; then
    echo -e "${RED}Binary leaked into text report OR crash on symlink!${NC}"
    exit 1
fi

echo -e "  -> Testing ENGINE: Token Estimation Engine..."
set +e
scan "$TEST_DIR" -F txt -o "$OUT_DIR" -n "token_test.txt" >/dev/null
set -e
if ! grep -q "tokens" "$OUT_DIR/token_test.txt"; then
    echo -e "${RED}Token estimation failed!${NC}"
    exit 1
fi

echo -e "  -> Testing ENGINE: Remote Repository Instant Scanning..."
set +e
OUTPUT=$(scan "https://127.0.0.1:9999/invalid_repo.git" 2>&1)
set -e
if [[ "$OUTPUT" != *"Cloning remote repository"* ]] && [[ "$OUTPUT" != *"Git clone operation failed"* ]]; then
    echo -e "${RED}Remote repository routing failed!${NC}"
    exit 1
fi

echo -e "  -> Testing ENGINE: Build Engine Dry Run Mode (--check)..."
cat << 'EOF' > "$TEST_DIR/check_blueprint.md"
```text
root/
└── new_file.txt
```
### FILE: new_file.txt
```text
I should not exist physically!
```
EOF
set +e
OUTPUT=$(build "$TEST_DIR/check_blueprint.md" "$OUT_DIR/check_build" --check < /dev/null 2>&1)
set -e

if [ -f "$OUT_DIR/check_build/new_file.txt" ]; then
    echo -e "${RED}Dry run (--check) failed! It actually created the physical file.${NC}"
    exit 1
fi
if [[ "$OUTPUT" != *"[CHECK MODE]"* ]] || [[ "$OUTPUT" != *"missing."* ]]; then
    echo -e "${RED}Dry run (--check) output missing expected logs.${NC}"
    exit 1
fi