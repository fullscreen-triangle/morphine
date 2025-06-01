import cv2
import numpy as np
import asyncio
import aiohttp
import threading
from typing import Optional, Callable, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import tempfile
import subprocess

logger = logging.getLogger(__name__)

class StreamSource(Enum):
    RTMP = "rtmp"
    WEBRTC = "webrtc"
    WEBCAM = "webcam"
    FILE = "file"
    HTTP_STREAM = "http"
    UDP = "udp"

@dataclass
class StreamConfig:
    source_type: StreamSource
    source_url: str
    stream_id: str
    fps: int = 30
    width: Optional[int] = None
    height: Optional[int] = None
    quality: str = "1080p"
    buffer_size: int = 10
    reconnect_attempts: int = 5
    reconnect_delay: float = 2.0

class VideoIngestionPipeline:
    """Video ingestion pipeline supporting multiple input sources"""
    
    def __init__(self):
        self.active_streams: Dict[str, 'StreamHandler'] = {}
        self.frame_callbacks: Dict[str, Callable] = {}
        
    async def start_stream(self, config: StreamConfig, frame_callback: Callable[[str, np.ndarray, int], None]) -> bool:
        """
        Start ingesting video from a stream source
        
        Args:
            config: Stream configuration
            frame_callback: Callback function for processing frames (stream_id, frame, frame_idx)
            
        Returns:
            True if stream started successfully
        """
        if config.stream_id in self.active_streams:
            logger.warning(f"Stream {config.stream_id} is already active")
            return False
        
        try:
            handler = StreamHandler(config, frame_callback)
            success = await handler.start()
            
            if success:
                self.active_streams[config.stream_id] = handler
                self.frame_callbacks[config.stream_id] = frame_callback
                logger.info(f"Started stream ingestion for {config.stream_id}")
                return True
            else:
                logger.error(f"Failed to start stream {config.stream_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting stream {config.stream_id}: {e}")
            return False
    
    async def stop_stream(self, stream_id: str) -> bool:
        """Stop a video stream"""
        if stream_id not in self.active_streams:
            logger.warning(f"Stream {stream_id} is not active")
            return False
        
        try:
            handler = self.active_streams[stream_id]
            await handler.stop()
            
            del self.active_streams[stream_id]
            del self.frame_callbacks[stream_id]
            
            logger.info(f"Stopped stream ingestion for {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {e}")
            return False
    
    def get_stream_stats(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a stream"""
        if stream_id not in self.active_streams:
            return None
        
        return self.active_streams[stream_id].get_stats()
    
    def list_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """List all active streams with their stats"""
        return {
            stream_id: handler.get_stats()
            for stream_id, handler in self.active_streams.items()
        }
    
    async def shutdown(self):
        """Shutdown all streams"""
        for stream_id in list(self.active_streams.keys()):
            await self.stop_stream(stream_id)

class StreamHandler:
    """Handles individual stream processing"""
    
    def __init__(self, config: StreamConfig, frame_callback: Callable):
        self.config = config
        self.frame_callback = frame_callback
        self.capture: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.frame_count = 0
        self.error_count = 0
        self.last_frame_time = 0
        self.processing_thread: Optional[threading.Thread] = None
        
    async def start(self) -> bool:
        """Start the stream handler"""
        try:
            success = await self._initialize_capture()
            if not success:
                return False
            
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)
            self.processing_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stream handler: {e}")
            return False
    
    async def stop(self):
        """Stop the stream handler"""
        self.is_running = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        if self.capture:
            self.capture.release()
            self.capture = None
    
    async def _initialize_capture(self) -> bool:
        """Initialize the video capture based on source type"""
        try:
            if self.config.source_type == StreamSource.WEBCAM:
                # Webcam capture
                device_id = int(self.config.source_url) if self.config.source_url.isdigit() else 0
                self.capture = cv2.VideoCapture(device_id)
                
            elif self.config.source_type == StreamSource.FILE:
                # File capture
                if not Path(self.config.source_url).exists():
                    logger.error(f"Video file not found: {self.config.source_url}")
                    return False
                self.capture = cv2.VideoCapture(self.config.source_url)
                
            elif self.config.source_type == StreamSource.RTMP:
                # RTMP stream
                self.capture = cv2.VideoCapture(self.config.source_url)
                
            elif self.config.source_type == StreamSource.HTTP_STREAM:
                # HTTP stream (IP cameras, etc.)
                self.capture = cv2.VideoCapture(self.config.source_url)
                
            elif self.config.source_type == StreamSource.UDP:
                # UDP stream
                self.capture = cv2.VideoCapture(self.config.source_url)
                
            elif self.config.source_type == StreamSource.WEBRTC:
                # WebRTC would require specialized handling
                logger.warning("WebRTC source type not yet implemented")
                return False
            
            if not self.capture or not self.capture.isOpened():
                logger.error(f"Failed to open capture for {self.config.source_url}")
                return False
            
            # Set capture properties
            if self.config.width and self.config.height:
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            
            self.capture.set(cv2.CAP_PROP_FPS, self.config.fps)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)
            
            # Log capture properties
            width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Initialized capture: {width}x{height} @ {fps} FPS")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing capture: {e}")
            return False
    
    def _process_frames(self):
        """Process frames in a separate thread"""
        reconnect_attempts = 0
        
        while self.is_running:
            try:
                if not self.capture or not self.capture.isOpened():
                    if reconnect_attempts < self.config.reconnect_attempts:
                        logger.info(f"Attempting to reconnect stream {self.config.stream_id} (attempt {reconnect_attempts + 1})")
                        asyncio.run(self._initialize_capture())
                        reconnect_attempts += 1
                        continue
                    else:
                        logger.error(f"Max reconnection attempts reached for stream {self.config.stream_id}")
                        break
                
                ret, frame = self.capture.read()
                
                if not ret:
                    self.error_count += 1
                    logger.warning(f"Failed to read frame from stream {self.config.stream_id}")
                    
                    # For file sources, this might be end of file
                    if self.config.source_type == StreamSource.FILE:
                        logger.info(f"End of file reached for {self.config.stream_id}")
                        break
                    
                    # For live streams, attempt reconnection
                    if reconnect_attempts < self.config.reconnect_attempts:
                        reconnect_attempts += 1
                        asyncio.run(asyncio.sleep(self.config.reconnect_delay))
                        continue
                    else:
                        break
                
                # Reset reconnection counter on successful frame
                reconnect_attempts = 0
                
                # Process frame
                self.frame_count += 1
                self.last_frame_time = cv2.getTickCount() / cv2.getTickFrequency()
                
                # Apply quality/resize if needed
                if self.config.quality == "720p" and frame.shape[0] > 720:
                    frame = cv2.resize(frame, (1280, 720))
                elif self.config.quality == "1080p" and frame.shape[0] > 1080:
                    frame = cv2.resize(frame, (1920, 1080))
                elif self.config.quality == "4K" and frame.shape[0] > 2160:
                    frame = cv2.resize(frame, (3840, 2160))
                
                # Call frame callback
                try:
                    self.frame_callback(self.config.stream_id, frame, self.frame_count)
                except Exception as e:
                    logger.error(f"Error in frame callback for stream {self.config.stream_id}: {e}")
                
                # Frame rate control
                expected_delay = 1.0 / self.config.fps
                current_time = cv2.getTickCount() / cv2.getTickFrequency()
                processing_time = current_time - self.last_frame_time
                
                if processing_time < expected_delay:
                    time.sleep(expected_delay - processing_time)
                
            except Exception as e:
                logger.error(f"Error processing frame for stream {self.config.stream_id}: {e}")
                self.error_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stream statistics"""
        current_time = cv2.getTickCount() / cv2.getTickFrequency()
        uptime = current_time - self.last_frame_time if self.last_frame_time > 0 else 0
        
        return {
            "stream_id": self.config.stream_id,
            "source_type": self.config.source_type.value,
            "source_url": self.config.source_url,
            "is_running": self.is_running,
            "frame_count": self.frame_count,
            "error_count": self.error_count,
            "uptime": uptime,
            "fps": self.config.fps,
            "quality": self.config.quality
        }

class RTMPServer:
    """Simple RTMP server for receiving streams"""
    
    def __init__(self, port: int = 1935):
        self.port = port
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        
    async def start_server(self, output_dir: str = "/tmp/morphine_streams"):
        """Start RTMP server using FFmpeg"""
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # FFmpeg command for RTMP server
            cmd = [
                "ffmpeg",
                "-listen", "1",
                "-f", "flv",
                "-i", f"rtmp://0.0.0.0:{self.port}/live/stream",
                "-c", "copy",
                "-f", "segment",
                "-segment_time", "10",
                "-segment_format", "mp4",
                f"{output_dir}/stream_%03d.mp4"
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"RTMP server started on port {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start RTMP server: {e}")
            return False
    
    async def stop_server(self):
        """Stop RTMP server"""
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            logger.info("RTMP server stopped")

# Convenience functions
async def create_webcam_stream(stream_id: str, device_id: int = 0, fps: int = 30) -> StreamConfig:
    """Create webcam stream configuration"""
    return StreamConfig(
        source_type=StreamSource.WEBCAM,
        source_url=str(device_id),
        stream_id=stream_id,
        fps=fps
    )

async def create_file_stream(stream_id: str, file_path: str, fps: int = 30) -> StreamConfig:
    """Create file stream configuration"""
    return StreamConfig(
        source_type=StreamSource.FILE,
        source_url=file_path,
        stream_id=stream_id,
        fps=fps
    )

async def create_rtmp_stream(stream_id: str, rtmp_url: str, fps: int = 30) -> StreamConfig:
    """Create RTMP stream configuration"""
    return StreamConfig(
        source_type=StreamSource.RTMP,
        source_url=rtmp_url,
        stream_id=stream_id,
        fps=fps
    ) 