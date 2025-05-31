---
layout: page
title: API Reference
nav_order: 7
---

<div class="page-logo">
  <img src="assets/Morphine2DCSDS.svg" alt="Morphine Chemical Structure" class="page-logo-img">
</div>

# API Reference
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

1. TOC
{:toc}

---

## Overview

The Morphine Platform provides comprehensive REST and WebSocket APIs for streaming, computer vision analytics, and micro-betting functionality. All APIs use JSON for data exchange and include detailed error handling.

**Base URLs:**
- REST API: `https://api.morphine.com/v1`
- WebSocket: `wss://ws.morphine.com/v1`
- Streaming: `https://stream.morphine.com`

## Authentication

All API endpoints require authentication using JWT tokens.

### Obtain Access Token

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "balance": 100.00
  }
}
```

### Using Authentication

Include the JWT token in the Authorization header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Streaming API

### Stream Management

#### Create Stream

```http
POST /streams
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Live Sports Event",
  "description": "Real-time analysis of football match",
  "settings": {
    "enable_cv": true,
    "enable_betting": true,
    "quality": "1080p"
  }
}
```

**Response:**
```json
{
  "stream_id": "stream_abc123",
  "ingest_url": "rtmp://ingest.morphine.com/live/stream_abc123",
  "playback_url": "https://stream.morphine.com/watch/stream_abc123",
  "status": "ready",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Get Stream Info

```http
GET /streams/{stream_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "stream_id": "stream_abc123",
  "title": "Live Sports Event",
  "status": "live",
  "viewer_count": 1247,
  "duration": 3600,
  "settings": {
    "enable_cv": true,
    "enable_betting": true,
    "quality": "1080p"
  },
  "analytics": {
    "total_detections": 15432,
    "average_speed": 18.5,
    "active_bets": 89
  }
}
```

#### List Active Streams

```http
GET /streams?status=live&limit=20&offset=0
Authorization: Bearer {token}
```

**Response:**
```json
{
  "streams": [
    {
      "stream_id": "stream_abc123",
      "title": "Live Sports Event",
      "viewer_count": 1247,
      "status": "live",
      "thumbnail": "https://cdn.morphine.com/thumbs/stream_abc123.jpg"
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

### Stream Control

#### Start Stream

```http
POST /streams/{stream_id}/start
Authorization: Bearer {token}
```

#### Stop Stream

```http
POST /streams/{stream_id}/stop
Authorization: Bearer {token}
```

#### Update Stream Settings

```http
PATCH /streams/{stream_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "settings": {
    "enable_betting": false,
    "quality": "720p"
  }
}
```

## Computer Vision API

### Analytics Endpoints

#### Get Live Analytics

```http
GET /analytics/{stream_id}/live
Authorization: Bearer {token}
```

**Response:**
```json
{
  "stream_id": "stream_abc123",
  "timestamp": "2024-01-15T10:30:15Z",
  "vibrio_results": {
    "detections": [
      {
        "track_id": "person_1",
        "bbox": {
          "x": 100,
          "y": 150,
          "width": 80,
          "height": 200
        },
        "confidence": 0.95,
        "speed": 25.3,
        "direction": "northeast"
      }
    ],
    "optical_flow": {
      "magnitude": 12.5,
      "dominant_direction": 45.2
    }
  },
  "moriarty_results": {
    "poses": [
      {
        "person_id": "person_1",
        "landmarks": [
          {
            "name": "nose",
            "x": 140,
            "y": 160,
            "confidence": 0.98
          }
        ],
        "joint_angles": {
          "knee_left": 145.2,
          "knee_right": 142.8
        }
      }
    ],
    "biomechanics": {
      "stride_length": 2.45,
      "stride_frequency": 3.2,
      "ground_reaction_force": [850, 1200]
    }
  }
}
```

#### Get Historical Analytics

```http
GET /analytics/{stream_id}/history?start_time=2024-01-15T10:00:00Z&end_time=2024-01-15T11:00:00Z&metrics=speed,pose
Authorization: Bearer {token}
```

**Response:**
```json
{
  "data": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "metrics": {
        "speed": {
          "average": 18.5,
          "max": 28.1,
          "detections": 15
        },
        "pose": {
          "poses_detected": 3,
          "average_confidence": 0.87
        }
      }
    }
  ],
  "summary": {
    "total_frames": 3600,
    "processing_rate": 29.5,
    "accuracy": 0.94
  }
}
```

#### Export Analytics Data

```http
POST /analytics/{stream_id}/export
Authorization: Bearer {token}
Content-Type: application/json

