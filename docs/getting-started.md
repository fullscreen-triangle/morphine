---
layout: page
title: Getting Started
nav_order: 6
---

<div class="page-logo">
  <img src="assets/Morphine2DCSDS.svg" alt="Morphine Chemical Structure" class="page-logo-img">
</div>

# Getting Started
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

1. TOC
{:toc}

---

## Quick Start

Get the Morphine Platform running locally in under 10 minutes with Docker.

### Prerequisites

- Docker 20.0+ with Docker Compose
- Git
- 8GB+ RAM
- NVIDIA GPU (recommended for computer vision)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/morphine.git
cd morphine

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Open the platform
open http://localhost:3000
```

That's it! The platform should be running with:
- Frontend at `http://localhost:3000`
- API at `http://localhost:3001`
- Stream endpoint at `http://localhost:8080`

## Development Setup

For development work, you'll want to run components individually for faster iteration.

### System Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **OS** | Linux/macOS/Windows | WSL2 recommended for Windows |
| **RAM** | 16GB+ | 8GB minimum |
| **Storage** | 50GB+ | For models and video data |
| **GPU** | NVIDIA with 4GB+ VRAM | Optional but recommended |
| **Network** | Broadband | For model downloads |

### Core Dependencies

#### Rust (Core Services)

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Verify installation
rustc --version
cargo --version

# Navigate to core directory
cd core

# Build and run
cargo build --release
cargo run --bin stream-server
```

#### Python (Computer Vision)

```bash
# Install Python 3.9+
python3 --version

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd analytics
pip install -r requirements.txt

# Download ML models
python scripts/download_models.py

# Test installation
python -m pytest tests/
```

#### Node.js (API Layer)

```bash
# Install Node.js 18+
node --version
npm --version

# Install dependencies
cd api
npm install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run in development mode
npm run dev
```

#### Next.js (Frontend)

```bash
# Install dependencies
cd frontend
npm install

# Set up environment
cp .env.local.example .env.local
# Edit .env.local with your configuration

# Run development server
npm run dev
```

## Configuration

### Environment Variables

Create and configure environment files for each service:

#### Core Service (`.env`)

```bash
# Core Rust service configuration
RUST_LOG=info
RUST_BACKTRACE=1

# WebRTC Configuration
STUN_SERVER=stun:stun.l.google.com:19302
TURN_SERVER=turn:your-turn-server.com
TURN_USERNAME=username
TURN_PASSWORD=password

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/morphine
REDIS_URL=redis://localhost:6379

# Analytics
ANALYTICS_QUEUE_SIZE=1000
CV_PROCESSING_THREADS=4
```

#### Analytics Service (`.env`)

```python
# Python ML service configuration
CUDA_VISIBLE_DEVICES=0
MODEL_CACHE_DIR=./models
LOG_LEVEL=INFO

# Computer Vision
VIBRIO_MODEL_PATH=./models/vibrio/
MORIARTY_MODEL_PATH=./models/moriarty/
POSE_COMPLEXITY=1
DETECTION_CONFIDENCE=0.5

# Performance
BATCH_SIZE=4
MAX_WORKERS=8
MEMORY_LIMIT=0.8
```

#### API Service (`.env`)

```bash
# Node.js API configuration
NODE_ENV=development
PORT=3001

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/morphine
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=your-secret-key
JWT_EXPIRES_IN=24h

# Streaming
STREAM_SERVER_URL=http://localhost:8080
WEBSOCKET_PORT=3002

# Betting
BETTING_ENABLED=true
MAX_BET_AMOUNT=1000
MIN_BET_AMOUNT=1
```

#### Frontend (`.env.local`)

```bash
# Next.js frontend configuration
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:3002
NEXT_PUBLIC_STREAM_URL=http://localhost:8080

# Authentication
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret

# Analytics
NEXT_PUBLIC_ANALYTICS_ENABLED=true
```

### Database Setup

#### PostgreSQL

```sql
-- Create database and user
CREATE DATABASE morphine;
CREATE USER morphine_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE morphine TO morphine_user;

-- Run migrations
cd api
npm run migrate
```

#### Redis

```bash
# Start Redis server
redis-server

# Verify connection
redis-cli ping
```

## Development Workflow

### Running Individual Services

Start services in this order for development:

```bash
# Terminal 1: Database services
docker-compose up postgres redis

# Terminal 2: Core Rust service
cd core
cargo run --bin stream-server

# Terminal 3: Python analytics
cd analytics
source venv/bin/activate
python -m src.main

# Terminal 4: Node.js API
cd api
npm run dev

# Terminal 5: Next.js frontend
cd frontend
npm run dev
```

### Hot Reloading

Each service supports hot reloading for development:

- **Rust**: Use `cargo watch -x run`
- **Python**: Built-in with `python -m src.main --reload`
- **Node.js**: Built-in with `npm run dev`
- **Next.js**: Built-in with `npm run dev`

### Testing

#### Unit Tests

```bash
# Rust tests
cd core
cargo test

# Python tests
cd analytics
python -m pytest

# Node.js tests
cd api
npm test

