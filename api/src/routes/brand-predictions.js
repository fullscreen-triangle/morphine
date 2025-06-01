const express = require('express');
const logger = require('../utils/logger');

const router = express.Router();

// In-memory storage for demo (would use proper database in production)
let brandCampaigns = new Map();
let activePredictions = new Map();
let brandAnalytics = new Map();

// Brand Campaign Management

router.post('/campaigns/create', async (req, res) => {
  try {
    const {
      brandName,
      campaignTitle,
      predictionType,
      targetContent, // what to look for
      streamId,
      duration, // campaign duration in minutes
      budget,
      payoutStructure,
      creativeBrief
    } = req.body;

    const campaignId = `brand_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const campaign = {
      campaignId,
      brandName,
      campaignTitle,
      predictionType, // "logo_count", "product_appearance", "brand_mention", "product_usage"
      targetContent,
      streamId,
      duration,
      budget,
      payoutStructure: {
        correctPrediction: payoutStructure.correctPrediction || 10,
        participationReward: payoutStructure.participationReward || 2,
        bonusMultiplier: payoutStructure.bonusMultiplier || 1.5
      },
      creativeBrief,
      status: 'active',
      createdAt: Date.now(),
      expiresAt: Date.now() + (duration * 60 * 1000),
      engagement: {
        totalPredictions: 0,
        uniqueParticipants: 0,
        averageEngagementTime: 0,
        brandMentions: 0,
        socialShares: 0
      },
      analytics: {
        impressions: 0,
        clicks: 0,
        conversions: 0,
        attentionScore: 0,
        brandRecall: 0
      }
    };

    brandCampaigns.set(campaignId, campaign);
    
    // Initialize real-time tracking
    initializeBrandTracking(campaignId, targetContent);
    
    res.json({
      success: true,
      campaignId,
      campaign,
      message: `Brand prediction campaign created for ${brandName}`,
      predictionUrl: `/predictions/brand/${campaignId}`
    });

  } catch (error) {
    console.error('Brand campaign creation error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create brand campaign',
      message: error.message
    });
  }
});

router.get('/campaigns/active', async (req, res) => {
  try {
    const { streamId } = req.query;
    
    const activeCampaigns = Array.from(brandCampaigns.values())
      .filter(campaign => 
        campaign.status === 'active' && 
        campaign.expiresAt > Date.now() &&
        (!streamId || campaign.streamId === streamId)
      )
      .map(campaign => ({
        campaignId: campaign.campaignId,
        brandName: campaign.brandName,
        campaignTitle: campaign.campaignTitle,
        predictionType: campaign.predictionType,
        targetContent: campaign.targetContent,
        duration: campaign.duration,
        payoutStructure: campaign.payoutStructure,
        engagement: campaign.engagement,
        timeRemaining: Math.max(0, campaign.expiresAt - Date.now())
      }));

    res.json({
      success: true,
      campaigns: activeCampaigns,
      totalActive: activeCampaigns.length
    });

  } catch (error) {
    console.error('Active campaigns fetch error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch active campaigns',
      message: error.message
    });
  }
});

// User Prediction Endpoints

router.post('/predict', async (req, res) => {
  try {
    const {
      campaignId,
      userId,
      prediction,
      confidence,
      timeWindow, // when they expect it to happen
      reasoning
    } = req.body;

    const campaign = brandCampaigns.get(campaignId);
    if (!campaign) {
      return res.status(404).json({
        success: false,
        error: 'Campaign not found'
      });
    }

    if (campaign.expiresAt <= Date.now()) {
      return res.status(400).json({
        success: false,
        error: 'Campaign has expired'
      });
    }

    const predictionId = `pred_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const userPrediction = {
      predictionId,
      campaignId,
      userId,
      prediction, // e.g., "7" for logo count, "yes" for appearance
      confidence,
      timeWindow,
      reasoning,
      timestamp: Date.now(),
      status: 'pending',
      result: null,
      payout: 0
    };

    activePredictions.set(predictionId, userPrediction);
    
    // Update campaign engagement
    campaign.engagement.totalPredictions++;
    if (!campaign.participantIds) campaign.participantIds = new Set();
    if (!campaign.participantIds.has(userId)) {
      campaign.engagement.uniqueParticipants++;
      campaign.participantIds.add(userId);
    }

    // Start real-time validation for this prediction
    await validatePredictionInRealTime(predictionId, campaign);

    res.json({
      success: true,
      predictionId,
      prediction: userPrediction,
      campaign: {
        brandName: campaign.brandName,
        campaignTitle: campaign.campaignTitle,
        payoutStructure: campaign.payoutStructure
      },
      message: 'Prediction submitted successfully'
    });

  } catch (error) {
    console.error('Brand prediction error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to submit prediction',
      message: error.message
    });
  }
});