{
  "format": "csv",
  "metrics": ["speed", "pose", "detections"],
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T11:00:00Z"
}
```

**Response:**
```json
{
  "export_id": "export_xyz789",
  "status": "processing",
  "estimated_completion": "2024-01-15T10:35:00Z",
  "download_url": null
}
```

### Model Management

#### List Available Models

```http
GET /models
Authorization: Bearer {token}
```

**Response:**
```json
{
  "models": [
    {
      "id": "yolov8_person",
      "name": "YOLOv8 Person Detection",
      "type": "detection",
      "framework": "vibrio",
      "accuracy": 0.94,
      "speed": "30 FPS"
    },
    {
      "id": "blazepose_33",
      "name": "BlazePose 33-point",
      "type": "pose_estimation",
      "framework": "moriarty",
      "accuracy": 0.91,
      "speed": "25 FPS"
    }
  ]
}
```

#### Update Model Configuration

```http
POST /analytics/{stream_id}/models
Authorization: Bearer {token}
Content-Type: application/json

{
  "detection_model": "yolov8_person",
  "pose_model": "blazepose_33",
  "settings": {
    "detection_threshold": 0.6,
    "pose_complexity": 1
  }
}
```

## Betting API

### Betting Opportunities

#### Get Active Opportunities

```http
GET /betting/{stream_id}/opportunities
Authorization: Bearer {token}
```

**Response:**
```json
{
  "opportunities": [
    {
      "bet_id": "bet_123",
      "type": "speed",
      "description": "Next speed > 25 km/h",
      "odds": 2.4,
      "expires_at": "2024-01-15T10:31:00Z",
      "min_stake": 1.0,
      "max_stake": 100.0,
      "context": {
        "current_speed": 18.5,
        "target_threshold": 25.0,
        "time_window": 10
      }
    },
    {
      "bet_id": "bet_124",
      "type": "action",
      "description": "Jump in next 15 seconds",
      "odds": 3.2,
      "expires_at": "2024-01-15T10:30:45Z",
      "min_stake": 1.0,
      "max_stake": 50.0,
      "context": {
        "action_type": "jump",
        "probability": 0.31,
        "time_window": 15
      }
    }
  ]
}
```

#### Place Bet

```http
POST /betting/bets
Authorization: Bearer {token}
Content-Type: application/json

{
  "bet_id": "bet_123",
  "stake": 10.0,
  "stream_id": "stream_abc123"
}
```

**Response:**
```json
{
  "bet_confirmation": {
    "id": "confirmation_xyz789",
    "bet_id": "bet_123",
    "stake": 10.0,
    "potential_payout": 24.0,
    "status": "active",
    "placed_at": "2024-01-15T10:30:25Z",
    "expires_at": "2024-01-15T10:31:00Z"
  },
  "updated_balance": 90.0
}
```

### Bet Management

#### Get User Bets

```http
GET /betting/bets?status=active&stream_id=stream_abc123
Authorization: Bearer {token}
```

**Response:**
```json
{
  "bets": [
    {
      "id": "confirmation_xyz789",
      "bet_id": "bet_123",
      "description": "Next speed > 25 km/h",
      "stake": 10.0,
      "potential_payout": 24.0,
      "status": "active",
      "placed_at": "2024-01-15T10:30:25Z",
      "expires_at": "2024-01-15T10:31:00Z"
    }
  ]
}
```

#### Get Bet History

```http
GET /betting/history?limit=50&offset=0
Authorization: Bearer {token}
```

**Response:**
```json
{
  "bets": [
    {
      "id": "confirmation_abc456",
      "description": "Player enters penalty box",
      "stake": 5.0,
      "payout": 0.0,
      "status": "lost",
      "placed_at": "2024-01-15T09:45:12Z",
      "resolved_at": "2024-01-15T09:46:30Z",
      "evidence": {
        "type": "position",
        "final_position": "midfield",
        "target_zone": "penalty_box"
      }
    }
  ],
  "summary": {
    "total_bets": 156,
    "total_staked": 450.0,
    "total_winnings": 380.0,
    "win_rate": 0.42
  }
}
```

### Balance Management

#### Get Balance

```http
GET /user/balance
Authorization: Bearer {token}
```

**Response:**
```json
{
  "balance": 95.50,
  "currency": "USD",
  "pending_bets": 15.0,
  "available": 80.50,
  "last_updated": "2024-01-15T10:30:25Z"
}
```

#### Add Funds

```http
POST /user/balance/add
Authorization: Bearer {token}
Content-Type: application/json

