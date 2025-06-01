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
  const [isCreatingStream, setIsCreatingStream] = useState(false);
  const [newStreamForm, setNewStreamForm] = useState({
    title: '',
    source_type: 'webcam',
    source_url: '0',
    settings: {}
  });

  const createStream = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/streams`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer demo-token'
        },
        body: JSON.stringify(newStreamForm)
      });

      const data = await response.json();
      if (data.success) {
        setIsCreatingStream(false);
        setNewStreamForm({
          title: '',
          source_type: 'webcam',
          source_url: '0',
          settings: {}
        });
        onStreamUpdate();
      } else {
        alert(`Failed to create stream: ${data.error}`);
      }
    } catch (error) {
      console.error('Failed to create stream:', error);
      alert('Failed to create stream');
    }
  };

  const stopStream = async (streamId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/streams/${streamId}/stop`, {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer demo-token'
        }
      });

      const data = await response.json();
      if (data.success) {
        onStreamUpdate();
      } else {
        alert(`Failed to stop stream: ${data.error}`);
      }
    } catch (error) {
      console.error('Failed to stop stream:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'starting': return 'bg-yellow-500';
      case 'stopping': return 'bg-orange-500';
      case 'stopped': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active': return 'Live';
      case 'starting': return 'Starting...';
      case 'stopping': return 'Stopping...';
      case 'stopped': return 'Stopped';
      default: return 'Unknown';
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">🎛️ Control Panel</h3>
          <button
            className="btn-primary text-sm"
            onClick={() => setIsCreatingStream(true)}
          >
            + New Stream
          </button>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="bg-gray-700 p-2 rounded text-center">
            <div className="text-2xl font-bold text-green-400">{streams.length}</div>
            <div className="text-gray-300">Total Streams</div>
          </div>
          <div className="bg-gray-700 p-2 rounded text-center">
            <div className="text-2xl font-bold text-blue-400">
              {streams.filter(s => s.status === 'active').length}
            </div>
            <div className="text-gray-300">Active</div>
          </div>
        </div>
      </div>

      {/* Stream List */}
      <div className="flex-1 overflow-y-auto p-4">
        <h4 className="text-sm font-semibold text-gray-300 mb-3">Active Streams</h4>
        
        {streams.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            <div className="text-4xl mb-2">📹</div>
            <div>No streams available</div>
            <div className="text-sm">Create a new stream to get started</div>
          </div>
        ) : (
          <div className="space-y-2">
            {streams.map((stream) => (
              <div
                key={stream.id}
                className={`p-3 rounded cursor-pointer transition-colors ${
                  selectedStream?.id === stream.id
                    ? 'bg-blue-600 border border-blue-400'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
                onClick={() => onStreamSelect(stream)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-medium mb-1">
                      {stream.title || `Stream ${stream.id.slice(0, 8)}`}
                    </div>
                    
                    <div className="flex items-center space-x-2 text-sm text-gray-300">
                      <div className={`w-2 h-2 rounded-full ${getStatusColor(stream.status)}`}></div>
                      <span>{getStatusText(stream.status)}</span>
                    </div>
                    
                    <div className="text-xs text-gray-400 mt-1">
                      {stream.source_type} • {stream.viewers || 0} viewers
                    </div>
                  </div>
                  
                  <div className="flex flex-col space-y-1">
                    {stream.status === 'active' && (
                      <button
                        className="text-xs text-red-400 hover:text-red-300"
                        onClick={(e) => {
                          e.stopPropagation();
                          stopStream(stream.id);
                        }}
                      >
                        Stop
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stream Settings */}
      {selectedStream && (
        <div className="border-t border-gray-700 p-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">Stream Settings</h4>
          
          <div className="space-y-3 text-sm">
            <div>
              <label className="block text-gray-400 mb-1">Stream ID</label>
              <div className="font-mono text-xs bg-gray-700 p-2 rounded">
                {selectedStream.id}
              </div>
            </div>
            
            <div>
              <label className="block text-gray-400 mb-1">Source</label>
              <div className="text-gray-300">
                {selectedStream.source_type}: {selectedStream.source_url}
              </div>
            </div>
            
            <div>
              <label className="block text-gray-400 mb-1">Created</label>
              <div className="text-gray-300">
                {new Date(selectedStream.created_at).toLocaleString()}
              </div>
            </div>
            
            {selectedStream.analytics_enabled && (
              <div className="text-green-400 text-xs">
                ✓ Computer vision analytics enabled
              </div>
            )}
          </div>
          
          <div className="mt-4 space-y-2">
            <button className="btn-secondary w-full text-sm">
              📊 Export Analytics
            </button>
            <button className="btn-secondary w-full text-sm">
              ⚙️ Stream Settings
            </button>
          </div>
        </div>
      )}

      {/* Create Stream Modal */}
      {isCreatingStream && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg w-96 max-w-full mx-4">
            <h3 className="text-lg font-bold mb-4">Create New Stream</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-300 mb-1">Stream Title</label>
                <input
                  type="text"
                  className="input-field w-full"
                  value={newStreamForm.title}
                  onChange={(e) => setNewStreamForm({...newStreamForm, title: e.target.value})}
                  placeholder="My Live Stream"
                />
              </div>
              
              <div>
                <label className="block text-sm text-gray-300 mb-1">Source Type</label>
                <select
                  className="input-field w-full"
                  value={newStreamForm.source_type}
                  onChange={(e) => setNewStreamForm({...newStreamForm, source_type: e.target.value})}
                >
                  <option value="webcam">Webcam</option>
                  <option value="rtmp">RTMP Stream</option>
                  <option value="file">Video File</option>
                  <option value="url">Stream URL</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-gray-300 mb-1">Source URL</label>
                <input
                  type="text"
                  className="input-field w-full"
                  value={newStreamForm.source_url}
                  onChange={(e) => setNewStreamForm({...newStreamForm, source_url: e.target.value})}
                  placeholder={
                    newStreamForm.source_type === 'webcam' ? '0' :
                    newStreamForm.source_type === 'rtmp' ? 'rtmp://localhost/live/stream' :
                    newStreamForm.source_type === 'file' ? '/path/to/video.mp4' :
                    'http://example.com/stream.m3u8'
                  }
                />
              </div>
            </div>
            
            <div className="flex space-x-3 mt-6">
              <button
                className="btn-secondary flex-1"
                onClick={() => setIsCreatingStream(false)}
              >
                Cancel
              </button>
              <button
                className="btn-primary flex-1"
                onClick={createStream}
                disabled={!newStreamForm.title}
              >
                Create Stream
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}; 