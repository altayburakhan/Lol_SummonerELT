# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .venv\Scripts\Activate.ps1
}

# Install package in development mode with test dependencies
pip install -e ".[test]"

# Run tests with coverage
pytest tests/ `
    --cov=src `
    --cov-report=term-missing `
    --cov-report=html `
    -v 