# Frontend tests
cd frontend
npm test
```

#### Integration Tests

```bash
# End-to-end tests
cd tests
npm install
npm run test:e2e
```

#### Load Testing

```bash
# Stream performance testing
cd tests/load
./test_streaming.sh

# API load testing
./test_api.sh

# Computer vision performance
./test_cv_pipeline.sh
```

## Common Tasks

### Adding a New Computer Vision Model

1. **Add model to analytics service:**

```python
# analytics/src/models/your_model.py
class YourModel:
    def __init__(self, model_path: str):
        self.model = load_model(model_path)
    
    def predict(self, frame: np.ndarray) -> Dict[str, Any]:
        # Your inference logic
        return results

# Register in analytics/src/pipeline.py
from .models.your_model import YourModel

class AnalyticsPipeline:
    def __init__(self):
        self.your_model = YourModel("path/to/model")
```

2. **Update API endpoints:**

```typescript
// api/src/routes/analytics.ts
router.get('/your-model/:streamId', async (req, res) => {
  const results = await analyticsService.getYourModelResults(req.params.streamId);
  res.json(results);
});
```

3. **Add frontend visualization:**

```typescript
// frontend/components/YourModelOverlay.tsx
const YourModelOverlay: React.FC = ({ data }) => {
  return (
    <div className="your-model-overlay">
      {/* Visualization logic */}
    </div>
  );
};
```

### Creating a New Betting Type

1. **Define bet type in Rust core:**

```rust
// core/src/betting/types.rs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BetType {
    // Existing types...
    YourBetType { param1: f64, param2: String },
}
```

2. **Implement bet generator:**

```rust
// core/src/betting/generators/your_generator.rs
pub struct YourBetGenerator;

impl BetGenerator for YourBetGenerator {
    async fn generate_bets(&self, analytics: &AnalyticsEvent) -> Result<Vec<MicroBet>> {
        // Your bet generation logic
    }
}
```

3. **Add frontend interface:**

```typescript
// frontend/components/betting/YourBetCard.tsx
const YourBetCard: React.FC = ({ bet, onPlace }) => {
  return (
    <div className="your-bet-card">
      {/* Betting interface */}
    </div>
  );
};
```

## Deployment

### Production Docker

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  morphine-core:
    image: morphine/core:latest
    environment:
      - RUST_LOG=warn
      - DATABASE_URL=${DATABASE_URL}
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  morphine-analytics:
    image: morphine/analytics:latest
    runtime: nvidia
    environment:
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      replicas: 2
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Kubernetes

```yaml
# k8s/morphine-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: morphine-platform
spec:
  replicas: 5
  selector:
    matchLabels:
      app: morphine
  template:
    spec:
      containers:
      - name: morphine-core
        image: morphine/core:latest
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi
```

### Environment-Specific Configurations

#### Development
- Hot reloading enabled
- Verbose logging
- Local database
- Mock services for external APIs

#### Staging
- Production builds
- Reduced logging
- Staging database
- Real external services

#### Production
- Optimized builds
- Error-only logging
- Production database
- Full monitoring

## Troubleshooting

### Common Issues

#### Port Conflicts

```bash
# Check what's using a port
lsof -i :3000

# Kill process
kill -9 <PID>
```

#### GPU Issues

```bash
# Check NVIDIA driver
nvidia-smi

# Verify CUDA installation
nvcc --version

# Test GPU in container
docker run --gpus all nvidia/cuda:11.0-base nvidia-smi
```

#### Memory Issues

```bash
# Check memory usage
docker stats

# Clean up Docker
docker system prune -a
```

#### Database Connection Issues

```bash
# Check PostgreSQL status
pg_isready -h localhost -p 5432

# View logs
docker logs morphine_postgres_1
```

### Performance Optimization

#### Rust Service

```toml
# Cargo.toml - Release optimizations
[profile.release]
lto = true
codegen-units = 1
panic = "abort"
```

#### Python Service

```python
# Use faster JSON library
import orjson as json

# Enable JIT compilation
import numba
```

#### Node.js Service

```bash
# Use production mode
NODE_ENV=production

# Enable clustering
PM2_INSTANCES=max
```

### Logging and Monitoring

#### Centralized Logging

```yaml
# docker-compose.yml
  fluentd:
    image: fluent/fluentd:v1.12
    volumes:
      - ./fluentd/conf:/fluentd/etc
    environment:
      - FLUENTD_CONF=fluent.conf
```

#### Metrics Collection

```bash
# Prometheus configuration
cd monitoring
docker-compose up prometheus grafana
```

#### Health Checks

```bash
# Service health endpoints
curl http://localhost:3001/health
curl http://localhost:8080/health
curl http://localhost:3000/api/health
```

## Next Steps

- [System Architecture](/architecture) - Understand the platform design
- [Computer Vision Deep Dive](/computer-vision) - Learn about CV capabilities
- [Streaming Implementation](/streaming-implementation) - Explore streaming features
- [Micro-Betting System](/micro-betting) - Understand betting mechanics
- [API Reference](/api-reference) - Detailed API documentation 