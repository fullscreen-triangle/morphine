import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aioredis
import numpy as np
import cv2
from ultralytics import YOLO

from frameworks.vibrio import VibrioAnalyzer
from frameworks.moriarty import MoriartyPipeline
from models.analytics import AnalyticsResult, FrameData, StreamAnalytics
from services.redis_service import RedisService
from services.stream_service import StreamService

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global vibrio_analyzer, moriarty_pipeline, redis_service, stream_service
    
    logger.info("Starting Morphine Analytics Service")
    
    # Initialize Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_service = RedisService(redis_url)
    await redis_service.connect()
    
    # Initialize Stream service
    core_url = os.getenv("CORE_SERVICE_URL", "http://localhost:3001")
    stream_service = StreamService(core_url, redis_service)
    
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
    frame_data: bytes
    timestamp: float
    frame_idx: int

class AnalyticsResponse(BaseModel):
    success: bool
    analytics: Dict[str, Any]
    processing_time: float
    error: str = None

class StreamStartRequest(BaseModel):
    stream_id: str
    settings: Dict[str, Any] = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "vibrio_ready": vibrio_analyzer is not None,
        "moriarty_ready": moriarty_pipeline is not None,
        "redis_connected": redis_service and await redis_service.ping()
    }

@app.post("/analytics/process_frame", response_model=AnalyticsResponse)
async def process_frame(request: FrameProcessRequest):
    """Process a single frame with computer vision analytics"""
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Decode frame data
        frame_array = np.frombuffer(request.frame_data, dtype=np.uint8)
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
        
        # Combine results
        analytics = AnalyticsResult(
            stream_id=request.stream_id,
            frame_idx=request.frame_idx,
            timestamp=request.timestamp,
            vibrio=vibrio_result,
            moriarty=moriarty_result,
            processing_time=asyncio.get_event_loop().time() - start_time
        )
        
        # Store in Redis for real-time access
        await redis_service.store_analytics(request.stream_id, analytics)
        
        # Notify core service
        await stream_service.notify_analytics_update(request.stream_id, analytics)
        
        return AnalyticsResponse(
            success=True,
            analytics=analytics.dict(),
            processing_time=analytics.processing_time
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
        # Initialize stream analytics state
        await redis_service.initialize_stream(request.stream_id, request.settings)
        
        # Start background processing
        await stream_service.start_stream_processing(request.stream_id)
        
        logger.info("Started analytics for stream", stream_id=request.stream_id)
        
        return {"success": True, "stream_id": request.stream_id}
        
    except Exception as e:
        logger.error("Failed to start stream analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analytics/stop_stream/{stream_id}")
async def stop_stream_analytics(stream_id: str):
    """Stop analytics processing for a stream"""
    try:
        await stream_service.stop_stream_processing(stream_id)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 