#!/bin/bash

set -e

echo "🚀 Setting up Morphine development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p {analytics,api,frontend,docker/nginx,storage/streams,storage/models}

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Database
DATABASE_URL=postgres://morphine:morphine_dev_password@localhost:5432/morphine
POSTGRES_DB=morphine
POSTGRES_USER=morphine
POSTGRES_PASSWORD=morphine_dev_password

# Redis
REDIS_URL=redis://localhost:6379

# Core Service
BIND_ADDRESS=0.0.0.0:3001
ANALYTICS_SERVICE_URL=http://localhost:8000
STREAM_STORAGE_PATH=./storage/streams
MAX_CONCURRENT_STREAMS=10
STREAM_ACTIVATION_TIMEOUT=300

# API Service
PORT=3000
CORE_SERVICE_URL=http://localhost:3001
JWT_SECRET=your_jwt_secret_here_change_in_production
NODE_ENV=development

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:3000
NEXT_PUBLIC_WS_URL=ws://localhost:3001/ws
NEXT_PUBLIC_CORE_URL=http://localhost:3001
EOF
    echo "✅ Created .env file with default values"
fi

# Check if Rust is installed
if ! command -v cargo > /dev/null 2>&1; then
    echo "🦀 Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
else
    echo "✅ Rust is already installed"
fi

# Check if Node.js is installed
if ! command -v node > /dev/null 2>&1; then
    echo "📦 Node.js not found. Please install Node.js 18+ and try again."
    exit 1
else
    echo "✅ Node.js is available"
fi

# Check if Python is installed
if ! command -v python3 > /dev/null 2>&1; then
    echo "🐍 Python not found. Please install Python 3.8+ and try again."
    exit 1
else
    echo "✅ Python is available"
fi

# Build Rust core service
echo "🔨 Building Rust core service..."
cd core
cargo check
cd ..

echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the services: ./scripts/dev.sh"
echo "2. Or start with Docker: docker-compose up -d"
echo "3. Visit http://localhost:3002 for the frontend"
echo "4. API available at http://localhost:3000"
echo "5. Core service at http://localhost:3001" 