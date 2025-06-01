const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');

// In-memory storage for demo (would use proper database in production)
let marketplaceData = {
  models: new Map(),
  listings: new Map(),
  purchases: new Map(),
  userModels: new Map(),
  userPurchases: new Map(),
  userEarnings: new Map(),
  validationHistory: new Map(),
  expertEndorsements: new Map()
};

// Platform configuration
const PLATFORM_CONFIG = {
  platformFeeRate: 0.15, // 15% platform fee
  minValidationForMarketplace: 3,
  minSuccessRateForMarketplace: 0.6,
  expertBonusMultiplier: 1.5,
  volumeBonusThreshold: 10000 // $10,000 in sales
};

// Model Types and Pricing Ranges
const MODEL_TYPES = {
  single_analysis: { basePrice: 5, maxPrice: 50, description: "One-time movement analysis" },
  player_profile: { basePrice: 50, maxPrice: 500, description: "Comprehensive player analysis" },
  technique_template: { basePrice: 100, maxPrice: 1000, description: "Reusable technique framework" },
  prediction_engine: { basePrice: 200, maxPrice: 5000, description: "Validated prediction model" }
};

// Create biomechanical model from Spectacular session
router.post('/create-model', async (req, res) => {
  try {
    const {
      title,
      description,
      price,
      type,
      annotations,
      movementType,
      gpsData,
      analysisQuality,
      userId = 'demo_user'
    } = req.body;

    // Validate input
    if (!title || !description || !type || !annotations) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields',
        required: ['title', 'description', 'type', 'annotations']
      });
    }

    if (!MODEL_TYPES[type]) {
      return res.status(400).json({
        success: false,
        error: 'Invalid model type',
        validTypes: Object.keys(MODEL_TYPES)
      });
    }

    // Generate model ID
    const modelId = `model_${uuidv4().substring(0, 12)}`;
    
    // Extract biomechanical insights from annotations
    const analysisData = extractBiomechanicalInsights(annotations, gpsData);
    
    // Calculate model quality score
    const qualityScore = calculateModelQuality(analysisData, analysisQuality, annotations);
    
    // Suggest optimal pricing
    const suggestedPrice = suggestOptimalPricing(type, qualityScore, analysisData);
    const finalPrice = price || suggestedPrice;

    // Create model
    const model = {
      modelId,
      creatorUserId: userId,
      type,
      status: 'draft',
      title,
      description,
      movementTypes: [movementType],
      analysisData,
      
      // Validation metrics
      validationCount: 0,
      successRate: 0.0,
      confidenceScore: qualityScore,
      expertEndorsements: [],
      
      // Market data
      price: finalPrice,
      suggestedPrice,
      totalSales: 0,
      totalRevenue: 0.0,
      rating: 0.0,
      reviewCount: 0,
      
      // Precision metrics
      gpsAccuracy: gpsData?.accuracy || 0,
      analysisQuality: analysisQuality || 0,
      combinedPrecision: calculateCombinedPrecision(gpsData, analysisQuality),
      
      // Metadata
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      tags: generateModelTags(movementType, analysisData)
    };

    // Store model
    marketplaceData.models.set(modelId, model);
    
    // Update user models
    if (!marketplaceData.userModels.has(userId)) {
      marketplaceData.userModels.set(userId, []);
    }
    marketplaceData.userModels.get(userId).push(modelId);

    // Check if model is ready for marketplace
    const marketplaceReady = assessMarketplaceReadiness(model);
    
    res.json({
      success: true,
      modelId,
      model: {
        ...model,
        marketplaceReady,
        nextSteps: marketplaceReady ? 
          ['Create marketplace listing', 'Set pricing strategy', 'Add promotional content'] :
          ['Validate through betting', 'Gather expert endorsements', 'Improve analysis quality']
      },
      marketplace: {
        suggestedPrice,
        qualityScore,
        estimatedEarnings: calculateEstimatedEarnings(finalPrice, qualityScore)
      }
    });

  } catch (error) {
    console.error('Model creation error:', error);
    res.status(500).json({
      success: false,
      error: 'Model creation failed',
      message: error.message
    });
  }
});

