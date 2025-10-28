#!/bin/bash

# Migration Cleanup Script for DeepSight Django Backend
# WARNING: This should ONLY be used in development environments!
#
# Usage:
#   ./scripts/cleanup_migrations.sh [options]
#
# Options:
#   --dry-run          Show what would be deleted without actually deleting
#   --skip-db-reset    Keep database intact, only recreate migration files
#   --auto-migrate     Automatically run migrations after recreation
#   --force            Skip confirmation prompts (use with caution!)

set -e  # Exit on error

# Colors
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
RESET='\033[0m'

# Parse arguments
DRY_RUN=false
SKIP_DB_RESET=false
AUTO_MIGRATE=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-db-reset)
            SKIP_DB_RESET=true
            shift
            ;;
        --auto-migrate)
            AUTO_MIGRATE=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --dry-run          Show what would be deleted without deleting"
            echo "  --skip-db-reset    Keep database intact, only recreate migrations"
            echo "  --auto-migrate     Automatically run migrations after recreation"
            echo "  --force            Skip confirmation prompts (use with caution!)"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${RESET}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to print colored messages
print_colored() {
    local message=$1
    local color=${2:-$RESET}
    echo -e "${color}${message}${RESET}"
}

# Function to confirm action
confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi

    local message=$1
    echo -en "${YELLOW}${message} (yes/no): ${RESET}"
    read -r response

    if [[ "$response" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        return 0
    else
        return 1
    fi
}

# Check environment safety
check_environment() {
    local django_env=${DJANGO_ENVIRONMENT:-development}

    if [ "$django_env" = "production" ]; then
        print_colored "ERROR: This script detected production environment!" "$RED"
        print_colored "Migration cleanup should NEVER be run in production!" "$RED"
        exit 1
    fi

    if [ "$django_env" != "development" ]; then
        print_colored "WARNING: Environment is '$django_env', not 'development'" "$YELLOW"
        if ! confirm "Are you sure you want to continue?"; then
            exit 0
        fi
    fi
}

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Check environment
check_environment

print_colored "\n============================================================" "$BLUE"
print_colored "Django Migration Cleanup Script" "$BLUE"
print_colored "============================================================" "$BLUE"
print_colored "Project root: $PROJECT_ROOT" "$BLUE"

if [ "$DRY_RUN" = true ]; then
    print_colored "Mode: DRY RUN" "$YELLOW"
else
    print_colored "Mode: LIVE" "$RED"
fi

# Find migration files
print_colored "\nSearching for migration files..." "$BLUE"

migration_files=$(find . -path "*/migrations/*.py" -not -name "__init__.py" -not -path "*/venv/*" -not -path "*/.venv/*" 2>/dev/null || true)
pyc_files=$(find . -path "*/migrations/*.pyc" -not -path "*/venv/*" -not -path "*/.venv/*" 2>/dev/null || true)

migration_count=$(echo "$migration_files" | grep -c . || echo "0")
pyc_count=$(echo "$pyc_files" | grep -c . || echo "0")
total_count=$((migration_count + pyc_count))

print_colored "Found $migration_count migration .py files" "$YELLOW"
print_colored "Found $pyc_count migration .pyc files" "$YELLOW"
print_colored "Total: $total_count files to delete" "$YELLOW"

# Django apps
django_apps=$(find . -maxdepth 1 -type d -name "[!.]*" -exec test -e "{}/models.py" -o -e "{}/models" -o -e "{}/migrations" \; -print | sed 's|^\./||' | sort)
app_count=$(echo "$django_apps" | grep -c . || echo "0")
print_colored "Found $app_count Django apps: $(echo $django_apps | tr '\n' ' ')" "$YELLOW"

# Show files in dry run
if [ "$DRY_RUN" = true ]; then
    print_colored "\nMigration files that would be deleted:" "$BLUE"
    if [ -n "$migration_files" ]; then
        echo "$migration_files" | while read -r file; do
            echo "  - $file"
        done
    fi
    if [ -n "$pyc_files" ]; then
        echo "$pyc_files" | while read -r file; do
            echo "  - $file"
        done
    fi
    print_colored "\nDRY RUN: No files were actually deleted" "$GREEN"
    exit 0
fi

# Confirm deletion
print_colored "\n⚠️  WARNING: This will delete all migration files!" "$RED"
if [ "$SKIP_DB_RESET" = false ]; then
    print_colored "⚠️  WARNING: This will also require you to reset your database!" "$RED"
fi

if ! confirm "\nDo you want to continue?"; then
    print_colored "Operation cancelled" "$YELLOW"
    exit 0
fi

# Step 1: Delete migration files
print_colored "\n============================================================" "$BLUE"
print_colored "Step 1: Deleting migration files" "$BLUE"
print_colored "============================================================" "$BLUE"

deleted_count=0

if [ -n "$migration_files" ]; then
    echo "$migration_files" | while read -r file; do
        if [ -f "$file" ]; then
            rm -f "$file"
            echo "  ✓ Deleted: $file"
            ((deleted_count++)) || true
        fi
    done
fi

if [ -n "$pyc_files" ]; then
    echo "$pyc_files" | while read -r file; do
        if [ -f "$file" ]; then
            rm -f "$file"
            echo "  ✓ Deleted: $file"
            ((deleted_count++)) || true
        fi
    done
fi

# Also delete __pycache__ in migrations directories
find . -path "*/migrations/__pycache__" -type d -not -path "*/venv/*" -not -path "*/.venv/*" -exec rm -rf {} + 2>/dev/null || true

print_colored "\n✓ Deleted migration files" "$GREEN"

# Step 2: Database reset reminder
if [ "$SKIP_DB_RESET" = false ]; then
    print_colored "\n============================================================" "$BLUE"
    print_colored "Step 2: Reset Database" "$BLUE"
    print_colored "============================================================" "$BLUE"

    print_colored "\nYou need to reset your database. Choose one method:" "$YELLOW"
    print_colored "\n  Option 1 - PostgreSQL (manual):" "$BLUE"
    print_colored "    psql -U your_user -d postgres" "$RESET"
    print_colored "    DROP DATABASE deepsight;" "$RESET"
    print_colored "    CREATE DATABASE deepsight;" "$RESET"

    print_colored "\n  Option 2 - Django extensions (if installed):" "$BLUE"
    print_colored "    python manage.py reset_db --noinput" "$RESET"

    print_colored "\n  Option 3 - SQLite (if using):" "$BLUE"
    print_colored "    rm db.sqlite3" "$RESET"

    if ! confirm "\nHave you reset the database?"; then
        print_colored "Please reset the database and then run:" "$YELLOW"
        print_colored "  python manage.py makemigrations" "$BLUE"
        print_colored "  python manage.py migrate" "$BLUE"
        exit 0
    fi
fi

# Step 3: Create new migrations
print_colored "\n============================================================" "$BLUE"
print_colored "Step 3: Creating new migrations" "$BLUE"
print_colored "============================================================" "$BLUE"

print_colored "\n▶ Creating migrations for all apps..." "$BLUE"
if python manage.py makemigrations; then
    print_colored "✓ Migrations created successfully" "$GREEN"
else
    print_colored "✗ Failed to create migrations" "$RED"
    exit 1
fi

# Step 4: Apply migrations
if [ "$AUTO_MIGRATE" = true ]; then
    print_colored "\n============================================================" "$BLUE"
    print_colored "Step 4: Applying migrations" "$BLUE"
    print_colored "============================================================" "$BLUE"

    print_colored "\n▶ Applying migrations..." "$BLUE"
    if python manage.py migrate; then
        print_colored "✓ Migrations applied successfully" "$GREEN"
    else
        print_colored "✗ Failed to apply migrations" "$RED"
        exit 1
    fi
else
    print_colored "\n============================================================" "$BLUE"
    print_colored "Step 4: Apply migrations manually" "$BLUE"
    print_colored "============================================================" "$BLUE"
    print_colored "\nPlease run manually:" "$YELLOW"
    print_colored "  python manage.py migrate" "$BLUE"
fi

# Summary
print_colored "\n============================================================" "$GREEN"
print_colored "Migration cleanup completed successfully!" "$GREEN"
print_colored "============================================================" "$GREEN"

if [ "$AUTO_MIGRATE" = false ]; then
    print_colored "\nNext steps:" "$YELLOW"
    print_colored "  1. Run: python manage.py migrate" "$BLUE"
    print_colored "  2. Run: python manage.py createsuperuser" "$BLUE"
    print_colored "  3. Reload any fixtures or test data" "$BLUE"
fi

print_colored "\n✓ Done!\n" "$GREEN"
