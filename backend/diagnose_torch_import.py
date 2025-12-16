#!/usr/bin/env python
"""
Diagnostic script to find what's importing torch at celery startup.
Run this before starting celery to identify the culprit.
"""
import sys
import os

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# Track all imports
import_stack = []
torch_imported_by = None

original_import = __builtins__.__import__


def tracking_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Track imports and catch torch."""
    global torch_imported_by

    # Track the import stack
    import_stack.append(name)

    # Check if torch/transformers is being imported
    if not torch_imported_by and ('torch' in name or 'transformers' in name):
        print(f"\n{'='*80}")
        print(f"FOUND: {name} is being imported!")
        print(f"{'='*80}")
        print("Import stack:")
        for i, module in enumerate(import_stack):
            indent = "  " * i
            print(f"{indent}{module}")
        print(f"{'='*80}\n")
        torch_imported_by = name

    try:
        result = original_import(name, globals, locals, fromlist, level)
        return result
    finally:
        import_stack.pop()


# Replace import
__builtins__.__import__ = tracking_import

print("Starting Django setup with import tracking...")
print("=" * 80)

try:
    import django
    django.setup()
    print("\nDjango setup complete!")

    print("\nImporting celery app...")
    from backend.celery import app
    print("Celery app imported!")

    print("\nImporting task modules...")
    from notebooks.tasks import processing_tasks
    print("Processing tasks imported!")

    from semantic_search.tasks import semantic_search_streaming_task
    print("Semantic search tasks imported!")

    if torch_imported_by:
        print(f"\n{'='*80}")
        print(f"RESULT: torch was imported via: {torch_imported_by}")
        print(f"{'='*80}")
    else:
        print("\n" + "="*80)
        print("SUCCESS: No torch/transformers imported!")
        print("="*80)

except Exception as e:
    print(f"\nError during import: {e}")
    import traceback
    traceback.print_exc()