// Validate model through betting success
router.post('/validate-model/:modelId', async (req, res) => {
  try {
    const { modelId } = req.params;
    const { predictionSuccess, predictionAccuracy, betOutcome } = req.body;

    if (!marketplaceData.models.has(modelId)) {
      return res.status(404).json({
        success: false,
        error: 'Model not found'
      });
    }

    const model = marketplaceData.models.get(modelId);
    
    // Update validation metrics
    model.validationCount += 1;
    
    // Update success rate
    const previousTotal = (model.validationCount - 1) * model.successRate;
    model.successRate = (previousTotal + (predictionSuccess ? 1 : 0)) / model.validationCount;
    
    // Update confidence score based on accuracy
    model.confidenceScore = (model.confidenceScore * 0.7) + (predictionAccuracy * 0.3);
    
    // Store validation record
    const validationRecord = {
      timestamp: new Date().toISOString(),
      predictionSuccess,
      predictionAccuracy,
      betOutcome,
      modelVersion: model.updatedAt
    };
    
    if (!marketplaceData.validationHistory.has(modelId)) {
      marketplaceData.validationHistory.set(modelId, []);
    }
    marketplaceData.validationHistory.get(modelId).push(validationRecord);
    
    // Update model status based on validation
    if (model.validationCount >= PLATFORM_CONFIG.minValidationForMarketplace && 
        model.successRate >= PLATFORM_CONFIG.minSuccessRateForMarketplace) {
      model.status = 'validated';
    }
    
    model.updatedAt = new Date().toISOString();
    marketplaceData.models.set(modelId, model);

    // Calculate bonus for successful validation
    let validationBonus = 0;
    if (predictionSuccess) {
      validationBonus = calculateValidationBonus(model, betOutcome);
      
      // Add to user earnings
      const userId = model.creatorUserId;
      const currentEarnings = marketplaceData.userEarnings.get(userId) || 0;
      marketplaceData.userEarnings.set(userId, currentEarnings + validationBonus);
    }

    res.json({
      success: true,
      modelId,
      validation: {
        validationCount: model.validationCount,
        successRate: model.successRate,
        confidenceScore: model.confidenceScore,
        status: model.status,
        validationBonus,
        marketplaceReady: assessMarketplaceReadiness(model)
      }
    });

  } catch (error) {
    console.error('Model validation error:', error);
    res.status(500).json({
      success: false,
      error: 'Model validation failed',
      message: error.message
    });
  }
});

// Create marketplace listing
router.post('/create-listing', async (req, res) => {
  try {
    const {
      modelId,
      listingType = 'one_time_purchase',
      basePrice,
      subscriptionPrice,
      licenseTerms,
      featured = false,
      userId = 'demo_user'
    } = req.body;

    if (!marketplaceData.models.has(modelId)) {
      return res.status(404).json({
        success: false,
        error: 'Model not found'
      });
    }

    const model = marketplaceData.models.get(modelId);
    
    // Check if user owns the model
    if (model.creatorUserId !== userId) {
      return res.status(403).json({
        success: false,
        error: 'Not authorized to create listing for this model'
      });
    }

    // Check if model is ready for marketplace
    if (!assessMarketplaceReadiness(model)) {
      return res.status(400).json({
        success: false,
        error: 'Model not ready for marketplace',
        requirements: {
          minValidations: PLATFORM_CONFIG.minValidationForMarketplace,
          minSuccessRate: PLATFORM_CONFIG.minSuccessRateForMarketplace,
          currentValidations: model.validationCount,
          currentSuccessRate: model.successRate
        }
      });
    }

    const listingId = `listing_${uuidv4().substring(0, 12)}`;
    
    const listing = {
      listingId,
      modelId,
      sellerUserId: userId,
      listingType,
      basePrice: basePrice || model.price,
      subscriptionPrice,
      licenseTerms,
      featured,
      active: true,
      
      // Performance tracking
      viewCount: 0,
      purchaseCount: 0,
      conversionRate: 0.0,
      averageRating: 0.0,
      
      createdAt: new Date().toISOString()
    };

    marketplaceData.listings.set(listingId, listing);
    
    // Update model status
    model.status = 'marketplace_ready';
    model.updatedAt = new Date().toISOString();
    marketplaceData.models.set(modelId, model);

    res.json({
      success: true,
      listingId,
      listing,
      estimatedMetrics: {
        expectedViews: calculateExpectedViews(model, listing),
        expectedSales: calculateExpectedSales(model, listing),
        estimatedRevenue: calculateEstimatedRevenue(model, listing)
      }
    });

  } catch (error) {
    console.error('Listing creation error:', error);
    res.status(500).json({
      success: false,
      error: 'Listing creation failed',
      message: error.message
    });
  }
});

