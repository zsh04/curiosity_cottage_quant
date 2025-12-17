#!/bin/bash
set -e

echo "🚀 Starting Local CI Check..."

# 1. Database Schema Check
echo "🔍 Checking Database Schema Drift..."
# Check if models match migrations
# Note: 'alembic check' is a newer command, if fails we might need fallback
if alembic check; then
    echo "✅ Database Schema is in sync."
else
    echo "❌ Database Schema Drift detected! Run 'alembic revision --autogenerate' to fix."
    exit 1
fi

# 2. Frontend Check
echo "🎨 Checking Frontend Build..."
cd frontend
if npm run build; then
    echo "✅ Frontend Build Successful."
else
    echo "❌ Frontend Build Failed!"
    exit 1
fi
cd ..

# 3. Unit Tests
echo "🧪 Running Unit Tests..."
if pytest tests/unit; then
    echo "✅ Unit Tests Passed."
else
    echo "❌ Unit Tests Failed!"
    exit 1
fi

echo "✨ Local CI Passed! You are ready to push."
