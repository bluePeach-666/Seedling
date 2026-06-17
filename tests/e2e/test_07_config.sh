#!/bin/bash
# Seedling-tools E2E Tests
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/common.sh"
set -e

setup_sandbox

CONFIG_HOME="$HOME/seedling_config_home"
rm -rf "$CONFIG_HOME"
mkdir -p "$CONFIG_HOME"
export HOME="$CONFIG_HOME"
export USERPROFILE="$CONFIG_HOME"

echo -e "  -> Testing CONFIG: First Run Global Config Initialization..."
set +e
scan "$TEST_DIR" -q -o "$OUT_DIR" -n "config_init.md" >/dev/null 2>&1
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Config initialization scan failed.${NC}"
    exit 1
fi
if [ ! -f "$HOME/.seedling/config.json" ]; then
    echo -e "${RED}Global config file was not created on first run.${NC}"
    exit 1
fi

echo -e "  -> Testing CONFIG: Local Scan Override..."
cat << 'EOF' > "$TEST_DIR/.seedling.json"
{"scan":{"show_hidden":false}}
EOF
set +e
( cd "$TEST_DIR" && scan . -q -o "$OUT_DIR" -n "config_local.md" >/dev/null 2>&1 )
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Local config override scan failed.${NC}"
    exit 1
fi
if grep -q ".hidden" "$OUT_DIR/config_local.md"; then
    echo -e "${RED}Local config did not hide hidden paths.${NC}"
    exit 1
fi

echo -e "  -> Testing CONFIG: Corrupt Local Config Fails Safely..."
echo "{bad json" > "$TEST_DIR/.seedling.json"
set +e
OUTPUT=$( cd "$TEST_DIR" && scan . -q -o "$OUT_DIR" -n "config_corrupt.md" 2>&1 )
STATUS=$?
set -e
if [ $STATUS -eq 0 ]; then
    echo -e "${RED}Corrupt local config should have failed.${NC}"
    exit 1
fi
if [[ "$OUTPUT" != *"ConfigurationCorruptionError"* ]] && [[ "$OUTPUT" != *"Malformed Seedling configuration"* ]]; then
    echo -e "${RED}Corrupt config error output was not specific enough.${NC}"
    exit 1
fi

echo -e "  -> Testing CONFIG: Build Default Target Applies From Global Config..."
rm -f "$TEST_DIR/.seedling.json"
cat << EOF > "$HOME/.seedling/config.json"
{
  "schema_version": 1,
  "build": {
    "default_target": "$OUT_DIR/config_build_target",
    "allow_overwrite": true
  },
  "state": {}
}
EOF
cat << 'EOF' > "$TEST_DIR/config_build_blueprint.md"
```text
root/
└── from_config.txt
```
### FILE: from_config.txt
```text
config target
```
EOF
set +e
OUTPUT=$( build "$TEST_DIR/config_build_blueprint.md" 2>&1 )
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Build with config-backed defaults failed.${NC}"
    exit 1
fi
if [ ! -f "$OUT_DIR/config_build_target/from_config.txt" ]; then
    echo -e "${RED}Build config default_target was not applied.${NC}"
    exit 1
fi

echo -e "  -> Testing CONFIG: Build Check Mode Applies From Global Config..."
cat << EOF > "$HOME/.seedling/config.json"
{
  "schema_version": 1,
  "build": {
    "default_target": "$OUT_DIR/config_build_check_target",
    "check": true,
    "allow_overwrite": true
  },
  "state": {}
}
EOF
set +e
OUTPUT=$( build "$TEST_DIR/config_build_blueprint.md" < /dev/null 2>&1 )
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Build with config-backed check mode failed.${NC}"
    exit 1
fi
if [ -f "$OUT_DIR/config_build_check_target/from_config.txt" ]; then
    echo -e "${RED}Build config check mode should not create physical files.${NC}"
    exit 1
fi
if [[ "$OUTPUT" != *"[CHECK MODE]"* ]]; then
    echo -e "${RED}Build config check mode was not applied.${NC}"
    exit 1
fi

echo -e "  -> Testing CONFIG: Clean Defaults Apply From Global Config..."
mkdir -p "$TEST_DIR/.next"
echo "node cache" > "$TEST_DIR/.next/cache.txt"
cat << EOF > "$HOME/.seedling/config.json"
{
  "schema_version": 1,
  "clean": {
    "strategy": "node-modules",
    "dry_run_default": true
  },
  "state": {}
}
EOF
set +e
OUTPUT=$( clean "$TEST_DIR" 2>&1 )
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Clean with config-backed defaults failed.${NC}"
    exit 1
fi
if [[ "$OUTPUT" != *"DRY-RUN"* ]] || [[ "$OUTPUT" != *".next"* ]]; then
    echo -e "${RED}Clean config defaults did not affect strategy or dry-run behavior.${NC}"
    exit 1
fi
if [ ! -d "$TEST_DIR/.next" ]; then
    echo -e "${RED}Dry-run clean unexpectedly removed .next cache.${NC}"
    exit 1
fi