// Purchase model
router.post('/purchase/:listingId', async (req, res) => {
  try {
    const { listingId } = req.params;
    const { buyerUserId = 'demo_buyer', accessDuration = null } = req.body;

    if (!marketplaceData.listings.has(listingId)) {
      return res.status(404).json({
        success: false,
        error: 'Listing not found'
      });
    }

    const listing = marketplaceData.listings.get(listingId);
    const model = marketplaceData.models.get(listing.modelId);

    if (!listing.active) {
      return res.status(400).json({
        success: false,
        error: 'Listing is not active'
      });
    }

    const purchaseId = `purchase_${uuidv4().substring(0, 12)}`;
    
    // Calculate pricing
    const pricePaid = listing.listingType === 'subscription' ? 
      listing.subscriptionPrice : listing.basePrice;
    const platformFee = pricePaid * PLATFORM_CONFIG.platformFeeRate;
    const sellerRevenue = pricePaid - platformFee;

    // Calculate access expiration
    let accessExpiresAt = null;
    if (listing.listingType === 'subscription') {
      accessExpiresAt = new Date();
      accessExpiresAt.setMonth(accessExpiresAt.getMonth() + 1);
    } else if (listing.listingType === 'rent' && accessDuration) {
      accessExpiresAt = new Date();
      accessExpiresAt.setHours(accessExpiresAt.getHours() + accessDuration);
    }

    const purchase = {
      purchaseId,
      buyerUserId,
      modelId: listing.modelId,
      sellerUserId: listing.sellerUserId,
      listingType: listing.listingType,
      
      // Transaction details
      pricePaid,
      platformFee,
      sellerRevenue,
      
      // Access details
      accessGrantedAt: new Date().toISOString(),
      accessExpiresAt: accessExpiresAt?.toISOString(),
      usageCount: 0,
      
      // Feedback
      rating: null,
      review: null,
      
      createdAt: new Date().toISOString()
    };

    marketplaceData.purchases.set(purchaseId, purchase);
    
    // Update user purchases
    if (!marketplaceData.userPurchases.has(buyerUserId)) {
      marketplaceData.userPurchases.set(buyerUserId, []);
    }
    marketplaceData.userPurchases.get(buyerUserId).push(purchaseId);
    
    // Update seller earnings
    const currentEarnings = marketplaceData.userEarnings.get(listing.sellerUserId) || 0;
    marketplaceData.userEarnings.set(listing.sellerUserId, currentEarnings + sellerRevenue);
    
    // Update listing metrics
    listing.purchaseCount += 1;
    listing.conversionRate = listing.viewCount > 0 ? 
      listing.purchaseCount / listing.viewCount : 0;
    marketplaceData.listings.set(listingId, listing);
    
    // Update model metrics
    model.totalSales += 1;
    model.totalRevenue += pricePaid;
    model.updatedAt = new Date().toISOString();
    marketplaceData.models.set(listing.modelId, model);

    res.json({
      success: true,
      purchaseId,
      purchase: {
        ...purchase,
        modelAccess: {
          analysisData: model.analysisData,
          movementTypes: model.movementTypes,
          qualityScore: model.confidenceScore,
          validationHistory: marketplaceData.validationHistory.get(listing.modelId) || []
        }
      },
      seller: {
        earnings: sellerRevenue,
        totalEarnings: marketplaceData.userEarnings.get(listing.sellerUserId)
      }
    });

  } catch (error) {
    console.error('Purchase error:', error);
    res.status(500).json({
      success: false,
      error: 'Purchase failed',
      message: error.message
    });
  }
});

