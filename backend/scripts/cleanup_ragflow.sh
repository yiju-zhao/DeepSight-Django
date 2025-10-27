#!/bin/bash

# RagFlow Cleanup Script
# =====================
# This script cleans up all RagFlow datasets, agents, and chat sessions.
# It calls the Django management command to perform the cleanup.
#
# Usage:
#   ./cleanup_ragflow.sh              # Interactive cleanup with confirmation
#   ./cleanup_ragflow.sh --dry-run    # Preview what would be deleted
#   ./cleanup_ragflow.sh --force      # Skip confirmation prompt
#
# Requirements:
#   - Django environment must be configured
#   - RagFlow API credentials must be set in .env
#   - Must be run from the backend directory

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Print header
print_header() {
    echo ""
    echo -e "${BLUE}=====================================================================${NC}"
    echo -e "${BLUE}  RagFlow Cleanup Script${NC}"
    echo -e "${BLUE}=====================================================================${NC}"
    echo ""
}

# Check if we're in the backend directory
check_directory() {
    if [ ! -f "manage.py" ]; then
        print_error "Error: manage.py not found!"
        print_error "Please run this script from the backend directory."
        exit 1
    fi
    print_success "Running from backend directory"
}

# Check if virtual environment is activated
check_venv() {
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "Virtual environment not detected."
        print_warning "Make sure your Python environment is configured correctly."
        echo ""
    else
        print_success "Virtual environment activated: $VIRTUAL_ENV"
    fi
}

# Check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        print_error "Error: .env file not found!"
        print_error "Please create a .env file with RagFlow configuration."
        print_error "Required variables: RAGFLOW_API_KEY, RAGFLOW_BASE_URL"
        exit 1
    fi
    print_success "Environment file found"
}

# Check if RagFlow credentials are set
check_credentials() {
    # Source .env to check variables
    set -a
    source .env
    set +a

    if [ -z "$RAGFLOW_API_KEY" ]; then
        print_error "Error: RAGFLOW_API_KEY not set in .env!"
        exit 1
    fi

    if [ -z "$RAGFLOW_BASE_URL" ]; then
        print_warning "RAGFLOW_BASE_URL not set, will use default"
    fi

    print_success "RagFlow credentials configured"
}

# Run pre-flight checks
preflight_checks() {
    print_info "Running pre-flight checks..."
    echo ""

    check_directory
    check_env
    check_credentials
    check_venv

    echo ""
    print_success "All checks passed!"
    echo ""
}

# Main execution
main() {
    print_header

    # Run checks
    preflight_checks

    # Parse arguments
    ARGS="$@"

    # Show help if requested
    if [[ "$ARGS" == *"--help"* ]] || [[ "$ARGS" == *"-h"* ]]; then
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --dry-run    Preview what would be deleted without making changes"
        echo "  --force      Skip confirmation prompt"
        echo "  --help       Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                 # Interactive cleanup with confirmation"
        echo "  $0 --dry-run       # Preview changes"
        echo "  $0 --force         # Skip confirmation"
        echo ""
        exit 0
    fi

    # Show warning for dry-run
    if [[ "$ARGS" == *"--dry-run"* ]]; then
        print_info "Running in DRY RUN mode - no changes will be made"
        echo ""
    fi

    # Show warning for force mode
    if [[ "$ARGS" == *"--force"* ]] && [[ "$ARGS" != *"--dry-run"* ]]; then
        print_warning "Running in FORCE mode - confirmation will be skipped!"
        echo ""
    fi

    # Execute Django management command
    print_info "Executing cleanup command..."
    echo ""

    if python manage.py cleanup_ragflow $ARGS; then
        echo ""
        print_success "Script completed successfully!"
    else
        echo ""
        print_error "Script failed with errors!"
        exit 1
    fi
}

# Run main function
main "$@"
