import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
import time

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aioredis
import numpy as np
import cv2
import base64

from src.frameworks.vibrio import VibrioAnalyzer
from src.frameworks.moriarty import MoriartyPipeline
from src.models.analytics import AnalyticsResult, FrameData, StreamAnalytics
from src.services.redis_service import RedisService
from src.services.stream_service import StreamService
from src.video.ingestion import VideoIngestionPipeline, StreamConfig, StreamSource

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Global components
vibrio_analyzer = None
moriarty_pipeline = None
redis_service = None
stream_service = None
video_pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global vibrio_analyzer, moriarty_pipeline, redis_service, stream_service, video_pipeline
    
    logger.info("Starting Morphine Analytics Service")
    
    # Initialize Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_service = RedisService(redis_url)
    await redis_service.connect()
    
    # Initialize Stream service
    core_url = os.getenv("CORE_SERVICE_URL", "http://localhost:8000")
    stream_service = StreamService(core_url, redis_service)
    
    # Initialize video ingestion pipeline
    video_pipeline = VideoIngestionPipeline()
    
    # Initialize Vibrio analyzer
    vibrio_analyzer = VibrioAnalyzer(
        model_path=os.getenv("YOLO_MODEL_PATH", "yolov8n.pt"),
        device="cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"
    )
    await vibrio_analyzer.initialize()
    
    # Initialize Moriarty pipeline
    moriarty_pipeline = MoriartyPipeline(
        complexity=1,
        enable_biomechanics=True
    )
    await moriarty_pipeline.initialize()
    
    logger.info("Analytics service initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down analytics service")
    if video_pipeline:
        await video_pipeline.shutdown()
    if redis_service:
        await redis_service.close()