// Get marketplace feed
router.get('/feed', async (req, res) => {
  try {
    const {
      userId = 'demo_user',
      category = 'all',
      sortBy = 'trending',
      limit = 20,
      offset = 0
    } = req.query;

    let listings = Array.from(marketplaceData.listings.values())
      .filter(listing => listing.active);

    // Apply category filter
    if (category !== 'all') {
      listings = listings.filter(listing => {
        const model = marketplaceData.models.get(listing.modelId);
        return model.movementTypes.includes(category);
      });
    }

    // Sort listings
    listings = sortListings(listings, sortBy);

    // Add model data to listings
    const enrichedListings = listings.slice(offset, offset + limit).map(listing => {
      const model = marketplaceData.models.get(listing.modelId);
      return {
        ...listing,
        model: {
          title: model.title,
          description: model.description,
          type: model.type,
          movementTypes: model.movementTypes,
          rating: model.rating,
          reviewCount: model.reviewCount,
          totalSales: model.totalSales,
          qualityScore: model.confidenceScore,
          tags: model.tags,
          createdAt: model.createdAt
        },
        creator: {
          userId: model.creatorUserId,
          expertiseLevel: calculateExpertiseLevel(model.creatorUserId),
          totalModels: (marketplaceData.userModels.get(model.creatorUserId) || []).length,
          totalEarnings: marketplaceData.userEarnings.get(model.creatorUserId) || 0
        }
      };
    });

    // Get personalized recommendations
    const recommendations = generatePersonalizedRecommendations(userId, enrichedListings);

    res.json({
      success: true,
      feed: {
        listings: enrichedListings,
        recommendations,
        totalCount: listings.length,
        hasMore: offset + limit < listings.length,
        categories: getAvailableCategories(),
        sortOptions: ['trending', 'newest', 'price_low', 'price_high', 'rating', 'sales']
      }
    });

  } catch (error) {
    console.error('Feed error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get marketplace feed',
      message: error.message
    });
  }
});

// Get user portfolio
router.get('/portfolio/:userId', async (req, res) => {
  try {
    const { userId } = req.params;

    const userModels = marketplaceData.userModels.get(userId) || [];
    const userPurchases = marketplaceData.userPurchases.get(userId) || [];
    const totalEarnings = marketplaceData.userEarnings.get(userId) || 0;

    // Get model details
    const models = userModels.map(modelId => {
      const model = marketplaceData.models.get(modelId);
      const listings = Array.from(marketplaceData.listings.values())
        .filter(listing => listing.modelId === modelId);
      
      return {
        ...model,
        listings,
        validationHistory: marketplaceData.validationHistory.get(modelId) || []
      };
    });

    // Get purchase details
    const purchases = userPurchases.map(purchaseId => {
      const purchase = marketplaceData.purchases.get(purchaseId);
      const model = marketplaceData.models.get(purchase.modelId);
      return {
        ...purchase,
        modelTitle: model.title,
        modelType: model.type
      };
    });

    // Calculate portfolio metrics
    const portfolioMetrics = calculatePortfolioMetrics(models, purchases, totalEarnings);

    res.json({
      success: true,
      portfolio: {
        user: {
          userId,
          expertiseLevel: calculateExpertiseLevel(userId),
          memberSince: models.length > 0 ? models[0].createdAt : new Date().toISOString()
        },
        models: {
          created: models,
          totalCount: models.length,
          totalRevenue: models.reduce((sum, model) => sum + model.totalRevenue, 0)
        },
        purchases: {
          bought: purchases,
          totalCount: purchases.length,
          totalSpent: purchases.reduce((sum, purchase) => sum + purchase.pricePaid, 0)
        },
        earnings: {
          total: totalEarnings,
          breakdown: calculateEarningsBreakdown(userId),
          trends: calculateEarningsTrends(userId)
        },
        metrics: portfolioMetrics
      }
    });

  } catch (error) {
    console.error('Portfolio error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get user portfolio',
      message: error.message
    });
  }
});

// Helper Functions

