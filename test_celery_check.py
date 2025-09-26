#!/usr/bin/env python
"""
Simple test script to verify Celery health check works
Run this with Celery stopped to see the behavior
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/Users/eason/Documents/HW Project/deepsight-all/DeepSight-Django/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from reports.services.job import JobService

def test_celery_health_check():
    print("Testing Celery health check...")

    job_service = JobService()
    is_running = job_service.check_celery_workers()

    if is_running:
        print("✅ Celery workers are running and responding")
    else:
        print("❌ Celery workers are NOT running")

    return is_running

if __name__ == "__main__":
    test_celery_health_check()