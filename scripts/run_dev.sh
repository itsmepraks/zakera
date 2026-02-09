#!/bin/bash

# Development runner script
echo "🚀 Starting Zakera in development mode..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
fi

# Start backend in background
echo "🔧 Starting backend server..."
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Backend PID: $BACKEND_PID"

# Wait a moment for backend to start
sleep 2

# Start frontend
echo "🎨 Starting frontend..."
cd src/frontend
npm run dev &
FRONTEND_PID=$!

echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "✨ Zakera is running!"
echo "📍 Backend: http://localhost:8000"
echo "📍 Frontend: http://localhost:3000"
echo "📍 API Docs: http://localhost:8000/api/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Handle cleanup
trap "echo '\n🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM

# Wait for processes
wait
