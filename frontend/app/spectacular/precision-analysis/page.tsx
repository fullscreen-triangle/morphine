"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import { 
  Target, 
  Zap, 
  MapPin, 
  Activity, 
  TrendingUp, 
  Eye, 
  Crosshair,
  Satellite,
  Timer,
  DollarSign,
  BarChart3,
  Users,
  Trophy,
  Settings,
  Play,
  Pause,
  Square,
  Download,
  Upload,
  Share
} from 'lucide-react';

interface GPSMetrics {
  latitude: number;
  longitude: number;
  altitude: number;
  accuracy: number;
  satelliteCount: number;
  hdop: number;
  timestamp: number;
}

interface BiomechanicalData {
  jointAngles: Record<string, number>;
  jointVelocities: Record<string, number>;
  forceVectors: Record<string, [number, number, number]>;
  centerOfMass: [number, number, number];
  movementEfficiency: number;
  powerOutput: number;
  stabilityScore: number;
  techniqueScore: number;
  movementType: string;
}

interface PrecisionAnalysisState {
  isRecording: boolean;
  gpsConnected: boolean;
  visionActive: boolean;
  currentAnalysis: BiomechanicalData | null;
  gpsMetrics: GPSMetrics | null;
  precisionScore: number;
  sessionDuration: number;
  clickedJoints: string[];
  selectedMuscles: string[];
  annotations: Array<{
    timestamp: number;
    type: 'joint' | 'muscle' | 'movement';
    data: any;
    userInsight: string;
  }>;
}

