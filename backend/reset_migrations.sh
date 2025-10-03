#!/bin/bash
# Reset Django migrations and database
# Use with caution - this will delete all data!

set -e  # Exit on error

BACKEND_DIR="/Users/eason/Documents/HW Project/deepsight-all/DeepSight-Django/backend"
cd "$BACKEND_DIR"

echo "=========================================="
echo "Django Migrations and Database Reset"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will DELETE ALL DATA!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Step 1: Deleting migration files..."
echo "=========================================="

# Find and delete all migration files except __init__.py
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
find . -path "*/migrations/__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "✓ Migration files deleted"
echo ""

echo "Step 2: Dropping database..."
echo "=========================================="
echo "Choose your database option:"
echo "  1) SQLite (delete db.sqlite3)"
echo "  2) PostgreSQL (need to manually drop and recreate)"
echo "  3) Skip database deletion"
read -p "Enter choice (1-3): " db_choice

case $db_choice in
    1)
        if [ -f "db.sqlite3" ]; then
            rm db.sqlite3
            echo "✓ SQLite database deleted"
        else
            echo "! No db.sqlite3 file found"
        fi
        ;;
    2)
        echo ""
        echo "For PostgreSQL, run these commands:"
        echo "  psql -U postgres"
        echo "  DROP DATABASE your_db_name;"
        echo "  CREATE DATABASE your_db_name;"
        echo "  \\q"
        echo ""
        read -p "Press Enter when done..."
        ;;
    3)
        echo "Skipping database deletion"
        ;;
esac

echo ""
echo "Step 3: Creating fresh migrations..."
echo "=========================================="

# Create migrations for each app
python manage.py makemigrations users
python manage.py makemigrations notebooks
python manage.py makemigrations reports
python manage.py makemigrations podcast
python manage.py makemigrations conferences

echo "✓ Fresh migrations created"
echo ""

echo "Step 4: Applying migrations..."
echo "=========================================="

python manage.py migrate

echo "✓ Migrations applied"
echo ""

echo "Step 5: Create superuser (optional)..."
echo "=========================================="
read -p "Do you want to create a superuser? (yes/no): " create_super

if [ "$create_super" = "yes" ]; then
    python manage.py createsuperuser
fi

echo ""
echo "=========================================="
echo "✓ Reset complete!"
echo "=========================================="
echo ""
echo "Your database is now clean with fresh migrations."
