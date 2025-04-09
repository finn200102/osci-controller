#!/bin/bash

# Activate virtual environment
source .venv/bin/activate

# Function to cleanup processes
cleanup() {
    echo "Stopping servers..."
    pkill -f "python main.py"
    pkill -f "python preassure_main.py"
    deactivate
    exit
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Start the oscilloscope server (main.py) in the background
echo "Starting oscilloscope server on port 8000..."
python main.py &

# Start the pressure server (preassure_main.py) in the background
echo "Starting pressure server on port 8001..."
python preassure_main.py &

echo "Both servers are running. Press Ctrl+C to stop."

# Wait indefinitely (or until Ctrl+C)
while true; do
    sleep 1
done 