---
layout: page
title: Streaming Implementation
nav_order: 4
---

# Streaming Implementation
{: .no_toc}

## Table of contents
{: .no_toc .text-delta}

1. TOC
{:toc}

---

## Overview

The Morphine Platform's streaming system is built on a high-performance Rust core that delivers ultra-low latency video streaming with integrated real-time computer vision processing. The system is designed to handle thousands of concurrent viewers while providing sub-500ms end-to-end latency.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Broadcaster   │    │   Rust Core     │    │   CV Pipeline   │    │     Viewers     │
│                 ├───►│                 ├───►│                 ├───►│                 │
│ - OBS/FFmpeg    │    │ - WebRTC Server │    │ - Vibrio        │    │ - Web Browser   │
│ - Camera Feed   │    │ - Stream Router │    │ - Moriarty      │    │ - Mobile App    │
│ - RTMP Input    │    │ - State Manager │    │ - Analytics     │    │ - Smart TV      │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Data Store    │    │   API Layer     │
                       │                 │    │                 │
                       │ - PostgreSQL    │    │ - Node.js       │
                       │ - Redis Cache   │    │ - WebSocket     │
                       │ - Time Series   │    │ - REST API      │
                       └─────────────────┘    └─────────────────┘
```

## Core Streaming Engine

### Rust WebRTC Implementation

The streaming core is implemented in Rust for maximum performance and memory safety:

```rust
use webrtc::peer_connection::RTCPeerConnection;
use webrtc::track::track_local::track_local_static_rtp::TrackLocalStaticRTP;
use tokio::sync::{Arc, RwLock};

pub struct StreamServer {
    peer_connections: Arc<RwLock<HashMap<String, RTCPeerConnection>>>,
    video_track: Arc<TrackLocalStaticRTP>,
    analytics_sender: mpsc::Sender<FrameAnalytics>,
}

impl StreamServer {
    pub async fn new() -> Result<Self> {
        // Initialize WebRTC configuration
        let config = RTCConfiguration {
            ice_servers: vec![RTCIceServer {
                urls: vec!["stun:stun.l.google.com:19302".to_owned()],
                ..Default::default()
            }],
            ..Default::default()
        };

        // Create video track for streaming
        let video_track = Arc::new(TrackLocalStaticRTP::new(
            RTCRtpCodecCapability {
                mime_type: MIME_TYPE_H264.to_owned(),
                ..Default::default()
            },
            "video".to_owned(),
            "morphine-stream".to_owned(),
        ));

        Ok(StreamServer {
            peer_connections: Arc::new(RwLock::new(HashMap::new())),
            video_track,
            analytics_sender: setup_analytics_channel().await?,
        })
    }

    pub async fn add_viewer(&self, viewer_id: String) -> Result<RTCSessionDescription> {
        let peer_connection = RTCPeerConnection::new(&self.config).await?;
        
        // Add video track to peer connection
        peer_connection.add_track(Arc::clone(&self.video_track)).await?;
        
        // Setup data channel for analytics
        let data_channel = peer_connection.create_data_channel(
            "analytics",
            Some(RTCDataChannelInit {
                ordered: Some(true),
                ..Default::default()
            }),
        ).await?;
        
        // Store peer connection
        {
            let mut connections = self.peer_connections.write().await;
            connections.insert(viewer_id.clone(), peer_connection.clone());
        }
        
        // Create offer
        let offer = peer_connection.create_offer(None).await?;
        peer_connection.set_local_description(offer.clone()).await?;
        
        Ok(offer)
    }

    pub async fn process_frame(&self, frame: Vec<u8>, timestamp: u64) -> Result<()> {
        // Send frame to computer vision pipeline
        let analytics_task = self.send_to_analytics(frame.clone(), timestamp);
        
        // Encode and send to viewers
        let streaming_task = self.broadcast_frame(frame, timestamp);
        
        // Execute in parallel
        tokio::try_join!(analytics_task, streaming_task)?;
        
        Ok(())
    }

