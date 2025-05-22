#!/bin/bash

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Install package in development mode with test dependencies
pip install -e ".[test]"

# Run tests with coverage
pytest tests/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    -v 