#!/bin/bash

# Activate the virtual environment
source venv_logydesk/bin/activate

# Start the Celery worker
celery -A app.main.celery_app worker --loglevel=info