    async fn broadcast_frame(&self, frame: Vec<u8>, timestamp: u64) -> Result<()> {
        let packet = rtp::packet::Packet {
            header: rtp::header::Header {
                timestamp,
                sequence_number: self.get_next_sequence_number(),
                payload_type: 96, // H264 payload type
                ..Default::default()
            },
            payload: frame.into(),
        };

        // Send to all connected viewers
        let connections = self.peer_connections.read().await;
        let futures: Vec<_> = connections.values()
            .map(|pc| self.video_track.write_rtp(&packet))
            .collect();
        
        futures::future::try_join_all(futures).await?;
        
        Ok(())
    }
}
```

### Stream Processing Pipeline

```rust
use crate::analytics::{VibrioProcessor, MoriartyProcessor};

pub struct StreamProcessor {
    input_receiver: mpsc::Receiver<StreamFrame>,
    output_sender: mpsc::Sender<ProcessedFrame>,
    vibrio: VibrioProcessor,
    moriarty: MoriartyProcessor,
}

impl StreamProcessor {
    pub async fn process_stream(&mut self) -> Result<()> {
        while let Some(frame) = self.input_receiver.recv().await {
            let start_time = Instant::now();
            
            // Parallel CV processing
            let (vibrio_result, moriarty_result) = tokio::join!(
                self.vibrio.process_frame(&frame.data),
                self.moriarty.analyze_frame(&frame.data)
            );
            
            let processed_frame = ProcessedFrame {
                original: frame,
                vibrio_analytics: vibrio_result?,
                moriarty_analytics: moriarty_result?,
                processing_time: start_time.elapsed(),
                timestamp: SystemTime::now(),
            };
            
            // Send to output
            self.output_sender.send(processed_frame).await?;
            
            // Log performance metrics
            tracing::info!(
                "Frame processed in {:?}ms",
                start_time.elapsed().as_millis()
            );
        }
        
        Ok(())
    }
}
```

## Low-Latency Design

### Performance Targets

| Metric | Target | Implementation |
|--------|--------|---------------|
| **End-to-End Latency** | < 500ms | WebRTC + optimized encoding |
| **CV Processing** | < 100ms | GPU acceleration + async |
| **Stream Ingestion** | < 50ms | Direct H264 passthrough |
| **Viewer Connection** | < 200ms | ICE optimization |
| **Analytics Update** | < 20ms | WebSocket push |

### Optimization Techniques

#### 1. Zero-Copy Operations

```rust
use bytes::{Buf, BufMut, BytesMut};

pub struct FrameBuffer {
    buffer: BytesMut,
    capacity: usize,
}

impl FrameBuffer {
    pub fn new(capacity: usize) -> Self {
        Self {
            buffer: BytesMut::with_capacity(capacity),
            capacity,
        }
    }
    
    // Zero-copy frame extraction
    pub fn extract_frame(&mut self, size: usize) -> Option<bytes::Bytes> {
        if self.buffer.len() >= size {
            Some(self.buffer.split_to(size).freeze())
        } else {
            None
        }
    }
    
    // Zero-copy frame insertion
    pub fn append_data(&mut self, data: &[u8]) -> Result<()> {
        if self.buffer.remaining_mut() >= data.len() {
            self.buffer.put(data);
            Ok(())
        } else {
            Err(BufferOverflowError)
        }
    }
}
```

#### 2. Adaptive Bitrate Streaming

```rust
pub struct AdaptiveBitrateController {
    target_latency: Duration,
    current_bitrate: u32,
    viewer_stats: HashMap<String, ViewerStats>,
}

impl AdaptiveBitrateController {
    pub fn adjust_bitrate(&mut self, stats: &StreamStats) -> u32 {
        let latency_factor = if stats.avg_latency > self.target_latency {
            0.8 // Reduce bitrate to improve latency
        } else {
            1.2 // Increase bitrate for better quality
        };
        
        let bandwidth_factor = stats.available_bandwidth as f32 / stats.target_bandwidth as f32;
        
        let new_bitrate = (self.current_bitrate as f32 * latency_factor * bandwidth_factor) as u32;
        
        self.current_bitrate = new_bitrate.clamp(500_000, 10_000_000); // 500kbps - 10Mbps
        self.current_bitrate
    }
}
```

## Integration with Computer Vision

### Real-Time Analytics Pipeline

```rust
use crate::cv::{VibrioAnalyzer, MoriartyAnalyzer};

