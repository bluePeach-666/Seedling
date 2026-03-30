#!/bin/bash
# Seedling-tools Ultimate Automated Test Suite Entrypoint
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo -e "\033[0;34m   Starting Seedling FULL Test Suite... \033[0m"
echo -e "\n\033[0;32m-> [Phase 1] Running Python Unit Tests (pytest)...\033[0m"
if ! python3 -m pytest "$DIR/tests/unit" -v; then
    echo -e "\n\033[0;31m<<< CRITICAL: Unit Tests FAILED! Aborting E2E phase to save time.\033[0m"
    exit 1
fi
echo -e "\033[0;32m<<< Unit Tests PASSED!\033[0m"
source "$DIR/tests/e2e/common.sh"
echo -e "\n\033[0;32m-> [Phase 2] Setup COMPLEX Sandbox for E2E...\033[0m"
setup_sandbox

FAILED_TESTS=0
for test_file in "$DIR"/tests/e2e/test_*.sh; do
    echo -e "\n${YELLOW}>>> Running module: $(basename "$test_file") ${NC}"
    
    if bash "$test_file"; then
        echo -e "${GREEN}<<< Module Passed: $(basename "$test_file") ${NC}"
    else
        echo -e "${RED}<<< Module FAILED: $(basename "$test_file") ${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        break 
    fi
done

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}   ALL TESTS (UT + E2E) PASSED SUCCESSFULLY! ${NC}"
    cleanup_sandbox
    exit 0
else
    echo -e "${RED}   $FAILED_TESTS E2E TEST MODULE(S) FAILED! ${NC}"
    echo -e "${RED}   Sandbox kept at $TEST_DIR for debugging. ${NC}"
    exit 1
fi