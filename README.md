# Morphine: Live Streaming Platform with Microbetting

<div align="center">
  <img src="docs/assets/morphine_logo.gif" alt="Morphine Logo" width="400"/>
</div>

> Live streaming platform with real-time computer vision analytics and microbetting functionality

## 🎥 What is Morphine?

Morphine is a **live streaming platform** that enables viewers to place **microbets** on stream events using real-time computer vision analytics. Watch live streams and bet on what happens next - from sports performance to gaming achievements.

Key Features:
- **🔴 Live Streaming** - High-quality video streaming with low latency
- **💰 Microbetting** - Place small bets on live stream events  
- **🤖 Smart Analytics** - Computer vision automatically detects betting opportunities
- **⚡ Real-time** - Instant bet placement and settlement based on live video analysis
- **📊 Live Data** - Real-time analytics dashboard with performance metrics

## 🎯 How It Works

1. **Stream Content** - Content creators stream live video (sports, gaming, etc.)
2. **AI Detection** - Computer vision analyzes the stream in real-time
3. **Betting Markets** - System creates betting opportunities based on detected events  
4. **Place Bets** - Viewers place microbets on stream outcomes
5. **Auto Settlement** - Bets are automatically settled using computer vision analysis

## 🏗️ Platform Architecture

### Streaming + Betting Stack
```
Frontend (Next.js)     → Live streaming interface with betting controls
API (Node.js)          → Real-time betting API with WebSocket support  
Analytics (Python)     → Computer vision for automatic bet detection
Core (Rust)            → High-performance bet processing and settlement
```

### Computer Vision Analytics

#### Stream Analysis
- **Real-time object detection** - Track players, objects, and actions
- **Event recognition** - Automatically identify bettable moments
- **Performance metrics** - Speed, accuracy, and achievement tracking
- **Highlight detection** - Find key moments for betting opportunities

#### Betting Integration  
- **Smart bet creation** - AI suggests betting markets based on video analysis
- **Instant settlement** - Bets resolved immediately using computer vision
- **Live odds** - Dynamic odds based on real-time performance data
- **Fair play** - Transparent, automated settlement with video evidence

## 🚀 Getting Started

### Prerequisites
- **Docker & Docker Compose** - For containerized deployment
- **Rust 1.75+** - For core service development  
- **Python 3.8+** - For analytics and computer vision
- **Node.js 18+** - For API and frontend
- **CUDA GPU** (recommended) - For real-time computer vision

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/morphine.git
cd morphine

# Set up the complete system
./scripts/setup-dev.sh

# Start all services
docker-compose up -d

# Access the system
open http://localhost:3002  # Frontend interface
```

### Service Architecture

```
Frontend (Next.js)     → http://localhost:3002
├── Real-time streaming dashboard
├── Advanced analytics visualization  
├── Sophisticated betting interface
└── Metacognitive system monitoring

API Layer (Node.js)    → http://localhost:3000  
├── RESTful endpoints for all functionality
├── WebSocket real-time communication
├── Authentication and authorization
└── Integration orchestration

Core Engine (Rust)     → http://localhost:3001
├── Metacognitive orchestrator
├── Geolocation verification
├── Hybrid reasoning engine
└── High-performance state management

Analytics (Python)     → http://localhost:8000
├── Vibrio computer vision framework
├── Moriarty biomechanical analysis
├── Real-time ML inference
└── Advanced pattern recognition
```

## 🎮 How It Actually Works

### 1. Stream Processing Pipeline

```
Live Video → Computer Vision → Metacognitive Analysis → Intelligent Decisions
     ↓              ↓                    ↓                       ↓
  WebRTC       Vibrio/Moriarty    Three-Layer Brain      Real-time Actions
```

### 2. Location Verification Flow

```
User Action → Multi-Source Location → Kalman Filtering → Exclusion Check → Crypto Proof
     ↓               ↓                      ↓                   ↓             ↓