pub struct CVIntegratedStream {
    stream_processor: StreamProcessor,
    analytics_buffer: CircularBuffer<AnalyticsFrame>,
    websocket_broadcaster: WebSocketBroadcaster,
}

impl CVIntegratedStream {
    pub async fn process_with_analytics(&mut self, frame: StreamFrame) -> Result<()> {
        // Start streaming immediately (don't wait for CV)
        let streaming_task = self.stream_processor.broadcast_frame(frame.clone());
        
        // Process with CV in parallel
        let analytics_task = async {
            let vibrio_result = self.vibrio.analyze_frame(&frame.data).await?;
            let moriarty_result = self.moriarty.analyze_frame(&frame.data).await?;
            
            let analytics = AnalyticsFrame {
                frame_id: frame.id,
                timestamp: frame.timestamp,
                vibrio: vibrio_result,
                moriarty: moriarty_result,
            };
            
            // Buffer analytics for betting system
            self.analytics_buffer.push(analytics.clone());
            
            // Broadcast to viewers via WebSocket
            self.websocket_broadcaster.broadcast_analytics(analytics).await?;
            
            Ok::<(), Error>(())
        };
        
        // Execute both tasks
        tokio::try_join!(streaming_task, analytics_task)?;
        
        Ok(())
    }
}
```

### Analytics Data Flow

```
Video Frame → Stream Broadcast → Viewers (WebRTC)
     ↓
CV Processing → Analytics Buffer → Betting System
     ↓
WebSocket Push → Frontend Updates → UI Overlays
```

## Viewer Experience

### Frontend Implementation

```typescript
// WebRTC streaming client
class MorphineStreamClient {
  private peerConnection: RTCPeerConnection;
  private websocket: WebSocket;
  private analyticsCallbacks: Map<string, Function> = new Map();

  constructor(streamId: string) {
    this.setupWebRTC();
    this.setupAnalytics(streamId);
  }

  private async setupWebRTC() {
    this.peerConnection = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    });

    // Handle incoming video stream
    this.peerConnection.ontrack = (event) => {
      const videoElement = document.getElementById('stream-video') as HTMLVideoElement;
      videoElement.srcObject = event.streams[0];
    };

    // Setup analytics data channel
    this.peerConnection.ondatachannel = (event) => {
      const channel = event.channel;
      channel.onmessage = (event) => {
        const analytics = JSON.parse(event.data);
        this.handleAnalytics(analytics);
      };
    };
  }

  private setupAnalytics(streamId: string) {
    this.websocket = new WebSocket(`wss://api.morphine.com/stream/${streamId}/analytics`);
    
    this.websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'detection':
          this.updateDetectionOverlay(data.payload);
          break;
        case 'pose':
          this.updatePoseOverlay(data.payload);
          break;
        case 'speed':
          this.updateSpeedMetrics(data.payload);
          break;
        case 'betting_opportunity':
          this.showBettingInterface(data.payload);
          break;
      }
    };
  }

  public async startStream(): Promise<void> {
    try {
      // Create offer
      const offer = await this.peerConnection.createOffer();
      await this.peerConnection.setLocalDescription(offer);
      
      // Send offer to server
      const response = await fetch('/api/stream/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offer: offer.sdp })
      });
      
      const { answer } = await response.json();
      
      // Set remote description
      await this.peerConnection.setRemoteDescription({
        type: 'answer',
        sdp: answer
      });
      
    } catch (error) {
      console.error('Failed to start stream:', error);
      throw error;
    }
  }
}
```

---

## Next Steps

- [Micro-Betting System](/micro-betting) - Learn how streaming integrates with betting
- [Computer Vision Deep Dive](/computer-vision) - Understand the CV integration
- [API Reference](/api-reference) - Explore streaming APIs
- [Getting Started](/getting-started) - Set up the streaming system locally 