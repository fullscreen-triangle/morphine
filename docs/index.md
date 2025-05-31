---
layout: home
title: Home
---

<div class="logo-header">
  <img src="assets/morphine_logo.gif" alt="Morphine Platform Logo" class="platform-logo">
</div>

# Morphine Platform
{: .hero-title}

**Computer Vision-Powered Streaming Platform with Real-Time Analytics and Micro-Betting**
{: .hero-subtitle}

[Get Started](/getting-started){: .btn .btn-primary .btn-lg} [View Architecture](/architecture){: .btn .btn-outline .btn-lg}

---

## What is Morphine?

Morphine is a revolutionary streaming platform that combines cutting-edge computer vision technology with real-time analytics and innovative micro-betting mechanics. Built on a robust multi-language architecture, it delivers low-latency streaming experiences with intelligent content analysis and interactive features.

## Key Features

<div class="feature-grid">
  <div class="feature-card">
    <h3>🎥 Advanced Streaming</h3>
    <p>Rust-powered stream engine with WebRTC for ultra-low latency video delivery and real-time state management.</p>
  </div>
  
  <div class="feature-card">
    <h3>🔬 Computer Vision</h3>
    <p>Powered by Vibrio and Moriarty frameworks for real-time video analysis, object detection, and intelligent annotations.</p>
  </div>
  
  <div class="feature-card">
    <h3>📊 Real-Time Analytics</h3>
    <p>Python-based ML pipeline processing frames in real-time with CUDA acceleration for instant insights.</p>
  </div>
  
  <div class="feature-card">
    <h3>🎯 Micro-Betting</h3>
    <p>Innovative betting mechanics integrated with stream events, powered by real-time analytics and user interactions.</p>
  </div>
  
  <div class="feature-card">
    <h3>🚀 High Performance</h3>
    <p>Multi-language architecture optimized for speed: Rust for core services, Python for ML, Node.js for APIs.</p>
  </div>
  
  <div class="feature-card">
    <h3>🔧 Developer Friendly</h3>
    <p>Comprehensive APIs, WebSocket connections, and modern frontend built with Next.js and React.</p>
  </div>
</div>

## Architecture Overview

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

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Core** | Rust | High-performance stream processing |
| **Analytics** | Python + OpenCV | Computer vision and ML inference |
| **API** | Node.js + Express | RESTful services and WebSocket |
| **Frontend** | Next.js + React | Modern user interface |
| **Database** | PostgreSQL + Redis | Data persistence and caching |
| **Infrastructure** | Docker + NGINX | Container orchestration |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/morphine.git
cd morphine

# Setup development environment
./scripts/setup-dev.sh

# Start all services
docker-compose up -d

# Access the platform
open http://localhost:3000
```

## Use Cases

- **Sports Streaming**: Real-time analysis of sports events with automated highlight detection
- **Gaming Platforms**: Interactive streaming with computer vision-enhanced viewer engagement
- **Educational Content**: Automated content analysis and interactive learning features
- **Live Events**: Real-time crowd analysis and engagement metrics

## Getting Involved

- 📖 [Read the Documentation](/architecture)
- 🚀 [Quick Start Guide](/getting-started)
- 🔧 [API Reference](/api-reference)
- 💡 [Computer Vision Deep Dive](/computer-vision)
- 🎲 [Micro-Betting System](/micro-betting)

---

<div class="cta-section">
  <h2>Ready to Build the Future of Streaming?</h2>
  <p>Explore the technical documentation and start building with Morphine Platform today.</p>
  <a href="/getting-started" class="btn btn-primary btn-lg">Get Started Now</a>
</div> 