router.get('/predict/:predictionId/status', async (req, res) => {
  try {
    const { predictionId } = req.params;
    
    const prediction = activePredictions.get(predictionId);
    if (!prediction) {
      return res.status(404).json({
        success: false,
        error: 'Prediction not found'
      });
    }

    const campaign = brandCampaigns.get(prediction.campaignId);
    
    res.json({
      success: true,
      prediction,
      campaign: {
        brandName: campaign.brandName,
        timeRemaining: Math.max(0, campaign.expiresAt - Date.now()),
        currentEngagement: campaign.engagement
      },
      realTimeTracking: await getRealTimeTrackingData(prediction.campaignId)
    });

  } catch (error) {
    console.error('Prediction status error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get prediction status',
      message: error.message
    });
  }
});

// Real-time Brand Tracking

async function initializeBrandTracking(campaignId, targetContent) {
  try {
    // Initialize computer vision tracking for brand elements
    const trackingData = {
      campaignId,
      targetContent,
      detectionHistory: [],
      currentCount: 0,
      lastDetection: null,
      confidenceThreshold: 0.7,
      isActive: true
    };

    brandAnalytics.set(campaignId, trackingData);
    
    // Start real-time detection (would integrate with video processing pipeline)
    console.log(`Started brand tracking for campaign ${campaignId}: ${targetContent.description}`);
    
  } catch (error) {
    console.error('Brand tracking initialization error:', error);
  }
}

async function validatePredictionInRealTime(predictionId, campaign) {
  try {
    const prediction = activePredictions.get(predictionId);
    if (!prediction) return;

    // Simulate real-time validation
    setTimeout(async () => {
      const trackingData = brandAnalytics.get(campaign.campaignId);
      if (!trackingData) return;

      // Simulate brand detection results
      const actualResult = simulateBrandDetection(campaign);
      
      // Validate prediction
      const isCorrect = validatePredictionAccuracy(prediction, actualResult);
      
      // Calculate payout
      const payout = calculateBrandPayout(prediction, campaign, isCorrect, actualResult);
      
      // Update prediction result
      prediction.status = 'completed';
      prediction.result = actualResult;
      prediction.payout = payout;
      prediction.accuracy = isCorrect;
      
      // Update campaign analytics
      updateCampaignAnalytics(campaign, prediction, actualResult);
      
      console.log(`Prediction ${predictionId} validated: ${isCorrect ? 'CORRECT' : 'INCORRECT'}, Payout: $${payout}`);
      
    }, Math.random() * 30000 + 10000); // Validate within 10-40 seconds

  } catch (error) {
    console.error('Real-time validation error:', error);
  }
}

function simulateBrandDetection(campaign) {
  // Simulate realistic brand detection results
  switch (campaign.predictionType) {
    case 'logo_count':
      return {
        type: 'logo_count',
        count: Math.floor(Math.random() * 15) + 1,
        detections: Array.from({length: Math.floor(Math.random() * 5) + 1}, () => ({
          timestamp: Date.now() - Math.random() * 60000,
          confidence: 0.7 + Math.random() * 0.3,
          location: {
            x: Math.random() * 1920,
            y: Math.random() * 1080,
            width: 50 + Math.random() * 200,
            height: 50 + Math.random() * 200
          }
        }))
      };
      
    case 'product_appearance':
      return {
        type: 'product_appearance',
        appeared: Math.random() > 0.3,
        firstAppearance: Date.now() - Math.random() * 120000,
        totalDuration: Math.random() * 45000,
        confidence: 0.8 + Math.random() * 0.2
      };
      
    case 'brand_mention':
      return {
        type: 'brand_mention',
        mentioned: Math.random() > 0.4,
        mentions: Math.floor(Math.random() * 5),
        timestamps: [],
        context: ['positive', 'neutral', 'promotional'][Math.floor(Math.random() * 3)]
      };
      
    default:
      return { type: 'unknown', result: 'inconclusive' };
  }
}

function validatePredictionAccuracy(prediction, actualResult) {
  switch (actualResult.type) {
    case 'logo_count':
      const predictedCount = parseInt(prediction.prediction);
      const actualCount = actualResult.count;
      return Math.abs(predictedCount - actualCount) <= 2; // Within 2 is considered correct
      
    case 'product_appearance':
      const predictedAppearance = prediction.prediction.toLowerCase() === 'yes';
      return predictedAppearance === actualResult.appeared;
      
    case 'brand_mention':
      const predictedMention = prediction.prediction.toLowerCase() === 'yes';
      return predictedMention === actualResult.mentioned;
      
    default:
      return false;
  }
}

function calculateBrandPayout(prediction, campaign, isCorrect, actualResult) {
  const base = campaign.payoutStructure.correctPrediction;
  const participation = campaign.payoutStructure.participationReward;
  const multiplier = campaign.payoutStructure.bonusMultiplier;
  
  let payout = participation; // Everyone gets participation reward
  
  if (isCorrect) {
    payout += base;
    
    // Bonus for high confidence correct predictions
    if (prediction.confidence > 0.8) {
      payout *= multiplier;
    }
    
    // Bonus for detailed reasoning
    if (prediction.reasoning && prediction.reasoning.length > 50) {
      payout *= 1.2;
    }
  }
  
  return Math.round(payout * 100) / 100; // Round to cents
}