function extractBiomechanicalInsights(annotations, gpsData) {
  const insights = {
    jointSequence: annotations.filter(a => a.type === 'joint').map(a => a.data.joint),
    muscleActivation: annotations.filter(a => a.type === 'muscle').map(a => a.data),
    phaseBreakdown: annotations.reduce((acc, a) => {
      if (a.data.phase) {
        if (!acc[a.data.phase]) acc[a.data.phase] = [];
        acc[a.data.phase].push(a);
      }
      return acc;
    }, {}),
    userObservations: annotations.map(a => a.userInsight).filter(Boolean),
    gpsIntegration: gpsData ? {
      precision: gpsData.accuracy,
      coordinates: [gpsData.latitude, gpsData.longitude, gpsData.altitude],
      timestamp: gpsData.timestamp
    } : null
  };

  return insights;
}

function calculateModelQuality(analysisData, analysisQuality, annotations) {
  let score = 0.5; // Base score

  // GPS integration bonus
  if (analysisData.gpsIntegration) {
    score += 0.2 * (1 - analysisData.gpsIntegration.precision);
  }

  // Annotation richness
  score += Math.min(0.2, annotations.length * 0.02);

  // Analysis quality from computer vision
  if (analysisQuality) {
    score += analysisQuality * 0.3;
  }

  // User insight quality
  const insightfulAnnotations = annotations.filter(a => 
    a.userInsight && a.userInsight.length > 20
  ).length;
  score += Math.min(0.2, insightfulAnnotations * 0.05);

  return Math.min(1.0, Math.max(0.0, score));
}

function suggestOptimalPricing(type, qualityScore, analysisData) {
  const baseRange = MODEL_TYPES[type];
  const qualityMultiplier = 0.5 + (qualityScore * 1.0);
  const gpsBonus = analysisData.gpsIntegration ? 1.3 : 1.0;
  
  const suggestedPrice = Math.round(
    baseRange.basePrice * qualityMultiplier * gpsBonus
  );

  return Math.min(suggestedPrice, baseRange.maxPrice);
}

function calculateCombinedPrecision(gpsData, analysisQuality) {
  if (!gpsData) return analysisQuality || 0;
  
  const gpsScore = 1 - (gpsData.accuracy || 1); // Lower accuracy = higher score
  return (gpsScore * 0.6) + ((analysisQuality || 0) * 0.4);
}

function generateModelTags(movementType, analysisData) {
  const tags = [movementType];
  
  if (analysisData.gpsIntegration) {
    tags.push('gps-enhanced', 'precision-tracking');
  }
  
  if (analysisData.jointSequence.length > 5) {
    tags.push('detailed-analysis');
  }
  
  if (analysisData.userObservations.length > 2) {
    tags.push('expert-insights');
  }

  return tags;
}

function assessMarketplaceReadiness(model) {
  return model.validationCount >= PLATFORM_CONFIG.minValidationForMarketplace &&
         model.successRate >= PLATFORM_CONFIG.minSuccessRateForMarketplace;
}

function calculateEstimatedEarnings(price, qualityScore) {
  const baseSales = 10; // Base expected sales
  const qualityMultiplier = 1 + qualityScore;
  const estimatedSales = Math.round(baseSales * qualityMultiplier);
  const grossRevenue = estimatedSales * price;
  const netRevenue = grossRevenue * (1 - PLATFORM_CONFIG.platformFeeRate);
  
  return {
    estimatedSales,
    grossRevenue,
    netRevenue,
    platformFee: grossRevenue - netRevenue
  };
}

function calculateValidationBonus(model, betOutcome) {
  const baseBonus = 10; // $10 base
  const confidenceMultiplier = model.confidenceScore;
  const betSizeMultiplier = Math.min(2.0, (betOutcome.amount || 100) / 100);
  
  return Math.round(baseBonus * confidenceMultiplier * betSizeMultiplier);
}

function sortListings(listings, sortBy) {
  switch (sortBy) {
    case 'newest':
      return listings.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    case 'price_low':
      return listings.sort((a, b) => a.basePrice - b.basePrice);
    case 'price_high':
      return listings.sort((a, b) => b.basePrice - a.basePrice);
    case 'rating':
      return listings.sort((a, b) => b.averageRating - a.averageRating);
    case 'sales':
      return listings.sort((a, b) => b.purchaseCount - a.purchaseCount);
    case 'trending':
    default:
      return listings.sort((a, b) => {
        const scoreA = (a.purchaseCount * 2) + a.viewCount + (a.averageRating * 10);
        const scoreB = (b.purchaseCount * 2) + b.viewCount + (b.averageRating * 10);
        return scoreB - scoreA;
      });
  }
}

