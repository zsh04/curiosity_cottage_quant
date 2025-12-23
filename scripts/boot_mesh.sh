#!/bin/bash

# Boot Mesh Script
# Task: Start the Holy Trinity (Oracle, Reflexivity, Siphon)

echo "Starting The Siphon (Data Ingest)..."
python3 app/services/ingest.py &
SIPHON_PID=$!
echo "Siphon PID: $SIPHON_PID"

echo "Starting The Reflexivity Engine (Soros + Physics)..."
python3 app/services/soros.py &
SOROS_PID=$!
echo "Soros PID: $SOROS_PID"

echo "Starting The Oracle (Brain Service)..."
python3 -m app.services.brain_service &
BRAIN_PID=$!
echo "Brain PID: $BRAIN_PID"

echo "Waiting for Oracle to warm up (15s)..."
sleep 15

# Verify
echo "Verifying Mesh..."
python3 scripts/verify_mesh.py

if [ $? -eq 0 ]; then
    echo "✅ MESH IS UP."
else
    echo "❌ MESH VERIFICATION FAILED."
fi

# Trap to kill background processes on exit
cleanup() {
    echo "Shutting down Mesh..."
    kill $SIPHON_PID
    kill $SOROS_PID
    kill $BRAIN_PID
}
trap cleanup EXIT

# Keep alive
wait $SIPHON_PID $SOROS_PID $BRAIN_PID
