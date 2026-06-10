#!/bin/bash
# Seedling-tools E2E Tests
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/common.sh"
CLEAN_BIN="${CLEAN_BIN:-clean}"

setup_sandbox

echo -e "  -> Testing CLEAN: Dry Run Preserves Cache Artifacts..."
mkdir -p "$TEST_DIR/src/__pycache__" "$TEST_DIR/.pytest_cache" "$TEST_DIR/dist" "$TEST_DIR/sample.egg-info"
echo "cache" > "$TEST_DIR/src/__pycache__/main.cpython-312.pyc"
echo "cache" > "$TEST_DIR/.pytest_cache/CACHEDIR.TAG"
echo "wheel" > "$TEST_DIR/dist/package.whl"
echo "metadata" > "$TEST_DIR/sample.egg-info/PKG-INFO"
echo "compiled" > "$TEST_DIR/src/loose.pyc"
echo "coverage" > "$TEST_DIR/.coverage"

set +e
OUTPUT=$("$CLEAN_BIN" "$TEST_DIR" --dry-run 2>&1)
set -e
if [[ "$OUTPUT" != *"DRY-RUN"* ]]; then
    echo -e "${RED}Clean dry-run did not report dry-run mode.${NC}"
    exit 1
fi
if [ ! -d "$TEST_DIR/src/__pycache__" ] || [ ! -d "$TEST_DIR/dist" ] || [ ! -f "$TEST_DIR/src/loose.pyc" ]; then
    echo -e "${RED}Clean dry-run removed files from disk.${NC}"
    exit 1
fi

echo -e "  -> Testing CLEAN: Non-Interactive Cache Removal..."
set +e
"$CLEAN_BIN" "$TEST_DIR" >/dev/null 2>&1
set -e
if [ -d "$TEST_DIR/src/__pycache__" ] || [ -d "$TEST_DIR/.pytest_cache" ] || [ -d "$TEST_DIR/dist" ] || [ -d "$TEST_DIR/build" ]; then
    echo -e "${RED}Clean command failed to remove generated cache/build artifacts.${NC}"
    exit 1
fi
if [ -d "$TEST_DIR/sample.egg-info" ] || [ -f "$TEST_DIR/src/loose.pyc" ] || [ -f "$TEST_DIR/.coverage" ]; then
    echo -e "${RED}Clean command failed to remove Python packaging/cache files.${NC}"
    exit 1
fi
if [ ! -f "$TEST_DIR/src/main.py" ] || [ ! -f "$TEST_DIR/README.md" ] || [ ! -d "$TEST_DIR/src/build" ]; then
    echo -e "${RED}Clean command removed ordinary source files or nested build directories.${NC}"
    exit 1
fi

echo -e "  -> Testing CLEAN: Ignored Directories Are Preserved..."
mkdir -p "$TEST_DIR/node_modules/pkg/__pycache__"
echo "ignored" > "$TEST_DIR/node_modules/pkg/__pycache__/ignored.pyc"
set +e
"$CLEAN_BIN" "$TEST_DIR" >/dev/null 2>&1
set -e
if [ ! -f "$TEST_DIR/node_modules/pkg/__pycache__/ignored.pyc" ]; then
    echo -e "${RED}Clean command traversed an ignored dependency directory.${NC}"
    exit 1
fi
