#!/bin/bash
# Script to clear Python cache files

echo "Clearing Python cache files..."

# Clear __pycache__ directories
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Clear .pyc files
find backend -type f -name "*.pyc" -delete

# Clear .pyo files
find backend -type f -name "*.pyo" -delete

echo "Python cache cleared successfully!"
echo ""
echo "Next steps:"
echo "1. Restart the Django development server"
echo "2. Restart all Celery workers"
echo "3. Update your .env file with MINIO_PUBLIC_ENDPOINT setting"
