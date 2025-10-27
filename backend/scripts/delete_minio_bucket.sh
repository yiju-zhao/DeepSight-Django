#!/bin/bash

# MinIO Bucket Deletion Script
# ============================
# This script deletes a MinIO bucket and all its objects.
# It calls the Django management command to perform the deletion.
#
# Usage:
#   ./scripts/delete_minio_bucket.sh                    # Interactive deletion with confirmation
#   ./scripts/delete_minio_bucket.sh --dry-run          # Preview what would be deleted
#   ./scripts/delete_minio_bucket.sh --force            # Skip confirmation prompt
#   ./scripts/delete_minio_bucket.sh --bucket my-bucket # Delete specific bucket
#
# Requirements:
#   - Django environment must be configured
#   - MinIO credentials must be set in .env
#   - Script is located in backend/scripts/ directory

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and navigate to backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

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
    echo -e "${BLUE}  MinIO Bucket Deletion Script${NC}"
    echo -e "${BLUE}=====================================================================${NC}"
    echo ""
}

# Check if we can find the backend directory with manage.py
check_directory() {
    if [ ! -f "manage.py" ]; then
        print_error "Error: manage.py not found!"
        print_error "Cannot locate backend directory from: $SCRIPT_DIR"
        print_error "Please ensure this script is in backend/scripts/"
        exit 1
    fi
    print_success "Found backend directory: $BACKEND_DIR"
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
        print_error "Please create a .env file with MinIO configuration."
        print_error "Required variables: MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY"
        exit 1
    fi
    print_success "Environment file found"
}

# Check if MinIO credentials are set
check_credentials() {
    # Source .env to check variables
    set -a
    source .env
    set +a

    if [ -z "$MINIO_ACCESS_KEY" ]; then
        print_warning "MINIO_ACCESS_KEY not set, will use default (minioadmin)"
    fi

    if [ -z "$MINIO_SECRET_KEY" ]; then
        print_warning "MINIO_SECRET_KEY not set, will use default (minioadmin)"
    fi

    if [ -z "$MINIO_ENDPOINT" ]; then
        print_warning "MINIO_ENDPOINT not set, will use default (http://localhost:9000)"
    fi

    print_success "MinIO configuration checked"
}

# Check if boto3 is installed
check_boto3() {
    if ! python -c "import boto3" 2>/dev/null; then
        print_error "Error: boto3 is not installed!"
        print_error "Please install it with: pip install boto3"
        exit 1
    fi
    print_success "boto3 library is installed"
}

# Run pre-flight checks
preflight_checks() {
    print_info "Running pre-flight checks..."
    echo ""

    check_directory
    check_env
    check_credentials
    check_boto3
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
        echo "  --bucket NAME  Specify bucket name to delete (defaults to 'deepsight-users')"
        echo "  --dry-run      Preview what would be deleted without making changes"
        echo "  --force        Skip confirmation prompt"
        echo "  --help         Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                          # Interactive deletion with confirmation"
        echo "  $0 --dry-run                # Preview deletion"
        echo "  $0 --force                  # Skip confirmation"
        echo "  $0 --bucket my-bucket       # Delete specific bucket"
        echo "  $0 --bucket test --dry-run  # Preview deletion of 'test' bucket"
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

    # Extract bucket name if provided
    BUCKET_NAME=""
    if [[ "$ARGS" == *"--bucket"* ]]; then
        # Extract bucket name from arguments
        for i in "$@"; do
            if [[ "$prev" == "--bucket" ]]; then
                BUCKET_NAME="$i"
                print_info "Target bucket: $BUCKET_NAME"
                echo ""
                break
            fi
            prev="$i"
        done
    fi

    # Execute Django management command
    print_info "Executing bucket deletion command..."
    echo ""

    if python manage.py delete_minio_bucket $ARGS; then
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
