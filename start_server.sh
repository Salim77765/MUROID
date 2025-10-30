#!/bin/bash

echo "========================================"
echo "YTMusic Backend Server Startup"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "Python found!"
python3 --version
echo ""

# Check if requirements are installed
echo "Checking dependencies..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
else
    echo "Dependencies already installed."
fi

echo ""
echo "========================================"
echo "Starting Flask server..."
echo "Server will be available at:"
echo "  - http://localhost:5000"
echo "  - http://127.0.0.1:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

python3 app.py
