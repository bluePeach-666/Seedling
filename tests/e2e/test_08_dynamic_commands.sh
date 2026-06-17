#!/bin/bash
# Seedling-tools E2E Tests
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/common.sh"
set -e

setup_sandbox

CONFIG_HOME="$HOME/seedling_command_bus_home"
rm -rf "$CONFIG_HOME"
mkdir -p "$CONFIG_HOME/.seedling/plugins"
export HOME="$CONFIG_HOME"
export USERPROFILE="$CONFIG_HOME"

cat << EOF > "$HOME/.seedling/config.json"
{
  "schema_version": 1,
  "commands": {
    "plugin_dirs": ["$HOME/.seedling/plugins"],
    "autoload": true,
    "strict": false
  },
  "state": {}
}
EOF

cat << 'EOF' > "$HOME/.seedling/plugins/custom_audit.py"
from __future__ import annotations
import argparse
from seedlingtools.commands.cli import AbstractPluginCommand

class CustomAuditCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "custom-audit"

    @property
    def description(self) -> str:
        return "Custom audit command"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("target")
        parser.add_argument("--label", default="local")

    def execute(self, args: argparse.Namespace) -> None:
        print(f"custom audit {args.label} {args.target}")
EOF

echo -e "  -> Testing COMMAND BUS: Dynamic Help Discovery..."
set +e
HELP_OUTPUT=$(seedling --help 2>&1)
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}seedling --help failed.${NC}"
    exit 1
fi
if [[ "$HELP_OUTPUT" != *"custom-audit"* ]] || [[ "$HELP_OUTPUT" != *"scan"* ]] || [[ "$HELP_OUTPUT" != *"build"* ]] || [[ "$HELP_OUTPUT" != *"clean"* ]] || [[ "$HELP_OUTPUT" != *"config"* ]] || [[ "$HELP_OUTPUT" != *"tools"* ]]; then
    echo -e "${RED}Root command help did not include builtins and plugin command.${NC}"
    exit 1
fi

echo -e "  -> Testing COMMAND BUS: Plugin Help..."
set +e
PLUGIN_HELP=$(seedling custom-audit --help 2>&1)
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Plugin help failed.${NC}"
    exit 1
fi
if [[ "$PLUGIN_HELP" != *"--label"* ]]; then
    echo -e "${RED}Plugin help did not include custom arguments.${NC}"
    exit 1
fi

echo -e "  -> Testing COMMAND BUS: Plugin Dispatch..."
set +e
PLUGIN_OUTPUT=$(seedling custom-audit "$TEST_DIR" --label ci 2>&1)
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Plugin command dispatch failed.${NC}"
    exit 1
fi
if [[ "$PLUGIN_OUTPUT" != *"custom audit ci"* ]]; then
    echo -e "${RED}Plugin command did not produce expected output.${NC}"
    exit 1
fi

echo "def broken(:" > "$HOME/.seedling/plugins/broken_plugin.py"

echo -e "  -> Testing COMMAND BUS: Broken Plugin Isolation..."
set +e
BROKEN_HELP=$(seedling --help 2>&1)
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Broken plugin should not crash non-strict help.${NC}"
    exit 1
fi
if [[ "$BROKEN_HELP" != *"scan"* ]] || [[ "$BROKEN_HELP" != *"custom-audit"* ]]; then
    echo -e "${RED}Broken plugin isolation removed valid commands from help.${NC}"
    exit 1
fi

echo -e "  -> Testing COMMAND BUS: Builtin Scan Routing..."
set +e
seedling scan "$TEST_DIR" -q -o "$OUT_DIR" -n "bus_scan.md" >/dev/null 2>&1
STATUS=$?
set -e
if [ $STATUS -ne 0 ]; then
    echo -e "${RED}Builtin scan routing through seedling failed.${NC}"
    exit 1
fi
if [ ! -f "$OUT_DIR/bus_scan.md" ]; then
    echo -e "${RED}Builtin scan through seedling did not create output.${NC}"
    exit 1
fi
