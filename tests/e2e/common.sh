#!/bin/bash
# Seedling-tools E2E Tests Common Utilities
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

export GREEN='\033[0;32m'
export BLUE='\033[0;34m'
export RED='\033[0;31m'
export YELLOW='\033[0;33m'
export NC='\033[0m'

export PATH="$HOME/.local/bin:$USERPROFILE/.local/bin:$PATH"
export TEST_DIR="$HOME/tmp/seedling_test_sandbox"
export OUT_DIR="$HOME/tmp/seedling_test_out"

setup_sandbox() {
    if [[ "$TEST_DIR" != "$HOME/tmp/"* ]] || [[ "$OUT_DIR" != "$HOME/tmp/"* ]]; then
        echo -e "${RED}CRITICAL: Invalid test directory path detected!${NC}"
        exit 1
    fi

    rm -rf "$TEST_DIR" "$OUT_DIR"
    mkdir -p "$TEST_DIR/src/nested/deep" "$TEST_DIR/node_modules" "$TEST_DIR/.hidden" "$OUT_DIR" "$TEST_DIR/build/logs" "$TEST_DIR/src/build"

    echo "print('Hello World')" > "$TEST_DIR/src/main.py"
    echo "def add(a, b): return a + b" > "$TEST_DIR/src/nested/utils.py"
    echo "# My Awesome App" > "$TEST_DIR/README.md"
    echo "fake_binary" > "$TEST_DIR/image.png"
    printf "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" > "$TEST_DIR/real_binary.png"
    
    set +e
    ln -s "$TEST_DIR/nowhere.txt" "$TEST_DIR/broken_link.txt" 2>/dev/null
    set -e
}

cleanup_sandbox() {
    if [[ "$TEST_DIR" == "$HOME/tmp/"* ]] && [[ "$OUT_DIR" == "$HOME/tmp/"* ]]; then
        rm -rf "$TEST_DIR" "$OUT_DIR"
        rm -f seedling_test_sandbox*.{md,txt,json,png,xml} 2>/dev/null
        echo -e "${BLUE}   Cleaned up all temporary files and test artifacts. ${NC}"
    fi
}