function updateCampaignAnalytics(campaign, prediction, actualResult) {
  // Update engagement metrics
  campaign.analytics.impressions++;
  
  if (prediction.accuracy) {
    campaign.analytics.conversions++;
  }
  
  // Calculate attention score based on prediction accuracy
  const currentAttention = prediction.accuracy ? 1.0 : 0.3;
  campaign.analytics.attentionScore = 
    (campaign.analytics.attentionScore * (campaign.engagement.totalPredictions - 1) + currentAttention) / 
    campaign.engagement.totalPredictions;
  
  // Update brand recall (simulated)
  campaign.analytics.brandRecall = Math.min(1.0, campaign.analytics.attentionScore * 0.8 + 0.2);
}

async function getRealTimeTrackingData(campaignId) {
  const trackingData = brandAnalytics.get(campaignId);
  if (!trackingData) return null;
  
  return {
    currentDetections: trackingData.currentCount,
    lastDetection: trackingData.lastDetection,
    detectionHistory: trackingData.detectionHistory.slice(-10), // Last 10 detections
    isTracking: trackingData.isActive
  };
}

// Analytics Endpoints for Brands

router.get('/campaigns/:campaignId/analytics', async (req, res) => {
  try {
    const { campaignId } = req.params;
    
    const campaign = brandCampaigns.get(campaignId);
    if (!campaign) {
      return res.status(404).json({
        success: false,
        error: 'Campaign not found'
      });
    }

    const predictions = Array.from(activePredictions.values())
      .filter(pred => pred.campaignId === campaignId);
    
    const analytics = {
      campaign: {
        brandName: campaign.brandName,
        campaignTitle: campaign.campaignTitle,
        status: campaign.status,
        timeRemaining: Math.max(0, campaign.expiresAt - Date.now())
      },
      engagement: {
        ...campaign.engagement,
        averageConfidence: predictions.length > 0 ? 
          predictions.reduce((sum, pred) => sum + pred.confidence, 0) / predictions.length : 0,
        correctPredictions: predictions.filter(pred => pred.accuracy).length,
        accuracyRate: predictions.length > 0 ? 
          predictions.filter(pred => pred.accuracy).length / predictions.length : 0
      },
      brandMetrics: {
        ...campaign.analytics,
        brandVisibility: campaign.engagement.totalPredictions * 0.75, // Estimated views
        engagementQuality: campaign.analytics.attentionScore,
        costPerEngagement: campaign.budget / Math.max(1, campaign.engagement.totalPredictions),
        estimatedReach: campaign.engagement.uniqueParticipants * 3.2 // Social multiplier
      },
      predictions: predictions.map(pred => ({
        predictionId: pred.predictionId,
        userId: pred.userId,
        prediction: pred.prediction,
        confidence: pred.confidence,
        accuracy: pred.accuracy,
        payout: pred.payout,
        timestamp: pred.timestamp
      }))
    };

    res.json({
      success: true,
      analytics
    });

  } catch (error) {
    console.error('Campaign analytics error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch campaign analytics',
      message: error.message
    });
  }
});

router.get('/campaigns/:campaignId/roi', async (req, res) => {
  try {
    const { campaignId } = req.params;
    
    const campaign = brandCampaigns.get(campaignId);
    if (!campaign) {
      return res.status(404).json({
        success: false,
        error: 'Campaign not found'
      });
    }

    const totalPayout = Array.from(activePredictions.values())
      .filter(pred => pred.campaignId === campaignId)
      .reduce((sum, pred) => sum + pred.payout, 0);

    const roi = {
      investment: {
        campaignBudget: campaign.budget,
        totalPayout: totalPayout,
        platformFee: campaign.budget * 0.15, // 15% platform fee
        totalCost: campaign.budget + totalPayout
      },
      returns: {
        brandEngagement: campaign.engagement.totalPredictions,
        attentionMinutes: campaign.engagement.totalPredictions * 2.5, // Avg 2.5 min per prediction
        brandImpressions: campaign.analytics.impressions,
        estimatedConversions: campaign.analytics.conversions,
        brandRecallScore: campaign.analytics.brandRecall
      },
      roi: {
        engagementROI: campaign.engagement.totalPredictions / (campaign.budget / 100),
        attentionROI: (campaign.engagement.totalPredictions * 2.5) / (campaign.budget / 10),
        costPerAttentionMinute: (campaign.budget + totalPayout) / Math.max(1, campaign.engagement.totalPredictions * 2.5),
        estimatedBrandValue: campaign.analytics.brandRecall * campaign.budget * 3.5
      }
    };

    res.json({
      success: true,
      roi,
      summary: {
        totalEngagement: campaign.engagement.totalPredictions,
        totalCost: roi.investment.totalCost,
        estimatedValue: roi.roi.estimatedBrandValue,
        roiMultiplier: roi.roi.estimatedBrandValue / roi.investment.totalCost
      }
    });

  } catch (error) {
    console.error('Campaign ROI error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to calculate campaign ROI',
      message: error.message
    });
  }
});

module.exports = router; 