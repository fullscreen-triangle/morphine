'use client';

import React, { useState, useEffect } from 'react';
import { StreamDashboard } from './components/StreamDashboard';
import { AnalyticsPanel } from './components/AnalyticsPanel';
import { BettingInterface } from './components/BettingInterface';
import { ControlPanel } from './components/ControlPanel';

export default function HomePage() {
  const [activeStreams, setActiveStreams] = useState([]);
  const [selectedStream, setSelectedStream] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchActiveStreams();
    const interval = setInterval(fetchActiveStreams, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchActiveStreams = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/streams`);
      const data = await response.json();
      
      if (data.success) {
        setActiveStreams(data.data || []);
        if (!selectedStream && data.data.length > 0) {
          setSelectedStream(data.data[0]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch streams:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-2xl">Loading Morphine Platform...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold gradient-text">Morphine Platform</h1>
            <div className="text-sm text-gray-400">
              Live Streaming Analytics & Betting
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-300">
              Active Streams: <span className="text-green-400">{activeStreams.length}</span>
            </div>
            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-80px)]">
        {/* Left Sidebar - Stream List & Controls */}
        <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
          <ControlPanel 
            streams={activeStreams}
            selectedStream={selectedStream}
            onStreamSelect={setSelectedStream}
            onStreamUpdate={fetchActiveStreams}
          />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col">
          {selectedStream ? (
            <>
              {/* Video Stream & Analytics */}
              <div className="flex-1 flex">
                {/* Stream Dashboard */}
                <div className="flex-1 p-6">
                  <StreamDashboard 
                    stream={selectedStream}
                    analytics={analytics}
                    onAnalyticsUpdate={setAnalytics}
                  />
                </div>

                {/* Analytics Panel */}
                <div className="w-80 bg-gray-800 border-l border-gray-700">
                  <AnalyticsPanel 
                    streamId={selectedStream.id}
                    analytics={analytics}
                  />
                </div>
              </div>

              {/* Bottom Panel - Betting Interface */}
              <div className="h-64 bg-gray-800 border-t border-gray-700">
                <BettingInterface 
                  streamId={selectedStream.id}
                  analytics={analytics}
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-6xl mb-4">🎥</div>
                <h2 className="text-2xl font-bold mb-2">No Active Streams</h2>
                <p className="text-gray-400 mb-6">
                  Start a stream to begin analytics and betting
                </p>
                <button 
                  className="btn-primary"
                  onClick={() => {/* TODO: Implement stream creation */}}
                >
                  Create New Stream
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 