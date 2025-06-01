const express = require('express');
const axios = require('axios');
const logger = require('../utils/logger');
const fetch = require('node-fetch');

const router = express.Router();

const ANALYTICS_SERVICE_URL = process.env.ANALYTICS_SERVICE_URL || 'http://localhost:8000';

// In-memory storage for demo (would use proper database in production)
let gpsData = {
  connected: false,
  currentPosition: null,
  precisionScore: 0.0,
  calibrationPoints: []
};

let visionData = {
  active: false,
  currentAnalysis: null,
  detectionHistory: [],
  sessionData: {}
};

// Get latest analytics for a stream
router.get('/:streamId/latest', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    const response = await axios.get(`${ANALYTICS_SERVICE_URL}/analytics/${streamId}/latest`, {
      timeout: 5000
    });
    
    res.json({
      success: true,
      analytics: response.data
    });
  } catch (error) {
    logger.error(`Failed to fetch latest analytics for stream ${req.params.streamId}:`, error.message);
    
    if (error.response?.status === 404) {
      return res.status(404).json({
        success: false,
        error: 'No analytics found for stream'
      });
    }
    
    res.status(500).json({
      success: false,
      error: 'Failed to fetch analytics',
      message: error.message
    });
  }
});

// Get analytics summary for a stream
router.get('/:streamId/summary', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    const response = await axios.get(`${ANALYTICS_SERVICE_URL}/analytics/${streamId}/summary`, {
      timeout: 5000
    });
    
    res.json({
      success: true,
      summary: response.data
    });
  } catch (error) {
    logger.error(`Failed to fetch analytics summary for stream ${req.params.streamId}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch analytics summary',
      message: error.message
    });
  }
});

// Process a frame (for testing purposes)
router.post('/process_frame', async (req, res) => {
  try {
    const response = await axios.post(`${ANALYTICS_SERVICE_URL}/analytics/process_frame`, req.body, {
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    res.json({
      success: true,
      result: response.data
    });
  } catch (error) {
    logger.error('Failed to process frame:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to process frame',
      message: error.message
    });
  }
});

// GPS Precision Endpoints

router.post('/gps/initialize', async (req, res) => {
  try {
    // Simulate GPS initialization
    // In production, this would connect to actual GPS hardware
    
    gpsData.connected = Math.random() > 0.1; // 90% success rate for demo
    
    if (gpsData.connected) {
      // Simulate initial GPS position
      gpsData.currentPosition = {
        latitude: 37.7749 + (Math.random() - 0.5) * 0.01,
        longitude: -122.4194 + (Math.random() - 0.5) * 0.01,
        altitude: 50 + Math.random() * 100,
        accuracy: 0.1 + Math.random() * 0.5,
        satelliteCount: 8 + Math.floor(Math.random() * 8),
        hdop: 0.5 + Math.random() * 2.0,
        timestamp: Date.now() * 1000000 // Convert to nanoseconds
      };
      
      gpsData.precisionScore = Math.min(1.0, 
        (16 - gpsData.currentPosition.satelliteCount) / 4 * 0.3 +
        (2.5 - gpsData.currentPosition.hdop) / 2.5 * 0.4 +
        (1.0 - gpsData.currentPosition.accuracy) / 1.0 * 0.3
      );
    }
    
    res.json({
      success: gpsData.connected,
      message: gpsData.connected ? 'GPS initialized successfully' : 'GPS initialization failed',
      position: gpsData.currentPosition,
      precisionScore: gpsData.precisionScore
    });
    
  } catch (error) {
    console.error('GPS initialization error:', error);
    res.status(500).json({
      success: false,
      error: 'GPS initialization failed',
      message: error.message
    });
  }
});

router.get('/gps/current', async (req, res) => {
  try {
    if (!gpsData.connected) {
      return res.json({
        success: false,
        error: 'GPS not connected'
      });
    }
    
    // Simulate GPS position updates with realistic drift
    if (gpsData.currentPosition) {
      const drift = 0.000001; // Small drift for realism
      gpsData.currentPosition.latitude += (Math.random() - 0.5) * drift;
      gpsData.currentPosition.longitude += (Math.random() - 0.5) * drift;
      gpsData.currentPosition.altitude += (Math.random() - 0.5) * 0.1;
      gpsData.currentPosition.timestamp = Date.now() * 1000000;
      
      // Update accuracy based on satellite count
      gpsData.currentPosition.accuracy = Math.max(0.05, 
        0.1 + (12 - gpsData.currentPosition.satelliteCount) * 0.05 + Math.random() * 0.1
      );
      
      // Recalculate precision score
      gpsData.precisionScore = Math.min(1.0, Math.max(0.0,
        (gpsData.currentPosition.satelliteCount - 4) / 12 * 0.3 +
        Math.max(0, (3.0 - gpsData.currentPosition.hdop) / 3.0) * 0.4 +
        Math.max(0, (1.0 - gpsData.currentPosition.accuracy) / 1.0) * 0.3
      ));
    }
    
    res.json({
      success: true,
      position: gpsData.currentPosition,
      precisionScore: gpsData.precisionScore,
      timestamp: Date.now() * 1000000
    });
    
  } catch (error) {
    console.error('GPS current position error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get GPS position',
      message: error.message
    });
  }
});

router.post('/gps/calibrate', async (req, res) => {
  try {
    const { gpsCoord, pixelPos, worldPos } = req.body;
    
    if (!gpsData.connected) {
      return res.status(400).json({
        success: false,
        error: 'GPS not connected'
      });
    }
    
    // Store calibration point
    gpsData.calibrationPoints.push({
      gps: gpsCoord,
      pixel: pixelPos,
      world: worldPos,
      timestamp: Date.now() * 1000000
    });
    
    // Calculate transformation matrix if we have enough points
    let calibrated = false;
    if (gpsData.calibrationPoints.length >= 4) {
      // Simulate successful calibration
      calibrated = true;
    }
    
    res.json({
      success: true,
      calibrationPoints: gpsData.calibrationPoints.length,
      calibrated: calibrated,
      message: calibrated ? 'GPS-Vision calibration complete' : 'Calibration point added'
    });
    
  } catch (error) {
    console.error('GPS calibration error:', error);
    res.status(500).json({
      success: false,
      error: 'GPS calibration failed',
      message: error.message
    });
  }
});

// Computer Vision Endpoints

router.post('/vision/initialize', async (req, res) => {
  try {
    // Simulate computer vision initialization
    visionData.active = Math.random() > 0.05; // 95% success rate for demo
    
    res.json({
      success: visionData.active,
      message: visionData.active ? 'Computer vision initialized' : 'Vision initialization failed',
      capabilities: {
        poseEstimation: true,
        biomechanicalAnalysis: true,
        forceVectorAnalysis: true,
        movementClassification: true,
        precisionTracking: true
      }
    });
    
  } catch (error) {
    console.error('Vision initialization error:', error);
    res.status(500).json({
      success: false,
      error: 'Vision initialization failed',
      message: error.message
    });
  }
});

router.post('/vision/process-frame', async (req, res) => {
  try {
    const { frameData, timestamp, sessionId } = req.body;
    
    if (!visionData.active) {
      return res.status(400).json({
        success: false,
        error: 'Computer vision not active'
      });
    }
    
    // Simulate frame processing with realistic biomechanical analysis
    const processingStartTime = process.hrtime.bigint();
    
    // Simulate pose detection
    const detections = [
      {
        bbox: [100, 50, 300, 450],
        confidence: 0.85 + Math.random() * 0.15,
        keypoints: generateRealisticKeypoints()
      }
    ];
    
    // Simulate biomechanical analysis
    const biomechanicalAnalysis = generateBiomechanicalAnalysis(detections[0]);
    
    const processingEndTime = process.hrtime.bigint();
    const processingTimeMs = Number(processingEndTime - processingStartTime) / 1000000;
    
    // Store analysis
    visionData.currentAnalysis = biomechanicalAnalysis;
    visionData.detectionHistory.push({
      timestamp: timestamp,
      sessionId: sessionId,
      detections: detections,
      analysis: biomechanicalAnalysis,
      processingTime: processingTimeMs
    });
    
    // Keep only recent history
    if (visionData.detectionHistory.length > 1000) {
      visionData.detectionHistory = visionData.detectionHistory.slice(-1000);
    }
    
    res.json({
      success: true,
      detections: detections,
      biomechanicalAnalysis: biomechanicalAnalysis,
      processingTime: processingTimeMs,
      precision: {
        gpsIntegrated: gpsData.connected,
        combinedPrecision: gpsData.connected ? 
          (gpsData.precisionScore * 0.6 + biomechanicalAnalysis.visionConfidence * 0.4) :
          biomechanicalAnalysis.visionConfidence
      }
    });
    
  } catch (error) {
    console.error('Frame processing error:', error);
    res.status(500).json({
      success: false,
      error: 'Frame processing failed',
      message: error.message
    });
  }
});

router.get('/vision/metrics', async (req, res) => {
  try {
    res.json({
      success: true,
      metrics: {
        active: visionData.active,
        totalDetections: visionData.detectionHistory.length,
        averageProcessingTime: visionData.detectionHistory.length > 0 ?
          visionData.detectionHistory.reduce((sum, item) => sum + item.processingTime, 0) / visionData.detectionHistory.length :
          0,
        currentAnalysis: visionData.currentAnalysis,
        gpsIntegration: {
          enabled: gpsData.connected,
          precisionScore: gpsData.precisionScore,
          calibrationPoints: gpsData.calibrationPoints.length
        }
      }
    });
    
  } catch (error) {
    console.error('Vision metrics error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get vision metrics',
      message: error.message
    });
  }
});

// Helper Functions

function generateRealisticKeypoints() {
  // Generate realistic human pose keypoints
  const baseWidth = 200;
  const baseHeight = 400;
  const centerX = 200;
  const centerY = 250;
  
  return {
    head: [centerX, centerY - baseHeight/2 + 30],
    neck: [centerX, centerY - baseHeight/2 + 60],
    left_shoulder: [centerX - baseWidth/3, centerY - baseHeight/2 + 80],
    right_shoulder: [centerX + baseWidth/3, centerY - baseHeight/2 + 80],
    left_elbow: [centerX - baseWidth/2.5, centerY - baseHeight/2 + 140],
    right_elbow: [centerX + baseWidth/2.5, centerY - baseHeight/2 + 140],
    left_wrist: [centerX - baseWidth/2, centerY - baseHeight/2 + 200],
    right_wrist: [centerX + baseWidth/2, centerY - baseHeight/2 + 200],
    torso: [centerX, centerY],
    left_hip: [centerX - baseWidth/4, centerY + baseHeight/4],
    right_hip: [centerX + baseWidth/4, centerY + baseHeight/4],
    left_knee: [centerX - baseWidth/5, centerY + baseHeight/2],
    right_knee: [centerX + baseWidth/5, centerY + baseHeight/2],
    left_ankle: [centerX - baseWidth/6, centerY + baseHeight/2 + 80],
    right_ankle: [centerX + baseWidth/6, centerY + baseHeight/2 + 80]
  };
}

function generateBiomechanicalAnalysis(detection) {
  // Generate realistic biomechanical analysis
  const keypoints = detection.keypoints;
  
  // Calculate joint angles
  const jointAngles = {
    left_knee: 110 + Math.random() * 40,
    right_knee: 115 + Math.random() * 35,
    left_elbow: 90 + Math.random() * 60,
    right_elbow: 95 + Math.random() * 55,
    left_hip: 140 + Math.random() * 30,
    right_hip: 142 + Math.random() * 28,
    left_shoulder: 75 + Math.random() * 50,
    right_shoulder: 80 + Math.random() * 45
  };
  
  // Calculate joint velocities (simulated)
  const jointVelocities = {};
  Object.keys(jointAngles).forEach(joint => {
    jointVelocities[joint] = (Math.random() - 0.5) * 50; // degrees/second
  });
  
  // Force vectors (simulated)
  const forceVectors = {
    ground_reaction: [0, 0, 650 + Math.random() * 100],
    left_knee: [Math.random() * 20 - 10, Math.random() * 20 - 10, Math.random() * 50],
    right_knee: [Math.random() * 20 - 10, Math.random() * 20 - 10, Math.random() * 50],
    left_hip: [Math.random() * 30 - 15, Math.random() * 30 - 15, Math.random() * 80],
    right_hip: [Math.random() * 30 - 15, Math.random() * 30 - 15, Math.random() * 80]
  };
  
  // Center of mass calculation
  const centerOfMass = [
    keypoints.torso[0] + (Math.random() - 0.5) * 10,
    keypoints.torso[1] + (Math.random() - 0.5) * 10,
    0 // Would be calculated from GPS altitude
  ];
  
  // Balance metrics
  const footSeparation = Math.abs(keypoints.left_ankle[0] - keypoints.right_ankle[0]);
  const comCopDistance = Math.sqrt(
    Math.pow(centerOfMass[0] - (keypoints.left_ankle[0] + keypoints.right_ankle[0])/2, 2) +
    Math.pow(centerOfMass[1] - (keypoints.left_ankle[1] + keypoints.right_ankle[1])/2, 2)
  );
  
  const balanceMetrics = {
    foot_separation: footSeparation,
    com_cop_distance: comCopDistance,
    balance_score: Math.max(0, 1.0 - comCopDistance / 100.0)
  };
  
  // Movement metrics
  const movementEfficiency = 0.6 + Math.random() * 0.3;
  const powerOutput = 200 + Math.random() * 400;
  const stabilityScore = 0.5 + Math.random() * 0.4;
  const techniqueScore = 0.4 + Math.random() * 0.5;
  
  // Movement classification
  const movementTypes = ['stationary', 'walking', 'running', 'jumping', 'kicking'];
  const movementType = movementTypes[Math.floor(Math.random() * movementTypes.length)];
  
  return {
    jointAngles: jointAngles,
    jointVelocities: jointVelocities,
    jointAccelerations: {}, // Would calculate from velocity history
    forceVectors: forceVectors,
    centerOfMass: centerOfMass,
    balanceMetrics: balanceMetrics,
    movementEfficiency: movementEfficiency,
    powerOutput: powerOutput,
    stabilityScore: stabilityScore,
    techniqueScore: techniqueScore,
    movementType: movementType,
    gpsAccuracy: gpsData.connected ? gpsData.precisionScore : 0,
    visionConfidence: detection.confidence,
    combinedPrecision: gpsData.connected ? 
      (gpsData.precisionScore * 0.6 + detection.confidence * 0.4) :
      detection.confidence,
    timestamp: Date.now() * 1000000
  };
}

// Export data endpoints
router.get('/export/precision-data', async (req, res) => {
  try {
    const { startTime, endTime } = req.query;
    const startTimeNs = parseInt(startTime) || 0;
    const endTimeNs = parseInt(endTime) || Date.now() * 1000000;
    
    // Filter data by time range
    const filteredDetections = visionData.detectionHistory.filter(item => 
      item.timestamp >= startTimeNs && item.timestamp <= endTimeNs
    );
    
    const exportData = {
      timeRange: {
        start_ns: startTimeNs,
        end_ns: endTimeNs,
        duration_s: (endTimeNs - startTimeNs) / 1e9
      },
      gpsData: {
        connected: gpsData.connected,
        currentPosition: gpsData.currentPosition,
        precisionScore: gpsData.precisionScore,
        calibrationPoints: gpsData.calibrationPoints
      },
      visionData: {
        detections: filteredDetections,
        totalDetections: filteredDetections.length,
        averageConfidence: filteredDetections.length > 0 ?
          filteredDetections.reduce((sum, item) => sum + item.detections[0]?.confidence || 0, 0) / filteredDetections.length :
          0
      },
      systemMetrics: {
        gpsVisionIntegration: gpsData.connected && visionData.active,
        overallPrecision: gpsData.connected ? 
          (gpsData.precisionScore * 0.6 + (visionData.currentAnalysis?.visionConfidence || 0) * 0.4) :
          (visionData.currentAnalysis?.visionConfidence || 0)
      }
    };
    
    res.json({
      success: true,
      data: exportData
    });
    
  } catch (error) {
    console.error('Export data error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to export precision data',
      message: error.message
    });
  }
});

module.exports = router; 