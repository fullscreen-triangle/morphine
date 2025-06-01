'use client';

import React, { useState, useEffect } from 'react';

interface AnalyticsPanelProps {
  streamId: string;
  analytics: any;
}

export const AnalyticsPanel: React.FC<AnalyticsPanelProps> = ({ streamId, analytics }) => {
  const [historicalData, setHistoricalData] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    if (streamId) {
      fetchSummary();
    }
  }, [streamId]);

  const fetchSummary = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_ANALYTICS_URL}/analytics/${streamId}/summary`);
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  };

  return (
    <div className="h-full flex flex-col p-4">
      <h3 className="text-lg font-bold mb-4">Analytics Panel</h3>
      
      {/* Real-time Analytics */}
      {analytics && (
        <div className="mb-6">
          <h4 className="font-semibold mb-2 text-blue-400">Real-time Data</h4>
          <div className="space-y-2 text-sm">
            {analytics.vibrio && (
              <div className="bg-gray-700 p-3 rounded">
                <div className="text-green-400 font-medium">Vibrio Framework</div>
                <div>Detections: {analytics.vibrio.detections?.length || 0}</div>
                <div>Active Tracks: {analytics.vibrio.tracks?.length || 0}</div>
                <div>Motion Energy: {(analytics.vibrio.motion_energy?.motion_energy * 100 || 0).toFixed(1)}%</div>
                <div>Flow Magnitude: {analytics.vibrio.optical_flow?.flow_magnitude?.toFixed(2) || 0}</div>
              </div>
            )}
            
            {analytics.moriarty && (
              <div className="bg-gray-700 p-3 rounded">
                <div className="text-yellow-400 font-medium">Moriarty Analysis</div>
                <div>Pose Detected: {analytics.moriarty.pose_detected ? '✓' : '✗'}</div>
                <div>Quality Score: {(analytics.moriarty.pose_quality_score * 100 || 0).toFixed(1)}%</div>
                <div>Joint Angles: {Object.keys(analytics.moriarty.biomechanics?.joint_angles || {}).length}</div>
                {analytics.moriarty.biomechanics?.center_of_mass && (
                  <div>Center of Mass: ({analytics.moriarty.biomechanics.center_of_mass[0].toFixed(0)}, {analytics.moriarty.biomechanics.center_of_mass[1].toFixed(0)})</div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Summary Statistics */}
      {summary && (
        <div className="mb-6">
          <h4 className="font-semibold mb-2 text-purple-400">Summary Statistics</h4>
          <div className="bg-gray-700 p-3 rounded text-sm space-y-1">
            <div>Total Frames: {summary.total_frames}</div>
            <div>Avg FPS: {summary.avg_fps?.toFixed(1) || 0}</div>
            <div>Detection Rate: {(summary.detection_rate * 100 || 0).toFixed(1)}%</div>
            <div>Pose Detection Rate: {(summary.pose_detection_rate * 100 || 0).toFixed(1)}%</div>
            <div>Error Rate: {(summary.error_rate * 100 || 0).toFixed(1)}%</div>
            <div>Avg Processing: {(summary.avg_processing_time * 1000 || 0).toFixed(1)}ms</div>
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      <div className="flex-1">
        <h4 className="font-semibold mb-2 text-green-400">Performance</h4>
        <div className="text-sm space-y-2">
          {analytics && (
            <div className="bg-gray-700 p-3 rounded">
              <div>Processing Time: {(analytics.processing_time * 1000).toFixed(1)}ms</div>
              <div>Timestamp: {new Date(analytics.timestamp * 1000).toLocaleTimeString()}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}; 