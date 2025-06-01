'use client';

import React, { useState, useEffect, useRef } from 'react';
import ReactPlayer from 'react-player';

interface StreamDashboardProps {
  stream: any;
  analytics: any;
  onAnalyticsUpdate: (analytics: any) => void;
}

export const StreamDashboard: React.FC<StreamDashboardProps> = ({ 
  stream, 
  analytics, 
  onAnalyticsUpdate 
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [currentFrame, setCurrentFrame] = useState(null);
  const [detections, setDetections] = useState([]);
  const [poseData, setPoseData] = useState(null);
  const [streamStats, setStreamStats] = useState({
    fps: 0,
    latency: 0,
    bitrate: 0
  });
  const wsRef = useRef<WebSocket | null>(null);
  const playerRef = useRef(null);

  useEffect(() => {
    if (stream?.id) {
      connectToAnalytics();
      return () => disconnectFromAnalytics();
    }
  }, [stream?.id]);

  const connectToAnalytics = () => {
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/${stream.id}`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      console.log('Connected to analytics websocket');
    };

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'analytics') {
          setDetections(data.vibrio?.detections || []);
          setPoseData(data.moriarty?.pose || null);
          onAnalyticsUpdate(data);
        } else if (data.type === 'frame') {
          setCurrentFrame(data.frame_data);
        } else if (data.type === 'stats') {
          setStreamStats(data.stats);
        }
      } catch (error) {
        console.error('Failed to parse websocket message:', error);
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      console.log('Disconnected from analytics websocket');
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
  };

  const disconnectFromAnalytics = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const renderDetectionOverlay = () => {
    if (!detections.length) return null;

    return (
      <div className="absolute inset-0 pointer-events-none">
        {detections.map((detection, idx) => (
          <div
            key={idx}
            className="absolute border-2 border-green-400"
            style={{
              left: `${detection.bbox.x}%`,
              top: `${detection.bbox.y}%`,
              width: `${detection.bbox.width}%`,
              height: `${detection.bbox.height}%`,
            }}
          >
            <div className="absolute -top-6 left-0 bg-green-400 text-black px-1 text-xs">
              {detection.class} ({(detection.confidence * 100).toFixed(1)}%)
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderPoseOverlay = () => {
    if (!poseData?.landmarks) return null;

    return (
      <div className="absolute inset-0 pointer-events-none">
        <svg className="w-full h-full">
          {poseData.landmarks.map((point, idx) => (
            <circle
              key={idx}
              cx={`${point.x * 100}%`}
              cy={`${point.y * 100}%`}
              r="3"
              fill="red"
              opacity="0.7"
            />
          ))}
        </svg>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Stream Header */}
      <div className="flex items-center justify-between p-4 bg-gray-800 border-b border-gray-700">
        <div>
          <h2 className="text-xl font-bold">{stream?.title || 'Live Stream'}</h2>
          <div className="text-sm text-gray-400">
            {stream?.type} • {stream?.viewers || 0} viewers
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className="text-sm">{isConnected ? 'Analytics Connected' : 'Disconnected'}</span>
          </div>
          
          <div className="text-sm text-gray-300">
            {streamStats.fps.toFixed(1)} FPS • {streamStats.latency}ms
          </div>
        </div>
      </div>

      {/* Video Player */}
      <div className="flex-1 relative bg-black">
        {stream?.stream_url ? (
          <div className="relative w-full h-full">
            <ReactPlayer
              ref={playerRef}
              url={stream.stream_url}
              playing={true}
              width="100%"
              height="100%"
              controls={true}
              config={{
                file: {
                  attributes: {
                    crossOrigin: 'anonymous'
                  }
                }
              }}
            />
            
            {/* Analytics Overlays */}
            {renderDetectionOverlay()}
            {renderPoseOverlay()}
            
            {/* Analytics Info Panel */}
            {analytics && (
              <div className="absolute top-4 right-4 bg-black bg-opacity-75 p-3 rounded-lg text-white max-w-xs">
                <div className="text-sm font-semibold mb-2">Live Analytics</div>
                
                {detections.length > 0 && (
                  <div className="mb-2">
                    <div className="text-xs text-gray-300">Objects: {detections.length}</div>
                    {detections.slice(0, 3).map((det, idx) => (
                      <div key={idx} className="text-xs">
                        {det.class}: {(det.confidence * 100).toFixed(1)}%
                      </div>
                    ))}
                  </div>
                )}
                
                {poseData && (
                  <div className="mb-2">
                    <div className="text-xs text-gray-300">Pose Detected</div>
                    <div className="text-xs">
                      Confidence: {(poseData.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                )}
                
                {analytics.vibrio?.speed && (
                  <div className="text-xs">
                    Speed: {analytics.vibrio.speed.toFixed(1)} km/h
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-6xl mb-4">📹</div>
              <div className="text-xl font-bold mb-2">No Stream Available</div>
              <div className="text-gray-400">
                Waiting for stream to start...
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Stream Controls */}
      <div className="p-4 bg-gray-800 border-t border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button 
              className="btn-secondary"
              onClick={() => {/* TODO: Implement stream recording */}}
            >
              🔴 Record
            </button>
            
            <button 
              className="btn-secondary"
              onClick={() => {/* TODO: Implement screenshot */}}
            >
              📸 Screenshot
            </button>
            
            <button 
              className="btn-secondary"
              onClick={() => {/* TODO: Implement analytics export */}}
            >
              📊 Export Data
            </button>
          </div>
          
          <div className="flex items-center space-x-4 text-sm text-gray-300">
            <div>Quality: Auto</div>
            <div>•</div>
            <div>Bitrate: {(streamStats.bitrate / 1000).toFixed(1)} Mbps</div>
          </div>
        </div>
      </div>
    </div>
  );
}; 