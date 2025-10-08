#!/bin/bash
# SABC Test Runner Script
# Comprehensive testing with multiple modes

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║              SABC Test Runner v1.0                             ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install test dependencies: pip install -r requirements-test.txt"
    exit 1
fi

# Parse command line arguments
MODE="${1:-all}"

case "$MODE" in
    "unit")
        echo -e "${YELLOW}Running unit tests only...${NC}"
        pytest tests/unit/ -v
        ;;

    "integration")
        echo -e "${YELLOW}Running integration tests only...${NC}"
        pytest tests/integration/ -v
        ;;

    "routes")
        echo -e "${YELLOW}Running route tests only...${NC}"
        pytest tests/routes/ -v
        ;;

    "security")
        echo -e "${YELLOW}Running security tests only...${NC}"
        pytest tests/security/ -v
        ;;

    "fast")
        echo -e "${YELLOW}Running fast tests (excluding slow tests)...${NC}"
        pytest -m "not slow" -v
        ;;

    "coverage")
        echo -e "${YELLOW}Running tests with coverage report...${NC}"
        pytest --cov=. --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;

    "ci")
        echo -e "${YELLOW}Running CI test suite...${NC}"
        pytest --cov=. --cov-report=xml --cov-report=term --cov-fail-under=80 -x
        ;;

    "parallel")
        echo -e "${YELLOW}Running tests in parallel...${NC}"
        pytest -n auto -v
        ;;

    "all")
        echo -e "${YELLOW}Running all tests...${NC}"
        pytest -v
        ;;

    "watch")
        echo -e "${YELLOW}Running tests in watch mode...${NC}"
        echo -e "${BLUE}Tests will re-run on file changes${NC}"
        pytest-watch
        ;;

    "help"|"-h"|"--help")
        echo "Usage: ./scripts/run_tests.sh [mode]"
        echo ""
        echo "Modes:"
        echo "  all          - Run all tests (default)"
        echo "  unit         - Run unit tests only"
        echo "  integration  - Run integration tests only"
        echo "  routes       - Run route/endpoint tests only"
        echo "  security     - Run security tests only"
        echo "  fast         - Run fast tests (skip slow tests)"
        echo "  coverage     - Run tests with HTML coverage report"
        echo "  ci           - Run tests as in CI (fail if coverage < 80%)"
        echo "  parallel     - Run tests in parallel (faster)"
        echo "  watch        - Run tests in watch mode (re-run on changes)"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./scripts/run_tests.sh unit"
        echo "  ./scripts/run_tests.sh coverage"
        echo "  ./scripts/run_tests.sh fast"
        exit 0
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Run './scripts/run_tests.sh help' for usage information"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}║                  ✅ ALL TESTS PASSED ✅                        ║${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
else
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                                ║${NC}"
    echo -e "${RED}║                  ❌ TESTS FAILED ❌                            ║${NC}"
    echo -e "${RED}║                                                                ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