{
  "amount": 50.0,
  "payment_method": "credit_card",
  "payment_token": "pm_1abc123"
}
```

## WebSocket API

### Connection

Connect to the WebSocket endpoint with authentication:

```javascript
const ws = new WebSocket('wss://ws.morphine.com/v1?token=your_jwt_token');
```

### Message Format

All WebSocket messages follow this format:

```json
{
  "type": "message_type",
  "stream_id": "stream_abc123",
  "timestamp": "2024-01-15T10:30:25Z",
  "data": {
    // Message-specific data
  }
}
```

### Subscription Management

#### Subscribe to Stream

```json
{
  "type": "subscribe",
  "stream_id": "stream_abc123",
  "events": ["analytics", "betting", "chat"]
}
```

#### Unsubscribe from Stream

```json
{
  "type": "unsubscribe",
  "stream_id": "stream_abc123"
}
```

### Real-time Events

#### Analytics Updates

```json
{
  "type": "analytics_update",
  "stream_id": "stream_abc123",
  "timestamp": "2024-01-15T10:30:25Z",
  "data": {
    "detections": [
      {
        "track_id": "person_1",
        "speed": 26.3,
        "bbox": [100, 150, 80, 200]
      }
    ],
    "frame_id": 54321
  }
}
```

#### New Betting Opportunity

```json
{
  "type": "betting_opportunity",
  "stream_id": "stream_abc123",
  "timestamp": "2024-01-15T10:30:25Z",
  "data": {
    "bet_id": "bet_125",
    "type": "speed",
    "description": "Next speed > 30 km/h",
    "odds": 3.5,
    "expires_at": "2024-01-15T10:31:25Z"
  }
}
```

#### Bet Resolution

```json
{
  "type": "bet_resolved",
  "stream_id": "stream_abc123",
  "timestamp": "2024-01-15T10:31:00Z",
  "data": {
    "bet_id": "bet_123",
    "outcome": "win",
    "payout": 24.0,
    "evidence": {
      "measured_speed": 27.8,
      "threshold": 25.0,
      "timestamp": "2024-01-15T10:30:58Z"
    }
  }
}
```

#### Chat Messages

```json
{
  "type": "chat_message",
  "stream_id": "stream_abc123",
  "timestamp": "2024-01-15T10:30:25Z",
  "data": {
    "user_id": "user_456",
    "username": "SportsFan2024",
    "message": "Great analysis on that last play!",
    "message_id": "msg_789"
  }
}
```

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Not Found |
| `429` | Rate Limited |
| `500` | Internal Server Error |

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_STREAM_ID",
    "message": "The specified stream ID does not exist",
    "details": {
      "stream_id": "invalid_stream_123",
      "suggestions": ["Check stream ID format", "Verify stream exists"]
    }
  },
  "request_id": "req_abc123",
  "timestamp": "2024-01-15T10:30:25Z"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `INVALID_TOKEN` | JWT token is invalid or expired |
| `INSUFFICIENT_BALANCE` | User balance too low for operation |
| `STREAM_NOT_FOUND` | Stream ID does not exist |
| `BET_EXPIRED` | Betting opportunity has expired |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `MODEL_NOT_AVAILABLE` | Requested CV model not available |

## Rate Limiting

The API implements rate limiting to ensure fair usage:

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Streaming | 100 requests | 1 minute |
| Analytics | 1000 requests | 1 minute |
| Betting | 50 requests | 1 minute |
| WebSocket | 10 connections | Per user |

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1642248625
```

## SDKs and Libraries

### JavaScript/TypeScript

```bash
npm install @morphine/sdk
```

```typescript
import { MorphineClient } from '@morphine/sdk';

const client = new MorphineClient({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.morphine.com/v1'
});

// Get stream analytics
const analytics = await client.analytics.getLive('stream_abc123');

// Place a bet
const bet = await client.betting.placeBet({
  betId: 'bet_123',
  stake: 10.0
});
```

### Python

```bash
pip install morphine-sdk
```

```python
from morphine import MorphineClient

client = MorphineClient(api_key='your_api_key')

# Get stream info
stream = client.streams.get('stream_abc123')

# Subscribe to analytics
analytics_stream = client.analytics.subscribe('stream_abc123')
for analytics in analytics_stream:
    print(f"Speed detected: {analytics.speed}")
```

### Rust

```toml
[dependencies]
morphine-sdk = "0.1.0"
```

```rust
use morphine_sdk::MorphineClient;

let client = MorphineClient::new("your_api_key").await?;

// Create stream
let stream = client.streams().create(CreateStreamRequest {
    title: "My Stream".to_string(),
    enable_cv: true,
}).await?;
```

---

## Support

For API support and questions:

- **Documentation**: [https://docs.morphine.com](https://docs.morphine.com)
- **Discord**: [https://discord.gg/morphine](https://discord.gg/morphine)
- **Email**: [api-support@morphine.com](mailto:api-support@morphine.com)
- **GitHub Issues**: [https://github.com/your-username/morphine/issues](https://github.com/your-username/morphine/issues) 