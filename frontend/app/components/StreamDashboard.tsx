'use client';

import React, { useEffect, useRef, useState } from 'react';

interface Stream {
  id: string;
  title: string;
  status: string;
  viewer_count: number;
  created_at: string;
}

interface Analytics {
  vibrio?: {
    detections: any[];
    tracks: any[];
    motion_energy: {
      motion_energy: number;
      motion_regions: number[][];
    };
    optical_flow: {
      flow_magnitude: number;
      flow_direction: number[];
    };
  };
  moriarty?: {
    pose_detected: boolean;
    landmarks: any;
    biomechanics: {
      joint_angles: Record<string, number>;
      center_of_mass: number[] | null;
    };
    pose_quality_score: number;
  };
  processing_time: number;
  timestamp: number;
}

interface StreamDashboardProps {
  stream: Stream;
  analytics: Analytics | null;
  onAnalyticsUpdate: (analytics: Analytics) => void;
}

export const StreamDashboard: React.FC<StreamDashboardProps> = ({
  stream,
  analytics,
  onAnalyticsUpdate
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [frameRate, setFrameRate] = useState(0);
  const [lastFrameTime, setLastFrameTime] = useState(0);

  useEffect(() => {
    if (stream?.id) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [stream?.id]);

  const connectWebSocket = () => {
    const wsUrl = `${process.env.NEXT_PUBLIC_ANALYTICS_URL?.replace('http', 'ws')}/ws/${stream.id}`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        setIsConnected(true);
        console.log('Connected to analytics WebSocket');
      };

      wsRef.current.onmessage = (event) => {
        try {
          const analyticsData = JSON.parse(event.data);
          onAnalyticsUpdate(analyticsData);
          
          // Calculate frame rate
          const currentTime = Date.now();
          if (lastFrameTime > 0) {
            const fps = 1000 / (currentTime - lastFrameTime);
            setFrameRate(Math.round(fps * 10) / 10);
          }
          setLastFrameTime(currentTime);
          
          // Draw analytics overlay
          drawAnalyticsOverlay(analyticsData);
        } catch (error) {
          console.error('Error parsing analytics data:', error);
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        console.log('Disconnected from analytics WebSocket');
        
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  };

  const drawAnalyticsOverlay = (analyticsData: Analytics) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw detections
    if (analyticsData.vibrio?.detections) {
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      
      analyticsData.vibrio.detections.forEach((detection: any, index: number) => {
        const [x, y, width, height] = detection.bbox;
        
        // Draw bounding box
        ctx.strokeRect(x, y, width, height);
        
        // Draw confidence
        ctx.fillStyle = '#00ff00';
        ctx.font = '14px Arial';
        ctx.fillText(
          `Human: ${(detection.confidence * 100).toFixed(1)}%`,
          x,
          y - 5
        );
        
        // Draw center point
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(detection.center[0], detection.center[1], 3, 0, 2 * Math.PI);
        ctx.fill();
      });
    }

    // Draw tracking paths
    if (analyticsData.vibrio?.tracks) {
      ctx.strokeStyle = '#0088ff';
      ctx.lineWidth = 2;
      
      analyticsData.vibrio.tracks.forEach((track: any) => {
        const [x, y] = track.position;
        
        // Draw track ID
        ctx.fillStyle = '#0088ff';
        ctx.font = '12px Arial';
        ctx.fillText(`ID: ${track.track_id}`, x + 5, y - 10);
        
        // Draw speed
        if (track.speed > 0) {
          ctx.fillText(`${track.speed.toFixed(1)} km/h`, x + 5, y + 15);
        }
      });
    }

    // Draw pose landmarks
    if (analyticsData.moriarty?.pose_detected && analyticsData.moriarty.landmarks) {
      ctx.fillStyle = '#ffff00';
      
      Object.values(analyticsData.moriarty.landmarks).forEach((landmark: any) => {
        if (landmark.visibility > 0.5) {
          ctx.beginPath();
          ctx.arc(landmark.x, landmark.y, 2, 0, 2 * Math.PI);
          ctx.fill();
        }
      });
      
      // Draw center of mass
      if (analyticsData.moriarty.biomechanics.center_of_mass) {
        const [comX, comY] = analyticsData.moriarty.biomechanics.center_of_mass;
        ctx.fillStyle = '#ff00ff';
        ctx.beginPath();
        ctx.arc(comX, comY, 5, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.fillStyle = '#ff00ff';
        ctx.font = '12px Arial';
        ctx.fillText('CoM', comX + 8, comY + 4);
      }
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Stream Header */}
      <div className="bg-gray-700 p-4 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">{stream.title}</h2>
            <div className="flex items-center space-x-4 text-sm text-gray-300 mt-1">
              <span>👥 {stream.viewer_count} viewers</span>
              <span className={`flex items-center ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                <div className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
              {frameRate > 0 && (
                <span className="text-blue-400">📊 {frameRate} FPS</span>
              )}
            </div>
          </div>
          
          <div className="text-right">
            <div className="text-sm text-gray-400">Stream ID</div>
            <div className="font-mono text-xs">{stream.id}</div>
          </div>
        </div>
      </div>

      {/* Video Container */}
      <div className="flex-1 bg-black relative overflow-hidden rounded-b-lg">
        {/* Placeholder for video stream */}
        <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
          <div className="text-center">
            <div className="text-6xl mb-4">📹</div>
            <div className="text-xl font-semibold mb-2">Live Stream</div>
            <div className="text-gray-400">Computer Vision Analytics Active</div>
          </div>
        </div>

        {/* Analytics Overlay Canvas */}
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ imageRendering: 'pixelated' }}
        />

        {/* Analytics Stats Overlay */}
        {analytics && (
          <div className="absolute top-4 left-4 bg-black bg-opacity-70 p-3 rounded text-sm">
            <div className="grid grid-cols-2 gap-4">
              {analytics.vibrio && (
                <div>
                  <div className="text-green-400 font-semibold">Vibrio</div>
                  <div>Detections: {analytics.vibrio.detections?.length || 0}</div>
                  <div>Tracks: {analytics.vibrio.tracks?.length || 0}</div>
                  <div>Motion: {(analytics.vibrio.motion_energy?.motion_energy * 100 || 0).toFixed(1)}%</div>
                </div>
              )}
              
              {analytics.moriarty && (
                <div>
                  <div className="text-yellow-400 font-semibold">Moriarty</div>
                  <div>Pose: {analytics.moriarty.pose_detected ? '✓' : '✗'}</div>
                  <div>Quality: {(analytics.moriarty.pose_quality_score * 100 || 0).toFixed(1)}%</div>
                  <div>Joints: {Object.keys(analytics.moriarty.biomechanics?.joint_angles || {}).length}</div>
                </div>
              )}
            </div>
            
            <div className="mt-2 pt-2 border-t border-gray-600">
              <div>Processing: {(analytics.processing_time * 1000).toFixed(1)}ms</div>
            </div>
          </div>
        )}

        {/* Connection Status */}
        {!isConnected && (
          <div className="absolute bottom-4 left-4 bg-red-600 bg-opacity-80 px-3 py-2 rounded text-sm">
            🔄 Reconnecting to analytics...
          </div>
        )}
      </div>
    </div>
  );
}; 