GPS+WiFi+Cell   Triangulation+Video    Temporal Smoothing   Zone Detection  Blockchain
```

### 3. Intelligent Decision Making

```
Partial Data → Context Layer → Reasoning Layer → Intuition Layer → Final Decision
     ↓              ↓               ↓                ↓                  ↓
Stream Input   Data Fusion    Logic Engine    Pattern Match     Confidence Score
```

## 🔧 Advanced Configuration

### Metacognitive Orchestrator Settings

```rust
// Configure the three-layer processing
let orchestrator = MetacognitiveOrchestrator::new()
    .with_context_confidence_threshold(0.7)
    .with_reasoning_timeout(Duration::from_millis(50))
    .with_intuition_pattern_depth(3)
    .with_metabolic_resource_allocation(0.8);
```

### Geolocation Verification Settings

```rust
// Set up precision location tracking
let geolocation = GeolocationService::new()
    .with_nanosecond_precision(true)
    .with_multi_source_fusion(true)
    .with_exclusion_zones(vec![
        ExclusionZone::event_location(lat, lon, radius_meters),
        ExclusionZone::competitor_zone(lat, lon, radius_meters),
    ]);
```

### Hybrid Reasoning Configuration

```rust
// Configure reasoning paradigm weights
let reasoning = HybridReasoningEngine::new()
    .with_paradigm_weights(HashMap::from([
        ("imperative".to_string(), 0.4),
        ("logical".to_string(), 0.3), 
        ("fuzzy".to_string(), 0.3),
    ]))
    .with_settlement_methods(vec![
        DistributionMethod::HybridDistribution,
        DistributionMethod::FuzzyProportional,
    ]);
```

## 📊 Performance Characteristics

| Operation | Target Latency | Description |
|-----------|---------------|-------------|
| **Streaming Decision** | < 90ms | Complete three-layer processing |
| **Location Verification** | < 50ms | Multi-source fusion + Kalman filtering |
| **Bet Settlement** | < 100ms | Hybrid reasoning across paradigms |
| **Frame Processing** | < 100ms | Computer vision + analytics |
| **Geolocation Update** | < 20ms | Real-time location tracking |

## 🔐 Security & Verification

### Cryptographic Proofs
- **SHA-256 hashing** for transaction integrity
- **Nanosecond timestamps** for temporal verification  
- **Multi-factor location** binding
- **Blockchain-ready** immutable records

### Exclusion Zone Enforcement
- **Real-time geofencing** with configurable boundaries
- **Historical verification** for post-transaction validation
- **Appeal process** with complete audit trails
- **Legal compliance** with regional restrictions

## 🌐 API Documentation

### Metacognitive Orchestration Endpoints

```bash
# Process streaming decisions with partial data
POST /orchestrator/streaming-decision
{
  "stream_id": "stream_123",
  "data": { "partial_analytics": "..." },
  "context": { "confidence": 0.8 },
  "location_data": { "gps": {...}, "cell_towers": [...] },
  "video_frame_hash": "abc123..."
}

# Get streaming decision history
GET /orchestrator/streaming-decisions/stream_123

# Register AI systems with the orchestrator
POST /orchestrator/ai-systems
{
  "system_id": "custom_ai_model",
  "capabilities": ["object_detection", "pose_estimation"],
  "weight": 0.7
}
```

### Geolocation Verification Endpoints

```bash
# Start location tracking session
POST /geolocation/session/start/user_123

# Update location with multi-source data
POST /geolocation/update
{
  "session_id": "session_456",
  "gps_data": { "lat": 40.7128, "lon": -74.0060, "accuracy": 5.0 },
  "cell_towers": [{ "tower_id": "cell_789", "signal_strength": -65 }],
  "wifi_points": [{ "bssid": "aa:bb:cc:dd:ee:ff", "signal_strength": -45 }],
  "video_frame_hash": "frame_abc123"
}

