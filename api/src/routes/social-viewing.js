const express = require('express');
const logger = require('../utils/logger');

const router = express.Router();

// In-memory storage for demo (would use proper database in production)
let viewingRooms = new Map();
let roomPredictions = new Map();
let socialInsights = new Map();
let groupAnalytics = new Map();

// Social Viewing Room Management

router.post('/rooms/create', async (req, res) => {
  try {
    const {
      hostUserId,
      eventId,
      eventTitle,
      eventType,
      roomName,
      isPrivate,
      maxParticipants,
      sharedModels,
      collaborativeFeatures
    } = req.body;

    const roomId = `room_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const viewingRoom = {
      roomId,
      hostUserId,
      eventId,
      eventTitle,
      eventType, // "sports", "gaming", "entertainment", "live_event"
      roomName,
      isPrivate,
      maxParticipants: maxParticipants || 10,
      
      participants: [{
        userId: hostUserId,
        role: 'host',
        joinedAt: Date.now(),
        contributedPredictions: 0,
        sharedInsights: 0,
        accuracy: 0
      }],
      
      sharedResources: {
        models: sharedModels || [], // Models host shares with group
        brandSpecialists: [], // Specialists in the room
        premiumInsights: [], // Paid insights shared
        analyticsAccess: false
      },
      
      collaborativeFeatures: {
        realTimeChat: collaborativeFeatures.realTimeChat || true,
        predictionSharing: collaborativeFeatures.predictionSharing || true,
        modelSharing: collaborativeFeatures.modelSharing || true,
        groupChallenges: collaborativeFeatures.groupChallenges || true,
        collectiveInsights: collaborativeFeatures.collectiveInsights || true
      },
      
      roomStats: {
        totalPredictions: 0,
        correctPredictions: 0,
        groupAccuracy: 0,
        mostActivePredictor: null,
        bestPerformer: null,
        insightCount: 0
      },
      
      currentEvent: {
        isLive: false,
        currentMoment: null,
        activePredictions: [],
        recentInsights: []
      },
      
      status: 'active',
      createdAt: Date.now()
    };

    viewingRooms.set(roomId, viewingRoom);
    roomPredictions.set(roomId, []);
    
    res.json({
      success: true,
      roomId,
      room: viewingRoom,
      joinUrl: `/join-room/${roomId}`,
      message: `Viewing room "${roomName}" created successfully`
    });

  } catch (error) {
    console.error('Room creation error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create viewing room',
      message: error.message
    });
  }
});

// Join Viewing Room

router.post('/rooms/:roomId/join', async (req, res) => {
  try {
    const { roomId } = req.params;
    const { userId, displayName, userModels, expertise } = req.body;

    const room = viewingRooms.get(roomId);
    if (!room) {
      return res.status(404).json({
        success: false,
        error: 'Room not found'
      });
    }

    if (room.participants.length >= room.maxParticipants) {
      return res.status(400).json({
        success: false,
        error: 'Room is full'
      });
    }

    // Check if user already in room
    const existingParticipant = room.participants.find(p => p.userId === userId);
    if (existingParticipant) {
      return res.status(400).json({
        success: false,
        error: 'User already in room'
      });
    }

    const participant = {
      userId,
      displayName,
      role: 'participant',
      joinedAt: Date.now(),
      contributedPredictions: 0,
      sharedInsights: 0,
      accuracy: 0,
      userModels: userModels || [], // Models they bring to share
      expertise: expertise || [] // Their areas of expertise
    };

    room.participants.push(participant);

    // Add user's models to shared resources
    if (userModels && userModels.length > 0) {
      room.sharedResources.models.push(...userModels);
    }

    res.json({
      success: true,
      participant,
      room: {
        roomId: room.roomId,
        roomName: room.roomName,
        eventTitle: room.eventTitle,
        participants: room.participants,
        sharedResources: room.sharedResources,
        currentEvent: room.currentEvent
      },
      message: `Joined room "${room.roomName}" successfully`
    });

  } catch (error) {
    console.error('Room join error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to join room',
      message: error.message
    });
  }
});

// Make Group Prediction

router.post('/rooms/:roomId/predict', async (req, res) => {
  try {
    const { roomId } = req.params;
    const {
      userId,
      predictionType,
      prediction,
      confidence,
      reasoning,
      modelUsed,
      targetMoment,
      sharingLevel // 'group_only', 'public', 'premium_share'
    } = req.body;

    const room = viewingRooms.get(roomId);
    if (!room) {
      return res.status(404).json({
        success: false,
        error: 'Room not found'
      });
    }

    const participant = room.participants.find(p => p.userId === userId);
    if (!participant) {
      return res.status(403).json({
        success: false,
        error: 'User not in room'
      });
    }

    const predictionId = `pred_${roomId}_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    
    const groupPrediction = {
      predictionId,
      roomId,
      userId,
      displayName: participant.displayName,
      predictionType, // "penalty_direction", "celebration_type", "camera_angle", etc.
      prediction,
      confidence,
      reasoning,
      modelUsed,
      targetMoment, // When this prediction is for
      sharingLevel,
      timestamp: Date.now(),
      reactions: [], // Other users' reactions
      status: 'active',
      result: null,
      accuracy: null
    };

    // Store prediction
    const roomPreds = roomPredictions.get(roomId) || [];
    roomPreds.push(groupPrediction);
    roomPredictions.set(roomId, roomPreds);

    // Update room stats
    room.roomStats.totalPredictions++;
    participant.contributedPredictions++;

    // Add to current active predictions
    room.currentEvent.activePredictions.push({
      predictionId,
      userId,
      displayName: participant.displayName,
      type: predictionType,
      summary: prediction,
      confidence
    });

    // Notify other participants (would use WebSocket in real implementation)
    const notification = {
      type: 'new_prediction',
      roomId,
      prediction: {
        displayName: participant.displayName,
        predictionType,
        prediction,
        confidence,
        reasoning,
        modelUsed
      }
    };

    res.json({
      success: true,
      predictionId,
      prediction: groupPrediction,
      roomUpdate: {
        activePredictions: room.currentEvent.activePredictions,
        totalPredictions: room.roomStats.totalPredictions
      },
      notification,
      message: 'Group prediction added successfully'
    });

  } catch (error) {
    console.error('Group prediction error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to add group prediction',
      message: error.message
    });
  }
});