export default function PrecisionAnalysisPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [analysisState, setAnalysisState] = useState<PrecisionAnalysisState>({
    isRecording: false,
    gpsConnected: false,
    visionActive: false,
    currentAnalysis: null,
    gpsMetrics: null,
    precisionScore: 0,
    sessionDuration: 0,
    clickedJoints: [],
    selectedMuscles: [],
    annotations: []
  });

  const [movementType, setMovementType] = useState('penalty_kick');
  const [currentPhase, setCurrentPhase] = useState('preparation');
  const [analysisInsight, setAnalysisInsight] = useState('');
  const [modelParams, setModelParams] = useState({
    title: '',
    description: '',
    price: 50,
    type: 'single_analysis'
  });

  // Nanosecond timestamp generator
  const getNanosecondTimestamp = useCallback(() => {
    return performance.now() * 1000000; // Convert milliseconds to nanoseconds
  }, []);

  // Initialize precision systems
  useEffect(() => {
    const initializeSystems = async () => {
      try {
        // Initialize GPS connection
        const gpsResponse = await fetch('/api/analytics/gps/initialize', {
          method: 'POST'
        });
        const gpsData = await gpsResponse.json();
        
        // Initialize computer vision
        const visionResponse = await fetch('/api/analytics/vision/initialize', {
          method: 'POST'
        });
        const visionData = await visionResponse.json();

        setAnalysisState(prev => ({
          ...prev,
          gpsConnected: gpsData.success,
          visionActive: visionData.success
        }));

        // Start real-time data streams
        if (gpsData.success) {
          startGPSStream();
        }
        if (visionData.success) {
          startVisionStream();
        }

      } catch (error) {
        console.error('Failed to initialize precision systems:', error);
      }
    };

    initializeSystems();
  }, []);

  const startGPSStream = useCallback(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('/api/analytics/gps/current');
        const gpsData = await response.json();
        
        if (gpsData.success) {
          setAnalysisState(prev => ({
            ...prev,
            gpsMetrics: gpsData.position,
            precisionScore: gpsData.precisionScore
          }));
        }
      } catch (error) {
        console.error('GPS stream error:', error);
      }
    }, 100); // 10Hz updates

    return () => clearInterval(interval);
  }, []);

  const startVisionStream = useCallback(() => {
    // This would integrate with the webcam/video stream
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { width: 1920, height: 1080, frameRate: 60 } 
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }

        // Start frame processing
        processVideoFrames();
      } catch (error) {
        console.error('Camera initialization failed:', error);
      }
    };

    startCamera();
  }, []);

  const processVideoFrames = useCallback(() => {
    const processFrame = async () => {
      if (!videoRef.current || !canvasRef.current) return;

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      const video = videoRef.current;

      // Draw current frame
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Get frame data
      const imageData = canvas.toDataURL('image/jpeg', 0.8);
      const timestamp = getNanosecondTimestamp();

      try {
        // Send frame for precision analysis
        const response = await fetch('/api/analytics/vision/process-frame', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            frameData: imageData,
            timestamp: timestamp,
            sessionId: 'spectacular_session_' + Date.now()
          })
        });

        const analysisResult = await response.json();
        
        if (analysisResult.success && analysisResult.biomechanicalAnalysis) {
          setAnalysisState(prev => ({
            ...prev,
            currentAnalysis: analysisResult.biomechanicalAnalysis
          }));

          // Draw analysis overlay
          drawAnalysisOverlay(ctx, analysisResult.biomechanicalAnalysis);
        }
      } catch (error) {
        console.error('Frame processing error:', error);
      }

      // Continue processing if recording
      if (analysisState.isRecording) {
        requestAnimationFrame(processFrame);
      }
    };

    processFrame();
  }, [analysisState.isRecording, getNanosecondTimestamp]);

  const drawAnalysisOverlay = useCallback((ctx: CanvasRenderingContext2D, analysis: BiomechanicalData) => {
    // Draw pose keypoints and skeleton
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.fillStyle = '#ff0000';

    // This would draw the actual keypoints from pose estimation
    // For demo purposes, we'll draw some sample overlays
    
    // Draw center of mass
    if (analysis.centerOfMass) {
      const [x, y] = analysis.centerOfMass;
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
    }

    // Draw force vectors
    Object.entries(analysis.forceVectors || {}).forEach(([joint, force]) => {
      const [fx, fy] = force;
      // Scale and draw force vector
      ctx.beginPath();
      ctx.moveTo(100, 100); // Would use actual joint position
      ctx.lineTo(100 + fx * 10, 100 + fy * 10);
      ctx.stroke();
    });

    // Draw joint angles
    ctx.fillStyle = '#ffffff';
    ctx.font = '12px Arial';
    Object.entries(analysis.jointAngles || {}).forEach(([joint, angle], index) => {
      ctx.fillText(`${joint}: ${angle.toFixed(1)}°`, 10, 20 + index * 15);
    });
  }, []);

  const handleJointClick = useCallback((joint: string, position: [number, number]) => {
    const timestamp = getNanosecondTimestamp();
    
    setAnalysisState(prev => ({
      ...prev,
      clickedJoints: [...prev.clickedJoints, joint],
      annotations: [...prev.annotations, {
        timestamp,
        type: 'joint',
        data: { joint, position },
        userInsight: analysisInsight
      }]
    }));

    // Send joint click to backend for model creation
    fetch('/api/spectacular/joint-click', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        joint,
        position,
        timestamp,
        movementType,
        phase: currentPhase,
        gpsPosition: analysisState.gpsMetrics,
        insight: analysisInsight
      })
    });
  }, [getNanosecondTimestamp, analysisInsight, movementType, currentPhase, analysisState.gpsMetrics]);

  const startRecording = useCallback(async () => {
    try {
      const response = await fetch('/api/spectacular/start-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          movementType,
          gpsEnabled: analysisState.gpsConnected,
          visionEnabled: analysisState.visionActive,
          timestamp: getNanosecondTimestamp()
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setAnalysisState(prev => ({
          ...prev,
          isRecording: true,
          sessionDuration: 0
        }));

        processVideoFrames();
      }
    } catch (error) {
      console.error('Failed to start recording:', error);
    }
  }, [movementType, analysisState.gpsConnected, analysisState.visionActive, getNanosecondTimestamp, processVideoFrames]);

  const stopRecording = useCallback(async () => {
    try {
      const response = await fetch('/api/spectacular/stop-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          annotations: analysisState.annotations,
          timestamp: getNanosecondTimestamp()
        })
      });

      const result = await response.json();
      
      setAnalysisState(prev => ({
        ...prev,
        isRecording: false
      }));

      // Show model creation options
      if (result.sessionData) {
        showModelCreationDialog(result.sessionData);
      }
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  }, [analysisState.annotations, getNanosecondTimestamp]);

  const showModelCreationDialog = (sessionData: any) => {
    // This would open a modal for model creation
    console.log('Session data ready for model creation:', sessionData);
  };

  const createMarketplaceModel = useCallback(async () => {
    try {
      const response = await fetch('/api/marketplace/create-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...modelParams,
          annotations: analysisState.annotations,
          movementType,
          gpsData: analysisState.gpsMetrics,
          analysisQuality: analysisState.precisionScore
        })
      });

      const result = await response.json();
      
      if (result.success) {
        alert(`Model created successfully! Model ID: ${result.modelId}`);
      }
    } catch (error) {
      console.error('Failed to create model:', error);
    }
  }, [modelParams, analysisState.annotations, movementType, analysisState.gpsMetrics, analysisState.precisionScore]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Spectacular Precision Analysis
            </h1>
            <p className="text-slate-300 mt-2">Nanosecond GPS + Computer Vision Biomechanical Intelligence</p>
          </div>
          
          <div className="flex items-center space-x-4">
            <Badge variant={analysisState.gpsConnected ? "default" : "destructive"} className="flex items-center space-x-1">
              <Satellite className="w-4 h-4" />
              <span>GPS {analysisState.gpsConnected ? 'Connected' : 'Disconnected'}</span>
            </Badge>
            <Badge variant={analysisState.visionActive ? "default" : "destructive"} className="flex items-center space-x-1">
              <Eye className="w-4 h-4" />
              <span>Vision {analysisState.visionActive ? 'Active' : 'Inactive'}</span>
            </Badge>
            <Badge variant="outline" className="flex items-center space-x-1">
              <Target className="w-4 h-4" />
              <span>Precision: {(analysisState.precisionScore * 100).toFixed(1)}%</span>
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Analysis View */}
          <div className="lg:col-span-2 space-y-6">
            {/* Video/Canvas Area */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center space-x-2">
                    <Crosshair className="w-5 h-5" />
                    <span>Precision Biomechanical Analysis</span>
                  </CardTitle>
                  
                  <div className="flex items-center space-x-2">
                    <Button 
                      variant={analysisState.isRecording ? "destructive" : "default"}
                      onClick={analysisState.isRecording ? stopRecording : startRecording}
                      className="flex items-center space-x-1"
                    >
                      {analysisState.isRecording ? (
                        <>
                          <Square className="w-4 h-4" />
                          <span>Stop</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          <span>Start Analysis</span>
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent>
                <div className="relative">
                  <video 
                    ref={videoRef}
                    className="w-full h-auto rounded-lg"
                    style={{ display: 'none' }}
                  />
                  <canvas 
                    ref={canvasRef}
                    width={1920}
                    height={1080}
                    className="w-full h-auto rounded-lg border border-slate-600"
                    onClick={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      const x = e.clientX - rect.left;
                      const y = e.clientY - rect.top;
                      // Convert to canvas coordinates
                      const canvasX = (x / rect.width) * 1920;
                      const canvasY = (y / rect.height) * 1080;
                      handleJointClick('clicked_point', [canvasX, canvasY]);
                    }}
                  />
                  
                  {/* Analysis Overlay */}
                  {analysisState.currentAnalysis && (
                    <div className="absolute top-4 left-4 bg-black/70 rounded-lg p-3 space-y-1">
                      <div className="text-xs text-cyan-400">Live Analysis</div>
                      <div className="text-sm">Type: {analysisState.currentAnalysis.movementType}</div>
                      <div className="text-sm">Efficiency: {(analysisState.currentAnalysis.movementEfficiency * 100).toFixed(1)}%</div>
                      <div className="text-sm">Power: {analysisState.currentAnalysis.powerOutput.toFixed(0)}W</div>
                      <div className="text-sm">Stability: {(analysisState.currentAnalysis.stabilityScore * 100).toFixed(1)}%</div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Analysis Controls */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle>Analysis Configuration</CardTitle>
              </CardHeader>
              
              <CardContent>
                <Tabs defaultValue="movement" className="w-full">
                  <TabsList className="grid grid-cols-4 w-full">
                    <TabsTrigger value="movement">Movement</TabsTrigger>
                    <TabsTrigger value="phase">Phase</TabsTrigger>
                    <TabsTrigger value="annotation">Annotation</TabsTrigger>
                    <TabsTrigger value="model">Model</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="movement" className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Movement Type</label>
                      <select 
                        value={movementType}
                        onChange={(e) => setMovementType(e.target.value)}
                        className="w-full mt-1 p-2 bg-slate-700 border border-slate-600 rounded-md"
                      >
                        <option value="penalty_kick">Penalty Kick</option>
                        <option value="free_throw">Free Throw</option>
                        <option value="tennis_serve">Tennis Serve</option>
                        <option value="golf_swing">Golf Swing</option>
                        <option value="running_gait">Running Gait</option>
                        <option value="jumping">Jumping</option>
                      </select>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="phase" className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Movement Phase</label>
                      <select 
                        value={currentPhase}
                        onChange={(e) => setCurrentPhase(e.target.value)}
                        className="w-full mt-1 p-2 bg-slate-700 border border-slate-600 rounded-md"
                      >
                        <option value="preparation">Preparation</option>
                        <option value="execution">Execution</option>
                        <option value="follow_through">Follow Through</option>
                        <option value="recovery">Recovery</option>
                      </select>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="annotation" className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Analysis Insight</label>
                      <textarea
                        value={analysisInsight}
                        onChange={(e) => setAnalysisInsight(e.target.value)}
                        placeholder="Describe what you observe about the biomechanics..."
                        className="w-full mt-1 p-2 bg-slate-700 border border-slate-600 rounded-md h-24"
                      />
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="model" className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium">Model Title</label>
                        <input
                          value={modelParams.title}
                          onChange={(e) => setModelParams(prev => ({ ...prev, title: e.target.value }))}
                          placeholder="Elite Penalty Kick Analysis"
                          className="w-full mt-1 p-2 bg-slate-700 border border-slate-600 rounded-md"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Price ($)</label>
                        <input
                          type="number"
                          value={modelParams.price}
                          onChange={(e) => setModelParams(prev => ({ ...prev, price: parseInt(e.target.value) }))}
                          className="w-full mt-1 p-2 bg-slate-700 border border-slate-600 rounded-md"
                        />
                      </div>
                    </div>
                    
                    <Button 
                      onClick={createMarketplaceModel}
                      className="w-full"
                      disabled={!analysisState.annotations.length}
                    >
                      <DollarSign className="w-4 h-4 mr-2" />
                      Create Marketplace Model
                    </Button>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* GPS Precision Metrics */}
            {analysisState.gpsMetrics && (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <MapPin className="w-5 h-5" />
                    <span>GPS Precision</span>
                  </CardTitle>
                </CardHeader>
                
                <CardContent className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-400">Accuracy</span>
                    <span className="text-sm font-mono">{analysisState.gpsMetrics.accuracy.toFixed(2)}m</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-400">Satellites</span>
                    <span className="text-sm font-mono">{analysisState.gpsMetrics.satelliteCount}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-400">HDOP</span>
                    <span className="text-sm font-mono">{analysisState.gpsMetrics.hdop.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-400">Altitude</span>
                    <span className="text-sm font-mono">{analysisState.gpsMetrics.altitude.toFixed(1)}m</span>
                  </div>
                  
                  <div className="pt-2">
                    <div className="text-xs text-slate-400 mb-1">Overall Precision</div>
                    <Progress value={analysisState.precisionScore * 100} className="h-2" />
                    <div className="text-xs text-right mt-1">{(analysisState.precisionScore * 100).toFixed(1)}%</div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Current Analysis */}
            {analysisState.currentAnalysis && (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Activity className="w-5 h-5" />
                    <span>Live Biomechanics</span>
                  </CardTitle>
                </CardHeader>
                
                <CardContent className="space-y-3">
                  <div>
                    <div className="text-xs text-slate-400 mb-1">Movement Efficiency</div>
                    <Progress value={analysisState.currentAnalysis.movementEfficiency * 100} className="h-2" />
                    <div className="text-xs text-right mt-1">{(analysisState.currentAnalysis.movementEfficiency * 100).toFixed(1)}%</div>
                  </div>
                  
                  <div>
                    <div className="text-xs text-slate-400 mb-1">Power Output</div>
                    <div className="text-lg font-mono">{analysisState.currentAnalysis.powerOutput.toFixed(0)}W</div>
                  </div>
                  
                  <div>
                    <div className="text-xs text-slate-400 mb-1">Stability Score</div>
                    <Progress value={analysisState.currentAnalysis.stabilityScore * 100} className="h-2" />
                    <div className="text-xs text-right mt-1">{(analysisState.currentAnalysis.stabilityScore * 100).toFixed(1)}%</div>
                  </div>
                  
                  <div>
                    <div className="text-xs text-slate-400 mb-1">Technique Score</div>
                    <Progress value={analysisState.currentAnalysis.techniqueScore * 100} className="h-2" />
                    <div className="text-xs text-right mt-1">{(analysisState.currentAnalysis.techniqueScore * 100).toFixed(1)}%</div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Session Stats */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="w-5 h-5" />
                  <span>Session Stats</span>
                </CardTitle>
              </CardHeader>
              
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-slate-400">Clicked Joints</span>
                  <span className="text-sm font-mono">{analysisState.clickedJoints.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-400">Annotations</span>
                  <span className="text-sm font-mono">{analysisState.annotations.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-400">Recording</span>
                  <Badge variant={analysisState.isRecording ? "default" : "secondary"}>
                    {analysisState.isRecording ? "Active" : "Inactive"}
                  </Badge>
                </div>
                
                {analysisState.isRecording && (
                  <div className="pt-2 border-t border-slate-600">
                    <div className="text-xs text-slate-400 mb-1">Session Duration</div>
                    <div className="text-lg font-mono">
                      {Math.floor(analysisState.sessionDuration / 60)}:{(analysisState.sessionDuration % 60).toString().padStart(2, '0')}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              
              <CardContent className="space-y-2">
                <Button variant="outline" size="sm" className="w-full justify-start">
                  <Download className="w-4 h-4 mr-2" />
                  Export Analysis
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start">
                  <Share className="w-4 h-4 mr-2" />
                  Share Session
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start">
                  <Trophy className="w-4 h-4 mr-2" />
                  View Marketplace
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start">
                  <Settings className="w-4 h-4 mr-2" />
                  Calibration
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
} 