'use client';

import React, { useState } from 'react';

interface Stream {
  id: string;
  title: string;
  status: string;
  viewer_count: number;
  created_at: string;
}

interface ControlPanelProps {
  streams: Stream[];
  selectedStream: Stream | null;
  onStreamSelect: (stream: Stream) => void;
  onStreamUpdate: () => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  streams,
  selectedStream,
  onStreamSelect,
  onStreamUpdate
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [newStreamTitle, setNewStreamTitle] = useState('');

  const createStream = async () => {
    if (!newStreamTitle.trim()) return;

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/streams`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: newStreamTitle,
          description: 'New stream with analytics'
        })
      });

      const data = await response.json();
      if (data.success) {
        setNewStreamTitle('');
        setIsCreating(false);
        onStreamUpdate();
      }
    } catch (error) {
      console.error('Failed to create stream:', error);
    }
  };

  const startStream = async (streamId: string) => {
    try {
      // Start core stream
      await fetch(`${process.env.NEXT_PUBLIC_CORE_URL}/api/streams/${streamId}/start`, {
        method: 'POST'
      });

      // Start analytics
      await fetch(`${process.env.NEXT_PUBLIC_ANALYTICS_URL}/analytics/start_stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stream_id: streamId,
          source_type: 'webcam',
          source_url: '0'
        })
      });

      onStreamUpdate();
    } catch (error) {
      console.error('Failed to start stream:', error);
    }
  };

  const stopStream = async (streamId: string) => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_CORE_URL}/api/streams/${streamId}/stop`, {
        method: 'POST'
      });
      
      await fetch(`${process.env.NEXT_PUBLIC_ANALYTICS_URL}/analytics/stop_stream/${streamId}`, {
        method: 'POST'
      });

      onStreamUpdate();
    } catch (error) {
      console.error('Failed to stop stream:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-green-500';
      case 'inactive': return 'bg-gray-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Stream Control</h2>
          <button
            className="btn-primary text-sm"
            onClick={() => setIsCreating(!isCreating)}
          >
            + New Stream
          </button>
        </div>

        {/* Create Stream Form */}
        {isCreating && (
          <div className="space-y-2">
            <input
              type="text"
              className="input-field w-full"
              placeholder="Stream title..."
              value={newStreamTitle}
              onChange={(e) => setNewStreamTitle(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && createStream()}
            />
            <div className="flex space-x-2">
              <button className="btn-primary text-sm flex-1" onClick={createStream}>
                Create
              </button>
              <button 
                className="btn-outline text-sm flex-1"
                onClick={() => {
                  setIsCreating(false);
                  setNewStreamTitle('');
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Stream List */}
      <div className="flex-1 overflow-y-auto">
        {streams.length > 0 ? (
          <div className="p-2 space-y-2">
            {streams.map((stream) => (
              <div
                key={stream.id}
                className={`p-3 rounded cursor-pointer transition-colors ${
                  selectedStream?.id === stream.id
                    ? 'bg-blue-600 border border-blue-500'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
                onClick={() => onStreamSelect(stream)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="font-medium truncate">{stream.title}</div>
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(stream.status)}`}></div>
                </div>
                
                <div className="text-sm text-gray-300 space-y-1">
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className="capitalize">{stream.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Viewers:</span>
                    <span>{stream.viewer_count}</span>
                  </div>
                </div>

                {/* Stream Controls */}
                <div className="mt-3 flex space-x-2">
                  {stream.status?.toLowerCase() === 'active' ? (
                    <button
                      className="btn-secondary text-xs flex-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        stopStream(stream.id);
                      }}
                    >
                      Stop
                    </button>
                  ) : (
                    <button
                      className="btn-primary text-xs flex-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        startStream(stream.id);
                      }}
                    >
                      Start
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-gray-400">
            <div className="text-4xl mb-4">📹</div>
            <div>No streams available</div>
            <div className="text-sm mt-2">Create a new stream to get started</div>
          </div>
        )}
      </div>

      {/* System Status */}
      <div className="p-4 border-t border-gray-700">
        <div className="text-sm space-y-2">
          <div className="flex justify-between">
            <span>Total Streams:</span>
            <span>{streams.length}</span>
          </div>
          <div className="flex justify-between">
            <span>Active:</span>
            <span className="text-green-400">
              {streams.filter(s => s.status?.toLowerCase() === 'active').length}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Total Viewers:</span>
            <span>{streams.reduce((sum, s) => sum + (s.viewer_count || 0), 0)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}; 