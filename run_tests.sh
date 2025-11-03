#!/bin/bash
# Run tests for the Snippets application

echo "Running Snippets Tests..."
echo ""

# Set test environment variables
export SNIPPET_USERNAME=admin
export SNIPPET_PASSWORD=changeme
export SECRET_KEY=test-secret-key-for-testing-only

# Check if venv exists and is valid
if [ -d "venv" ]; then
    # Test if venv is working
    if ! ./venv/bin/python --version &>/dev/null; then
        echo "Warning: Existing venv is broken, recreating..."
        rm -rf venv
    fi
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
fi

# Install/update dependencies
echo "Installing dependencies..."
./venv/bin/pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

echo ""
echo "Running tests..."
echo ""

# Run pytest with coverage
./venv/bin/python -m pytest test_app.py -v --cov=app --cov-report=term-missing

# Check pytest exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "All tests passed!"
    exit 0
else
    echo ""
    echo "Tests failed!"
    exit 1
fi
