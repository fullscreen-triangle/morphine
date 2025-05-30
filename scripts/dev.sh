#!/bin/bash

set -e

echo "🚀 Starting Morphine development services..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Function to cleanup background processes
cleanup() {
    echo "🛑 Stopping development services..."
    jobs -p | xargs -r kill
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start PostgreSQL and Redis with Docker
echo "🐘 Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for database to be ready..."
until docker-compose exec postgres pg_isready -U morphine > /dev/null 2>&1; do
    sleep 1
done

echo "⏳ Waiting for Redis to be ready..."
until docker-compose exec redis redis-cli ping > /dev/null 2>&1; do
    sleep 1
done

echo "✅ Database services are ready!"

# Start Rust core service in development mode
echo "🦀 Starting Rust core service..."
cd core
cargo run &
CORE_PID=$!
cd ..

# Wait for core service to start
echo "⏳ Waiting for core service to start..."
sleep 5

# Start Python analytics service (if it exists)
if [ -d "analytics" ] && [ -f "analytics/requirements.txt" ]; then
    echo "🐍 Starting Python analytics service..."
    cd analytics
    python3 -m venv venv 2>/dev/null || true
    source venv/bin/activate
    pip install -r requirements.txt > /dev/null 2>&1 || true
    python3 main.py &
    ANALYTICS_PID=$!
    cd ..
else
    echo "⚠️  Analytics service not found, skipping..."
fi

# Start Node.js API service (if it exists)
if [ -d "api" ] && [ -f "api/package.json" ]; then
    echo "📦 Starting Node.js API service..."
    cd api
    npm install > /dev/null 2>&1 || true
    npm run dev &
    API_PID=$!
    cd ..
else
    echo "⚠️  API service not found, skipping..."
fi

# Start Next.js frontend (if it exists)
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo "⚛️  Starting Next.js frontend..."
    cd frontend
    npm install > /dev/null 2>&1 || true
    npm run dev &
    FRONTEND_PID=$!
    cd ..
else
    echo "⚠️  Frontend service not found, skipping..."
fi

echo ""
echo "🎉 All services started!"
echo ""
echo "📍 Service URLs:"
echo "   Frontend:  http://localhost:3002"
echo "   API:       http://localhost:3000"
echo "   Core:      http://localhost:3001"
echo "   Analytics: http://localhost:8000"
echo ""
echo "📊 Database URLs:"
echo "   PostgreSQL: localhost:5432 (morphine/morphine_dev_password)"
echo "   Redis:      localhost:6379"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for all background processes
wait 