# Add exclusion zones
POST /geolocation/exclusion-zones
{
  "zone": {
    "center_lat": 40.7589, 
    "center_lon": -73.9851,
    "radius_meters": 500,
    "zone_type": "EventLocation"
  }
}

# Verify transaction location
POST /geolocation/verify-transaction
{
  "transaction_id": "tx_123",
  "user_id": "user_456", 
  "video_evidence": { "frame_hash": "...", "metadata": "..." }
}
```

### Hybrid Reasoning Endpoints

```bash
# Evaluate bet outcomes using hybrid reasoning
POST /reasoning/evaluate-bet
{
  "bet_id": "bet_123",
  "event_data": { "speed": 25.5, "pose_detected": "running" },
  "context": { "confidence": 0.9, "multiple_sources": true }
}

# Distribute prize pools with sophisticated algorithms
POST /reasoning/distribute-prize/pool_123

# Get complete reasoning trace for transparency
GET /reasoning/bet-trace/bet_123

# Update paradigm weights for tuning
PATCH /reasoning/paradigm-weights
{
  "imperative": 0.5,
  "logical": 0.3,
  "fuzzy": 0.2
}
```

## 📚 Documentation

- **[Complete Architecture Guide](docs/ARCHITECTURE.md)** - Deep technical implementation details
- **[Computer Vision Frameworks](docs/vibrio.md)** - Vibrio & Moriarty system details  
- **[Metacognitive Processing](docs/izinyoka.md)** - Three-layer biomimetic architecture
- **[Geolocation Systems](docs/sighthound.md)** - Nanosecond-precise location verification
- **[Hybrid Reasoning](docs/trebuchet.md)** - Multi-paradigm decision systems
- **[API Reference](docs/api.md)** - Complete endpoint documentation
- **[Deployment Guide](docs/deployment.md)** - Production setup and scaling

## 🧪 Research Applications

### Metacognitive Computing Research
- **Biomimetic intelligence** systems
- **Partial information** decision making
- **Multi-layer cognitive** architectures
- **Metabolic processing** cycles

### Geolocation Technology Research  
- **Nanosecond precision** timing systems
- **Multi-source fusion** algorithms
- **Real-time verification** protocols
- **Cryptographic location** binding

### Hybrid Programming Paradigms
- **Imperative-logical-fuzzy** integration
- **Multi-paradigm reasoning** systems
- **Sophisticated settlement** algorithms  
- **Transparent decision** tracing

### Computer Vision Innovation
- **Real-time biomechanical** analysis
- **Advanced object tracking** systems
- **Automated highlight** detection
- **Multi-modal sensor** fusion

## 🤝 Contributing

This is a research platform exploring advanced concepts in:
- **Biomimetic artificial intelligence**
- **Real-time computer vision**  
- **Sophisticated reasoning systems**
- **Nanosecond-precise geolocation**
- **Hybrid programming paradigms**

To contribute:

1. **Understand the vision** - Read the complete architecture documentation
2. **Set up development environment** - Use `./scripts/setup-dev.sh`
3. **Choose your focus area** - AI, geolocation, reasoning, or computer vision
4. **Follow research ethics** - All systems designed for transparency and user understanding

## 🏛️ Research Ethics & Transparency

This platform implements cutting-edge research with **complete transparency**:

- **Open-source architecture** - All systems are fully documented
- **Explainable AI** - Every decision includes reasoning traces  
- **User understanding** - No hidden algorithms or black boxes
- **Ethical constraints** - Built-in safeguards and appeal processes
- **Research focus** - Advancing human understanding of intelligent systems

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🔬 Research Vision Statement

**Morphine represents the future of intelligent platforms** - systems that don't just deliver content, but understand, reason, and make sophisticated decisions in real-time. By combining biomimetic intelligence, nanosecond-precise verification, and hybrid reasoning, we're creating a new paradigm for how technology can augment human capabilities while maintaining complete transparency and ethical operation.

This is not just a streaming platform. **This is a research platform for the future of artificial intelligence.**
