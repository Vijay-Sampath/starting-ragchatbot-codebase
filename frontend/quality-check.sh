#!/bin/bash

# Frontend Code Quality Check Script
# This script runs all code quality tools for the frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Frontend Code Quality Check${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    npm install
    echo ""
fi

# Parse arguments
FIX_MODE=false
CHECK_ONLY=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --fix) FIX_MODE=true ;;
        --check) CHECK_ONLY=true ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --fix     Auto-fix formatting and linting issues"
            echo "  --check   Only check without fixing (default)"
            echo "  -h, --help Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

ERRORS=0

# Run Prettier
echo -e "${BLUE}[1/3] Running Prettier (formatting)...${NC}"
if [ "$FIX_MODE" = true ]; then
    if npm run format; then
        echo -e "${GREEN}Formatting applied successfully.${NC}"
    else
        echo -e "${RED}Prettier encountered errors.${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    if npm run format:check; then
        echo -e "${GREEN}Formatting check passed.${NC}"
    else
        echo -e "${RED}Formatting issues found. Run with --fix to auto-fix.${NC}"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# Run ESLint
echo -e "${BLUE}[2/3] Running ESLint (JavaScript linting)...${NC}"
if [ "$FIX_MODE" = true ]; then
    if npm run lint:js:fix; then
        echo -e "${GREEN}JavaScript linting completed.${NC}"
    else
        echo -e "${RED}ESLint encountered errors that couldn't be auto-fixed.${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    if npm run lint:js; then
        echo -e "${GREEN}JavaScript linting passed.${NC}"
    else
        echo -e "${RED}JavaScript linting issues found. Run with --fix to auto-fix.${NC}"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# Run Stylelint
echo -e "${BLUE}[3/3] Running Stylelint (CSS linting)...${NC}"
if [ "$FIX_MODE" = true ]; then
    if npm run lint:css:fix; then
        echo -e "${GREEN}CSS linting completed.${NC}"
    else
        echo -e "${RED}Stylelint encountered errors that couldn't be auto-fixed.${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    if npm run lint:css; then
        echo -e "${GREEN}CSS linting passed.${NC}"
    else
        echo -e "${RED}CSS linting issues found. Run with --fix to auto-fix.${NC}"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# Summary
echo -e "${BLUE}======================================${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All quality checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$ERRORS quality check(s) failed.${NC}"
    if [ "$FIX_MODE" = false ]; then
        echo -e "${YELLOW}Tip: Run with --fix to auto-fix issues.${NC}"
    fi
    exit 1
fi
