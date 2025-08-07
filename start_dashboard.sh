#!/bin/bash

# Assignment Assistant Dashboard Startup Script
# This script sets up the environment and starts the dashboard

echo "Starting Assignment Assistant Dashboard..."

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found. Using default values."
    export BUBBLE_API_KEY_LIVE="your-bubble-api-key-here"
    export SESSION_SECRET="assignment-assistant-secret-key-2025"
    export PORT=5001
fi

# Kill any existing processes on the port
echo "Checking for existing processes on port $PORT..."
lsof -ti:$PORT | xargs kill -9 2>/dev/null

# Start the Flask application
echo "Starting Flask application on port $PORT..."
python3 app.py

# The dashboard will be available at http://localhost:5001