function calculateExpertiseLevel(userId) {
  const userModels = marketplaceData.userModels.get(userId) || [];
  const totalEarnings = marketplaceData.userEarnings.get(userId) || 0;
  
  if (totalEarnings > 10000) return 'expert';
  if (totalEarnings > 1000) return 'intermediate';
  if (userModels.length > 5) return 'developing';
  return 'beginner';
}

function generatePersonalizedRecommendations(userId, listings) {
  // Simple recommendation based on user's models and purchases
  const userModels = marketplaceData.userModels.get(userId) || [];
  const userPurchases = marketplaceData.userPurchases.get(userId) || [];
  
  // Get user's interests from their model types
  const userInterests = userModels.map(modelId => {
    const model = marketplaceData.models.get(modelId);
    return model.movementTypes;
  }).flat();
  
  // Recommend similar models
  return listings
    .filter(listing => {
      const model = marketplaceData.models.get(listing.modelId);
      return model.movementTypes.some(type => userInterests.includes(type));
    })
    .slice(0, 5);
}

function getAvailableCategories() {
  const categories = new Set();
  marketplaceData.models.forEach(model => {
    model.movementTypes.forEach(type => categories.add(type));
  });
  return Array.from(categories);
}

function calculatePortfolioMetrics(models, purchases, totalEarnings) {
  return {
    totalModels: models.length,
    validatedModels: models.filter(m => m.status === 'validated').length,
    averageModelRating: models.length > 0 ? 
      models.reduce((sum, m) => sum + m.rating, 0) / models.length : 0,
    totalSales: models.reduce((sum, m) => sum + m.totalSales, 0),
    conversionRate: models.length > 0 ? 
      models.reduce((sum, m) => sum + (m.totalSales / Math.max(1, m.viewCount || 1)), 0) / models.length : 0,
    earningsGrowth: calculateEarningsGrowth(totalEarnings),
    expertiseScore: calculateExpertiseScore(models, totalEarnings)
  };
}

function calculateEarningsBreakdown(userId) {
  // Simplified breakdown
  const totalEarnings = marketplaceData.userEarnings.get(userId) || 0;
  return {
    modelSales: totalEarnings * 0.8,
    validationBonuses: totalEarnings * 0.15,
    expertBonuses: totalEarnings * 0.05
  };
}

function calculateEarningsTrends(userId) {
  // Simplified trend calculation
  return [
    { month: 'Jan', earnings: 100 },
    { month: 'Feb', earnings: 250 },
    { month: 'Mar', earnings: 400 }
  ];
}

function calculateEarningsGrowth(totalEarnings) {
  // Simplified growth calculation
  return totalEarnings > 0 ? 25.5 : 0; // 25.5% growth
}

function calculateExpertiseScore(models, totalEarnings) {
  const validatedModels = models.filter(m => m.status === 'validated').length;
  const avgSuccessRate = models.length > 0 ? 
    models.reduce((sum, m) => sum + m.successRate, 0) / models.length : 0;
  
  return Math.min(100, 
    (validatedModels * 10) + 
    (avgSuccessRate * 30) + 
    (Math.min(totalEarnings / 100, 50))
  );
}

function calculateExpectedViews(model, listing) {
  return Math.round(50 + (model.confidenceScore * 100) + (listing.featured ? 200 : 0));
}

function calculateExpectedSales(model, listing) {
  const expectedViews = calculateExpectedViews(model, listing);
  const conversionRate = 0.05 + (model.confidenceScore * 0.1);
  return Math.round(expectedViews * conversionRate);
}

function calculateEstimatedRevenue(model, listing) {
  const expectedSales = calculateExpectedSales(model, listing);
  const grossRevenue = expectedSales * listing.basePrice;
  return grossRevenue * (1 - PLATFORM_CONFIG.platformFeeRate);
}

module.exports = router; 