# Create FastAPI app
app = FastAPI(
    title="Morphine Analytics Service",
    description="Computer Vision Analytics powered by Vibrio and Moriarty frameworks",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class FrameProcessRequest(BaseModel):
    stream_id: str
    frame_data: str  # Base64 encoded frame
    timestamp: float
    frame_idx: int

class AnalyticsResponse(BaseModel):
    success: bool
    analytics: Dict[str, Any]
    processing_time: float
    error: str = None

class StreamStartRequest(BaseModel):
    stream_id: str
    source_type: str = "webcam"
    source_url: str = "0"
    settings: Dict[str, Any] = {}

class HealthResponse(BaseModel):
    status: str
    vibrio_ready: bool
    moriarty_ready: bool
    redis_connected: bool
    active_streams: int
    version: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_connected = redis_service and await redis_service.ping()
    active_streams = len(video_pipeline.active_streams) if video_pipeline else 0
    
    return HealthResponse(
        status="healthy",
        vibrio_ready=vibrio_analyzer is not None,
        moriarty_ready=moriarty_pipeline is not None,
        redis_connected=redis_connected,
        active_streams=active_streams,
        version="1.0.0"
    )

@app.post("/analytics/process_frame", response_model=AnalyticsResponse)
async def process_frame(request: FrameProcessRequest):
    """Process a single frame with computer vision analytics"""
    try:
        start_time = time.time()
        
        # Decode base64 frame data
        frame_bytes = base64.b64decode(request.frame_data)
        frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise ValueError("Invalid frame data")
        
        # Process with both frameworks in parallel
        vibrio_task = vibrio_analyzer.analyze_frame(frame, request.timestamp)
        moriarty_task = moriarty_pipeline.analyze_frame(frame, request.timestamp)
        
        vibrio_result, moriarty_result = await asyncio.gather(
            vibrio_task, moriarty_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(vibrio_result, Exception):
            logger.error("Vibrio analysis failed", error=str(vibrio_result))
            vibrio_result = None
        
        if isinstance(moriarty_result, Exception):
            logger.error("Moriarty analysis failed", error=str(moriarty_result))
            moriarty_result = None
        
        processing_time = time.time() - start_time
        
        # Combine results
        analytics = AnalyticsResult(
            stream_id=request.stream_id,
            frame_idx=request.frame_idx,
            timestamp=request.timestamp,
            vibrio=vibrio_result,
            moriarty=moriarty_result,
            processing_time=processing_time
        )
        
        # Store in Redis for real-time access
        await redis_service.store_analytics(request.stream_id, analytics)
        
        # Notify core service
        await stream_service.notify_analytics_update(request.stream_id, analytics)
        
        return AnalyticsResponse(
            success=True,
            analytics=analytics.dict(),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error("Frame processing failed", error=str(e), stream_id=request.stream_id)
        return AnalyticsResponse(
            success=False,
            analytics={},
            processing_time=0.0,
            error=str(e)
        )

@app.post("/analytics/start_stream")
async def start_stream_analytics(request: StreamStartRequest):
    """Start analytics processing for a stream"""
    try:
        # Create stream configuration
        source_type_map = {
            "webcam": StreamSource.WEBCAM,
            "file": StreamSource.FILE,
            "rtmp": StreamSource.RTMP,
            "http": StreamSource.HTTP_STREAM,
            "udp": StreamSource.UDP
        }
        
        source_type = source_type_map.get(request.source_type, StreamSource.WEBCAM)
        
        config = StreamConfig(
            source_type=source_type,
            source_url=request.source_url,
            stream_id=request.stream_id,
            **request.settings
        )
        
        # Start video ingestion with analytics callback
        success = await video_pipeline.start_stream(
            config, 
            lambda stream_id, frame, frame_idx: asyncio.create_task(
                process_video_frame(stream_id, frame, frame_idx)
            )
        )
        
        if success:
            # Initialize stream analytics state
            await redis_service.initialize_stream(request.stream_id, request.settings)
            
            logger.info("Started analytics for stream", stream_id=request.stream_id)
            return {"success": True, "stream_id": request.stream_id}
        else:
            raise Exception("Failed to start video stream")
        
    except Exception as e:
        logger.error("Failed to start stream analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analytics/stop_stream/{stream_id}")
async def stop_stream_analytics(stream_id: str):
    """Stop analytics processing for a stream"""
    try:
        await video_pipeline.stop_stream(stream_id)
        await redis_service.cleanup_stream(stream_id)
        
        logger.info("Stopped analytics for stream", stream_id=stream_id)
        
        return {"success": True, "stream_id": stream_id}
        
    except Exception as e:
        logger.error("Failed to stop stream analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/{stream_id}/latest")
async def get_latest_analytics(stream_id: str):
    """Get the latest analytics for a stream"""
    try:
        analytics = await redis_service.get_latest_analytics(stream_id)
        if not analytics:
            raise HTTPException(status_code=404, detail="No analytics found for stream")
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/{stream_id}/summary")
async def get_stream_summary(stream_id: str):
    """Get analytics summary for a stream"""
    try:
        summary = await redis_service.get_stream_summary(stream_id)
        return summary
        
    except Exception as e:
        logger.error("Failed to get stream summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/{stream_id}/metrics")
async def get_stream_metrics(stream_id: str):
    """Get performance metrics for a stream"""
    try:
        summary = await redis_service.get_stream_summary(stream_id)
        
        metrics = {
            "fps": summary.get("avg_fps", 0.0),
            "detection_rate": summary.get("detection_rate", 0.0),
            "pose_detection_rate": summary.get("pose_detection_rate", 0.0),
            "error_rate": summary.get("error_rate", 0.0),
            "avg_processing_time": summary.get("avg_processing_time", 0.0),
            "total_frames": summary.get("total_frames", 0)
        }
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get stream metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/analytics/{stream_id}/settings")
async def update_stream_settings(stream_id: str, settings: Dict[str, Any]):
    """Update analytics settings for a stream"""
    try:
        # Update settings in Redis
        await redis_service.redis_client.hset(
            f"stream:{stream_id}:settings",
            mapping=settings
        )
        
        logger.info("Updated settings for stream", stream_id=stream_id, settings=settings)
        return {"success": True, "settings": settings}
        
    except Exception as e:
        logger.error("Failed to update stream settings", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{stream_id}")
async def websocket_endpoint(websocket: WebSocket, stream_id: str):
    """WebSocket endpoint for real-time analytics"""
    await websocket.accept()
    logger.info("WebSocket connected for stream", stream_id=stream_id)
    
    try:
        # Subscribe to analytics updates for this stream
        while True:
            # Get latest analytics
            analytics = await redis_service.get_latest_analytics(stream_id)
            if analytics:
                await websocket.send_json(analytics)
            
            # Wait a bit before next update
            await asyncio.sleep(0.1)  # 10 FPS update rate
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for stream", stream_id=stream_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), stream_id=stream_id)
        await websocket.close()

@app.get("/streams/active")
async def get_active_streams():
    """Get list of active streams"""
    if video_pipeline:
        return video_pipeline.list_active_streams()
    return {}

async def process_video_frame(stream_id: str, frame: np.ndarray, frame_idx: int):
    """Process a video frame from the ingestion pipeline"""
    try:
        timestamp = time.time()
        
        # Process with both frameworks
        vibrio_task = vibrio_analyzer.analyze_frame(frame, timestamp)
        moriarty_task = moriarty_pipeline.analyze_frame(frame, timestamp)
        
        vibrio_result, moriarty_result = await asyncio.gather(
            vibrio_task, moriarty_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(vibrio_result, Exception):
            logger.error("Vibrio analysis failed", error=str(vibrio_result))
            vibrio_result = None
        
        if isinstance(moriarty_result, Exception):
            logger.error("Moriarty analysis failed", error=str(moriarty_result))
            moriarty_result = None
        
        # Create analytics result
        analytics = AnalyticsResult(
            stream_id=stream_id,
            frame_idx=frame_idx,
            timestamp=timestamp,
            vibrio=vibrio_result,
            moriarty=moriarty_result,
            processing_time=time.time() - timestamp
        )
        
        # Store and notify
        await redis_service.store_analytics(stream_id, analytics)
        await stream_service.notify_analytics_update(stream_id, analytics)
        
    except Exception as e:
        logger.error("Error processing video frame", error=str(e), stream_id=stream_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True) 