// Share Insight with Group

router.post('/rooms/:roomId/share-insight', async (req, res) => {
  try {
    const { roomId } = req.params;
    const {
      userId,
      insightType,
      insight,
      supportingData,
      confidence,
      applicableToFuture
    } = req.body;

    const room = viewingRooms.get(roomId);
    if (!room) {
      return res.status(404).json({
        success: false,
        error: 'Room not found'
      });
    }

    const participant = room.participants.find(p => p.userId === userId);
    if (!participant) {
      return res.status(403).json({
        success: false,
        error: 'User not in room'
      });
    }

    const insightId = `insight_${roomId}_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    
    const sharedInsight = {
      insightId,
      roomId,
      userId,
      displayName: participant.displayName,
      insightType, // "pattern_recognition", "behavioral_analysis", "timing_prediction", etc.
      insight,
      supportingData,
      confidence,
      applicableToFuture,
      timestamp: Date.now(),
      reactions: [],
      usefulness: 0, // Rated by other participants
      predictions_helped: [] // Predictions that used this insight
    };

    // Store insight
    const roomInsights = socialInsights.get(roomId) || [];
    roomInsights.push(sharedInsight);
    socialInsights.set(roomId, roomInsights);

    // Update participant stats
    participant.sharedInsights++;
    room.roomStats.insightCount++;

    // Add to recent insights
    room.currentEvent.recentInsights.unshift(sharedInsight);
    if (room.currentEvent.recentInsights.length > 10) {
      room.currentEvent.recentInsights = room.currentEvent.recentInsights.slice(0, 10);
    }

    res.json({
      success: true,
      insightId,
      insight: sharedInsight,
      roomUpdate: {
        recentInsights: room.currentEvent.recentInsights,
        insightCount: room.roomStats.insightCount
      },
      message: 'Insight shared with group successfully'
    });

  } catch (error) {
    console.error('Share insight error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to share insight',
      message: error.message
    });
  }
});

// Get Live Room State

router.get('/rooms/:roomId/live-state', async (req, res) => {
  try {
    const { roomId } = req.params;
    
    const room = viewingRooms.get(roomId);
    if (!room) {
      return res.status(404).json({
        success: false,
        error: 'Room not found'
      });
    }

    const recentPredictions = roomPredictions.get(roomId) || [];
    const recentInsights = socialInsights.get(roomId) || [];
    
    // Get live predictions for current moment
    const livePredictions = recentPredictions
      .filter(pred => pred.status === 'active')
      .slice(-20) // Last 20 predictions
      .map(pred => ({
        displayName: pred.displayName,
        predictionType: pred.predictionType,
        prediction: pred.prediction,
        confidence: pred.confidence,
        reasoning: pred.reasoning,
        modelUsed: pred.modelUsed,
        timestamp: pred.timestamp
      }));

    // Get live insights
    const liveInsights = recentInsights
      .slice(-10) // Last 10 insights
      .map(insight => ({
        displayName: insight.displayName,
        insightType: insight.insightType,
        insight: insight.insight,
        confidence: insight.confidence,
        timestamp: insight.timestamp,
        usefulness: insight.usefulness
      }));

    // Calculate group dynamics
    const groupDynamics = calculateGroupDynamics(room, recentPredictions, recentInsights);

    res.json({
      success: true,
      roomState: {
        roomInfo: {
          roomId: room.roomId,
          roomName: room.roomName,
          eventTitle: room.eventTitle,
          participantCount: room.participants.length
        },
        participants: room.participants.map(p => ({
          displayName: p.displayName,
          contributedPredictions: p.contributedPredictions,
          sharedInsights: p.sharedInsights,
          accuracy: p.accuracy,
          expertise: p.expertise
        })),
        livePredictions,
        liveInsights,
        groupDynamics,
        sharedResources: room.sharedResources,
        roomStats: room.roomStats
      }
    });

  } catch (error) {
    console.error('Live state error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get live room state',
      message: error.message
    });
  }
});

// React to Prediction/Insight

router.post('/rooms/:roomId/react', async (req, res) => {
  try {
    const { roomId } = req.params;
    const {
      userId,
      targetId, // predictionId or insightId
      targetType, // 'prediction' or 'insight'
      reactionType, // 'agree', 'disagree', 'brilliant', 'doubt', 'build_on'
      comment
    } = req.body;

    const room = viewingRooms.get(roomId);
    if (!room) {
      return res.status(404).json({
        success: false,
        error: 'Room not found'
      });
    }

    const participant = room.participants.find(p => p.userId === userId);
    if (!participant) {
      return res.status(403).json({
        success: false,
        error: 'User not in room'
      });
    }

    const reaction = {
      userId,
      displayName: participant.displayName,
      reactionType,
      comment,
      timestamp: Date.now()
    };

    // Add reaction to target
    if (targetType === 'prediction') {
      const predictions = roomPredictions.get(roomId) || [];
      const prediction = predictions.find(p => p.predictionId === targetId);
      if (prediction) {
        prediction.reactions.push(reaction);
      }
    } else if (targetType === 'insight') {
      const insights = socialInsights.get(roomId) || [];
      const insight = insights.find(i => i.insightId === targetId);
      if (insight) {
        insight.reactions.push(reaction);
        // Update usefulness score
        if (reactionType === 'brilliant') insight.usefulness += 2;
        else if (reactionType === 'agree') insight.usefulness += 1;
        else if (reactionType === 'disagree') insight.usefulness -= 1;
      }
    }

    res.json({
      success: true,
      reaction,
      message: 'Reaction added successfully'
    });

  } catch (error) {
    console.error('Reaction error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to add reaction',
      message: error.message
    });
  }
});

// Group Analytics

router.get('/rooms/:roomId/analytics', async (req, res) => {
  try {
    const { roomId } = req.params;
    
    const room = viewingRooms.get(roomId);
    if (!room) {
      return res.status(404).json({
        success: false,
        error: 'Room not found'
      });
    }

    const predictions = roomPredictions.get(roomId) || [];
    const insights = socialInsights.get(roomId) || [];

    const analytics = {
      room: {
        roomId: room.roomId,
        roomName: room.roomName,
        eventTitle: room.eventTitle,
        duration: Date.now() - room.createdAt,
        participantCount: room.participants.length
      },
      
      engagement: {
        totalPredictions: predictions.length,
        totalInsights: insights.length,
        predictionsPerParticipant: predictions.length / room.participants.length,
        insightsPerParticipant: insights.length / room.participants.length,
        averageConfidence: predictions.length > 0 ? 
          predictions.reduce((sum, p) => sum + p.confidence, 0) / predictions.length : 0
      },
      
      participants: room.participants.map(participant => {
        const userPredictions = predictions.filter(p => p.userId === participant.userId);
        const userInsights = insights.filter(i => i.userId === participant.userId);
        
        return {
          displayName: participant.displayName,
          contributedPredictions: userPredictions.length,
          sharedInsights: userInsights.length,
          accuracy: calculateUserAccuracy(userPredictions),
          engagement: calculateEngagementScore(userPredictions, userInsights),
          expertise: participant.expertise,
          topPredictionTypes: getTopPredictionTypes(userPredictions)
        };
      }),
      
      insights: {
        mostUsefulInsights: insights
          .sort((a, b) => b.usefulness - a.usefulness)
          .slice(0, 5)
          .map(insight => ({
            insight: insight.insight,
            author: insight.displayName,
            usefulness: insight.usefulness,
            reactions: insight.reactions.length
          })),
        
        patternDiscoveries: extractPatternDiscoveries(insights),
        collaborativeBreakthroughs: findCollaborativeBreakthroughs(predictions, insights)
      },
      
      modelUsage: {
        sharedModels: room.sharedResources.models.length,
        modelPredictions: predictions.filter(p => p.modelUsed).length,
        topModels: getTopUsedModels(predictions)
      }
    };

    res.json({
      success: true,
      analytics
    });

  } catch (error) {
    console.error('Group analytics error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get group analytics',
      message: error.message
    });
  }
});

// Helper Functions

function calculateGroupDynamics(room, predictions, insights) {
  const participantCount = room.participants.length;
  const recentActivity = predictions.filter(p => 
    Date.now() - p.timestamp < 300000 // Last 5 minutes
  ).length;
  
  return {
    activityLevel: recentActivity > participantCount ? 'high' : 
                   recentActivity > participantCount * 0.5 ? 'medium' : 'low',
    collaborationScore: insights.length / Math.max(1, predictions.length),
    diversityScore: calculateDiversityScore(predictions),
    expertiseBalance: calculateExpertiseBalance(room.participants)
  };
}

function calculateUserAccuracy(userPredictions) {
  const completedPredictions = userPredictions.filter(p => p.accuracy !== null);
  if (completedPredictions.length === 0) return 0;
  
  return completedPredictions.reduce((sum, p) => sum + (p.accuracy ? 1 : 0), 0) / completedPredictions.length;
}

function calculateEngagementScore(predictions, insights) {
  return predictions.length * 1 + insights.length * 2; // Insights worth more
}

function getTopPredictionTypes(predictions) {
  const types = {};
  predictions.forEach(p => {
    types[p.predictionType] = (types[p.predictionType] || 0) + 1;
  });
  
  return Object.entries(types)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 3)
    .map(([type, count]) => ({ type, count }));
}

function extractPatternDiscoveries(insights) {
  return insights
    .filter(i => i.insightType === 'pattern_recognition' && i.usefulness > 2)
    .map(i => ({
      pattern: i.insight,
      author: i.displayName,
      confidence: i.confidence
    }));
}

function findCollaborativeBreakthroughs(predictions, insights) {
  // Find instances where insights led to better predictions
  return insights
    .filter(insight => insight.predictions_helped.length > 0)
    .map(insight => ({
      insight: insight.insight,
      author: insight.displayName,
      helpedPredictions: insight.predictions_helped.length,
      impact: 'collaborative_breakthrough'
    }));
}

function getTopUsedModels(predictions) {
  const models = {};
  predictions.filter(p => p.modelUsed).forEach(p => {
    models[p.modelUsed] = (models[p.modelUsed] || 0) + 1;
  });
  
  return Object.entries(models)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 5)
    .map(([model, count]) => ({ model, count }));
}

function calculateDiversityScore(predictions) {
  const types = new Set(predictions.map(p => p.predictionType));
  return types.size / Math.max(1, predictions.length);
}

function calculateExpertiseBalance(participants) {
  const allExpertise = participants.flatMap(p => p.expertise || []);
  const uniqueExpertise = new Set(allExpertise);
  return uniqueExpertise.size / Math.max(1, participants.length);
}

module.exports = router; 