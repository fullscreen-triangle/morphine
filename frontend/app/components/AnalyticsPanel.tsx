'use client';

import React, { useState, useEffect } from 'react';

interface AnalyticsPanelProps {
  streamId: string;
  analytics: any;
}

export const AnalyticsPanel: React.FC<AnalyticsPanelProps> = ({ streamId, analytics }) => {
  const [historicalData, setHistoricalData] = useState<any[]>([]);
  const [selectedMetric, setSelectedMetric] = useState('detections');
  const [timeRange, setTimeRange] = useState('5min');

  useEffect(() => {
    fetchHistoricalData();
    const interval = setInterval(fetchHistoricalData, 30000);
    return () => clearInterval(interval);
  }, [streamId, timeRange]);

  const fetchHistoricalData = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/analytics/${streamId}/history?range=${timeRange}`
      );
      const data = await response.json();
      if (data.success) {
        setHistoricalData(data.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch historical data:', error);
    }
  };

  const getMetricValue = (data: any, metric: string) => {
    switch (metric) {
      case 'detections':
        return data?.vibrio?.detections?.length || 0;
      case 'pose_confidence':
        return data?.moriarty?.pose_quality_score || 0;
      case 'motion_energy':
        return data?.vibrio?.motion_energy?.motion_energy || 0;
      case 'processing_time':
        return data?.processing_time || 0;
      default:
        return 0;
    }
  };

  const renderMetricChart = () => {
    const dataPoints = historicalData.slice(-20);
    const maxValue = Math.max(...dataPoints.map(d => getMetricValue(d, selectedMetric)));
    
    return (
      <div className="h-32 flex items-end space-x-1">
        {dataPoints.map((data, idx) => {
          const value = getMetricValue(data, selectedMetric);
          const height = maxValue > 0 ? (value / maxValue) * 100 : 0;
          
          return (
            <div
              key={idx}
              className="flex-1 bg-blue-500 rounded-t opacity-70 hover:opacity-100 transition-opacity"
              style={{ height: `${height}%` }}
              title={`${selectedMetric}: ${value}`}
            />
          );
        })}
      </div>
    );
  };

  const getCurrentStats = () => {
    if (!analytics) return null;

    return {
      detections: analytics.vibrio?.detections?.length || 0,
      tracks: analytics.vibrio?.tracks?.length || 0,
      poseDetected: analytics.moriarty?.pose_detected || false,
      poseConfidence: analytics.moriarty?.pose_quality_score || 0,
      motionEnergy: analytics.vibrio?.motion_energy?.motion_energy || 0,
      processingTime: analytics.processing_time || 0,
      joints: Object.keys(analytics.moriarty?.biomechanics?.joint_angles || {}).length,
    };
  };

  const stats = getCurrentStats();

  return (
    <div className="h-full p-4 overflow-y-auto">
      <h3 className="text-lg font-bold mb-4">📊 Analytics</h3>

      {/* Current Stats */}
      {stats && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold mb-3 text-gray-300">Current Frame</h4>
          
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-gray-700 p-3 rounded">
              <div className="text-green-400 font-semibold">Objects</div>
              <div className="text-2xl font-bold">{stats.detections}</div>
            </div>
            
            <div className="bg-gray-700 p-3 rounded">
              <div className="text-blue-400 font-semibold">Tracks</div>
              <div className="text-2xl font-bold">{stats.tracks}</div>
            </div>
            
            <div className="bg-gray-700 p-3 rounded">
              <div className="text-yellow-400 font-semibold">Pose</div>
              <div className="text-lg">{stats.poseDetected ? '✓' : '✗'}</div>
              <div className="text-xs text-gray-400">
                {(stats.poseConfidence * 100).toFixed(1)}%
              </div>
            </div>
            
            <div className="bg-gray-700 p-3 rounded">
              <div className="text-red-400 font-semibold">Motion</div>
              <div className="text-lg">{(stats.motionEnergy * 100).toFixed(1)}%</div>
            </div>
          </div>
          
          <div className="mt-3 text-xs text-gray-400">
            Processing: {(stats.processingTime * 1000).toFixed(1)}ms
          </div>
        </div>
      )}

      {/* Detailed Analytics */}
      {analytics?.vibrio?.detections && analytics.vibrio.detections.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold mb-3 text-gray-300">Detections</h4>
          
          <div className="space-y-2">
            {analytics.vibrio.detections.slice(0, 5).map((detection: any, idx: number) => (
              <div key={idx} className="bg-gray-700 p-2 rounded text-sm">
                <div className="flex justify-between items-center">
                  <span className="font-medium">{detection.class}</span>
                  <span className="text-green-400">
                    {(detection.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  Position: ({detection.center?.[0]?.toFixed(0)}, {detection.center?.[1]?.toFixed(0)})
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pose Analysis */}
      {analytics?.moriarty?.pose_detected && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold mb-3 text-gray-300">Pose Analysis</h4>
          
          <div className="bg-gray-700 p-3 rounded">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <div className="text-gray-400">Quality</div>
                <div className="font-bold">
                  {(analytics.moriarty.pose_quality_score * 100).toFixed(1)}%
                </div>
              </div>
              
              <div>
                <div className="text-gray-400">Joints</div>
                <div className="font-bold">{stats?.joints || 0}</div>
              </div>
            </div>
            
            {analytics.moriarty.biomechanics?.center_of_mass && (
              <div className="mt-2 text-xs">
                <div className="text-gray-400">Center of Mass</div>
                <div>
                  ({analytics.moriarty.biomechanics.center_of_mass[0]?.toFixed(1)}, 
                   {analytics.moriarty.biomechanics.center_of_mass[1]?.toFixed(1)})
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Historical Chart */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-300">Trends</h4>
          
          <div className="flex space-x-2">
            <select
              className="text-xs bg-gray-700 rounded px-2 py-1"
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value)}
            >
              <option value="detections">Detections</option>
              <option value="pose_confidence">Pose Confidence</option>
              <option value="motion_energy">Motion Energy</option>
              <option value="processing_time">Processing Time</option>
            </select>
            
            <select
              className="text-xs bg-gray-700 rounded px-2 py-1"
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
            >
              <option value="1min">1 min</option>
              <option value="5min">5 min</option>
              <option value="15min">15 min</option>
              <option value="1hour">1 hour</option>
            </select>
          </div>
        </div>
        
        <div className="bg-gray-700 p-3 rounded">
          {renderMetricChart()}
        </div>
      </div>

      {/* Betting Opportunities */}
      <div className="mb-4">
        <h4 className="text-sm font-semibold mb-3 text-gray-300">Betting Opportunities</h4>
        
        <div className="space-y-2">
          {stats?.detections > 0 && (
            <div className="bg-green-900 bg-opacity-30 border border-green-500 p-2 rounded text-sm">
              <div className="text-green-400 font-medium">Object Detection</div>
              <div className="text-xs text-gray-300">
                {stats.detections} objects detected - bet on count accuracy
              </div>
            </div>
          )}
          
          {stats?.poseDetected && (
            <div className="bg-blue-900 bg-opacity-30 border border-blue-500 p-2 rounded text-sm">
              <div className="text-blue-400 font-medium">Pose Detected</div>
              <div className="text-xs text-gray-300">
                High quality pose - bet on joint angles
              </div>
            </div>
          )}
          
          {stats?.motionEnergy > 0.3 && (
            <div className="bg-yellow-900 bg-opacity-30 border border-yellow-500 p-2 rounded text-sm">
              <div className="text-yellow-400 font-medium">High Motion</div>
              <div className="text-xs text-gray-300">
                Active movement - bet on speed predictions
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Debug Info */}
      {process.env.NODE_ENV === 'development' && analytics && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold mb-2 text-gray-300">Debug</h4>
          <pre className="text-xs bg-gray-800 p-2 rounded overflow-x-auto text-gray-400">
            {JSON.stringify(analytics, null, 2).substring(0, 500)}...
          </pre>
        </div>
      )}
    </div>
  );
}; 