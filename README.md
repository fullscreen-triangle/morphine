# Morphine Platform

> Computer Vision-Powered Streaming Platform with Real-Time Analytics and Micro-Betting

## Overview

Morphine is a novel streaming platform that combines advanced computer vision, real-time analytics, and micro-betting mechanics. The platform uses threshold-based stream activation and generates high-quality video annotations through user interactions.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Rust Core      │     │  Python ML      │     │  Node.js API    │
│  - Stream Engine│────►│  - CV Processing│────►│  - REST Layer   │
│  - State Mgmt   │     │  - Analytics    │     │  - WebSocket    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                     ┌─────────────────┐
                     │  Next.js Client │
                     │  - Stream View  │
                     │  - Betting UI   │
                     └─────────────────┘
```

## Components

### Core Services
- **`core/`** - Rust-based stream engine and state management
- **`analytics/`** - Python computer vision (Vibrio & Moriarty frameworks)
- **`api/`** - Node.js REST API and WebSocket server
- **`frontend/`** - Next.js React application

### Infrastructure
- **`docker/`** - Container configurations
- **`scripts/`** - Build and deployment scripts
- **`docs/`** - Technical documentation

## Quick Start

```bash
# Setup development environment
./scripts/setup-dev.sh

# Start all services
docker-compose up -d

# Run in development mode
./scripts/dev.sh
```

## Technology Stack

- **Backend**: Rust, Python, Node.js
- **Frontend**: Next.js, React, TypeScript
- **Computer Vision**: OpenCV, MediaPipe, YOLOv8
- **Database**: PostgreSQL, Redis
- **Infrastructure**: Docker, NGINX

## Documentation

See `/docs` for detailed technical documentation:
- [System Architecture](docs/technologies.md)
- [Computer Vision Framework](docs/vibrio.md)
- [Sports Analysis](docs/moriarty.md)
- [Streaming Platform](docs/streaming.md)
- [Micro-betting System](docs/micro-betting.md)

## License

MIT License
