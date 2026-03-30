#!/bin/bash
# Seedling-tools E2E Tests
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$DIR/common.sh"
set -e

echo -e "  -> Testing EXPORTER: JSON Output Mode (-F json)..."
set +e
scan "$TEST_DIR" -F json -d 2 -o "$OUT_DIR" -n "json_output.json" >/dev/null
set -e
if [ ! -f "$OUT_DIR/json_output.json" ] || ! grep -q '"meta"' "$OUT_DIR/json_output.json"; then
    echo -e "${RED}JSON output file missing or malformed!${NC}"
    exit 1
fi

echo -e "  -> Testing EXPORTER: JSON Output with --full..."
set +e
scan "$TEST_DIR" -F json --full -d 1 -o "$OUT_DIR" -n "json_full.json" >/dev/null
set -e
if ! grep -q '"contents"' "$OUT_DIR/json_full.json"; then
    echo -e "${RED}JSON --full failed! Should include contents field.${NC}"
    exit 1
fi

echo -e "  -> Testing EXPORTER: XML Output Mode (-F xml)..."
set +e
scan "$TEST_DIR" -F xml -d 2 -o "$OUT_DIR" -n "xml_output.xml" >/dev/null
set -e
if [ ! -f "$OUT_DIR/xml_output.xml" ] || ! grep -q "<ProjectAnalysis>" "$OUT_DIR/xml_output.xml"; then
    echo -e "${RED}XML output file missing or malformed!${NC}"
    exit 1
fi

echo -e "  -> Testing EXPORTER: XML Output with --full..."
set +e
scan "$TEST_DIR" -F xml --full -d 1 -o "$OUT_DIR" -n "xml_full.xml" >/dev/null
set -e
if ! grep -q "<SourceContents>" "$OUT_DIR/xml_full.xml"; then
    echo -e "${RED}XML --full failed! Should include SourceContents node.${NC}"
    exit 1
fi

echo -e "  -> Testing EXPORTER: Prompt Template System (--template)..."
echo "SYSTEM_PROMPT_INJECT_TEST {{SEEDLING_CONTEXT}} PROMPT_FOOTER_TEST" > "$TEST_DIR/dummy_prompt.txt"
set +e
scan "$TEST_DIR" --template "$TEST_DIR/dummy_prompt.txt" -o "$OUT_DIR" -n "template_output.md" >/dev/null
set -e
if [ ! -f "$OUT_DIR/template_output.md" ]; then
    echo -e "${RED}Template output file not created!${NC}"
    exit 1
fi
if ! grep -q "SYSTEM_PROMPT_INJECT_TEST" "$OUT_DIR/template_output.md" || ! grep -q "PROMPT_FOOTER_TEST" "$OUT_DIR/template_output.md"; then
    echo -e "${RED}Template injection failed! Header/Footer markers missing.${NC}"
    exit 1
fi

echo -e "  -> Testing EXPORTER: Normal Image Export (-F image)..."
set +e
OUTPUT=$(scan "$TEST_DIR/src" -F image -o "$OUT_DIR" -n "tree.png" 2>&1)
set -e
if [[ "$OUTPUT" == *"'Pillow' is required"* ]] || [[ "$OUTPUT" == *"Pillow is missing"* ]]; then
    echo -e "${YELLOW}     Skipping Image export test: Pillow library not installed in CI.${NC}"
else
    if [ ! -f "$OUT_DIR/tree.png" ]; then
        echo -e "${RED}Normal Image export failed! tree.png not found.${NC}"
        exit 1
    fi
    
    set +e
    scan "$TEST_DIR/src" -F image --full -o "$OUT_DIR" -n "tree_full.png" >/dev/null 2>&1
    set -e
    if [ -f "$OUT_DIR/tree_full.png" ]; then
        echo -e "${RED}Image export with --full should have fallen back to .md!${NC}"
        exit 1
    fi
    if [ ! -f "$OUT_DIR/tree_full.md" ]; then
        echo -e "${RED}Image fallback to .md failed!${NC}"
        exit 1
    fi
fi