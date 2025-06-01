const express = require('express');
const logger = require('../utils/logger');

const router = express.Router();

// In-memory storage for demo (would use proper database in production)
let brandSpecialists = new Map();
let brandModels = new Map();
let specialistEarnings = new Map();
let brandInsights = new Map();

// Brand Specialist Registration

router.post('/specialists/register', async (req, res) => {
  try {
    const {
      userId,
      specializedBrands,
      expertise,
      credentials,
      portfolioUrl,
      pricingTiers
    } = req.body;

    const specialistId = `specialist_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const specialist = {
      specialistId,
      userId,
      specializedBrands, // ["pepsi", "nike", "apple"]
      expertise: {
        yearsExperience: expertise.yearsExperience,
        successRate: expertise.successRate || 0,
        totalPredictions: expertise.totalPredictions || 0,
        avgAccuracy: expertise.avgAccuracy || 0,
        specializations: expertise.specializations // ["sports_events", "entertainment", "live_streaming"]
      },
      credentials,
      portfolioUrl,
      pricingTiers: {
        basicModel: pricingTiers.basicModel || 50,
        premiumModel: pricingTiers.premiumModel || 200,
        exclusiveConsulting: pricingTiers.exclusiveConsulting || 1000,
        corporateContract: pricingTiers.corporateContract || 10000
      },
      stats: {
        modelsCreated: 0,
        modelsSold: 0,
        totalEarnings: 0,
        avgRating: 0,
        clientCount: 0
      },
      verification: {
        verified: false,
        certificationLevel: 'bronze', // bronze, silver, gold, platinum
        verifiedBrands: []
      },
      createdAt: Date.now()
    };

    brandSpecialists.set(specialistId, specialist);
    
    // Initialize earnings tracking
    specialistEarnings.set(specialistId, {
      totalEarnings: 0,
      modelSales: 0,
      consultingFees: 0,
      prizeWinnings: 0,
      corporateContracts: 0,
      monthlyBreakdown: {}
    });

    res.json({
      success: true,
      specialistId,
      specialist,
      message: 'Brand specialist registered successfully'
    });

  } catch (error) {
    console.error('Specialist registration error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to register specialist',
      message: error.message
    });
  }
});

// Create Brand-Specific Model

router.post('/models/create', async (req, res) => {
  try {
    const {
      specialistId,
      brandName,
      modelTitle,
      modelType,
      description,
      trainingData,
      accuracy,
      price,
      category,
      eventTypes,
      insights
    } = req.body;

    const specialist = brandSpecialists.get(specialistId);
    if (!specialist) {
      return res.status(404).json({
        success: false,
        error: 'Specialist not found'
      });
    }

    const modelId = `model_${brandName}_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    
    const brandModel = {
      modelId,
      specialistId,
      brandName: brandName.toLowerCase(),
      modelTitle,
      modelType, // "logo_frequency", "placement_timing", "context_analysis", "comprehensive"
      description,
      category, // "sports", "entertainment", "live_events", "streaming"
      eventTypes, // ["football", "basketball", "concerts", "gaming"]
      
      performance: {
        accuracy: accuracy,
        trainingEvents: trainingData.eventCount,
        dataPoints: trainingData.dataPoints,
        lastUpdated: Date.now(),
        validationScore: calculateValidationScore(trainingData, accuracy)
      },
      
      pricing: {
        price: price,
        tier: determinePriceTier(price),
        licenseType: 'single_use', // single_use, subscription, unlimited
        discounts: {
          bulk: price > 100 ? 0.15 : 0.1,
          subscription: 0.25
        }
      },
      
      insights: {
        keyPatterns: insights.keyPatterns,
        timingPatterns: insights.timingPatterns,
        placementStrategy: insights.placementStrategy,
        competitorAnalysis: insights.competitorAnalysis,
        successFactors: insights.successFactors
      },
      
      usage: {
        downloads: 0,
        activeUsers: 0,
        avgUserAccuracy: 0,
        userFeedback: [],
        successStories: []
      },
      
      status: 'active',
      createdAt: Date.now()
    };

    brandModels.set(modelId, brandModel);
    
    // Update specialist stats
    specialist.stats.modelsCreated++;
    
    // Store brand insights for global analytics
    updateBrandInsights(brandName, insights);

    res.json({
      success: true,
      modelId,
      model: brandModel,
      specialist: {
        name: specialist.userId,
        expertise: specialist.expertise,
        verification: specialist.verification
      },
      message: `${brandName} prediction model created successfully`
    });

  } catch (error) {
    console.error('Model creation error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create model',
      message: error.message
    });
  }
});

// Browse Brand Models

router.get('/models/browse', async (req, res) => {
  try {
    const { 
      brand, 
      category, 
      eventType, 
      minAccuracy, 
      maxPrice, 
      sortBy = 'accuracy',
      page = 1,
      limit = 20 
    } = req.query;

    let models = Array.from(brandModels.values())
      .filter(model => model.status === 'active');

    // Apply filters
    if (brand) {
      models = models.filter(model => model.brandName === brand.toLowerCase());
    }
    if (category) {
      models = models.filter(model => model.category === category);
    }
    if (eventType) {
      models = models.filter(model => model.eventTypes.includes(eventType));
    }
    if (minAccuracy) {
      models = models.filter(model => model.performance.accuracy >= parseFloat(minAccuracy));
    }
    if (maxPrice) {
      models = models.filter(model => model.pricing.price <= parseFloat(maxPrice));
    }

    // Sort models
    models.sort((a, b) => {
      switch (sortBy) {
        case 'accuracy':
          return b.performance.accuracy - a.performance.accuracy;
        case 'price_low':
          return a.pricing.price - b.pricing.price;
        case 'price_high':
          return b.pricing.price - a.pricing.price;
        case 'popularity':
          return b.usage.downloads - a.usage.downloads;
        case 'recent':
          return b.createdAt - a.createdAt;
        default:
          return b.performance.accuracy - a.performance.accuracy;
      }
    });

    // Pagination
    const startIndex = (page - 1) * limit;
    const paginatedModels = models.slice(startIndex, startIndex + limit);

    // Add specialist info to each model
    const modelsWithSpecialists = paginatedModels.map(model => {
      const specialist = brandSpecialists.get(model.specialistId);
      return {
        ...model,
        specialist: {
          expertise: specialist?.expertise,
          verification: specialist?.verification,
          stats: specialist?.stats
        }
      };
    });

    res.json({
      success: true,
      models: modelsWithSpecialists,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: models.length,
        pages: Math.ceil(models.length / limit)
      },
      filters: {
        availableBrands: getAvailableBrands(),
        availableCategories: getAvailableCategories(),
        priceRange: getPriceRange(),
        accuracyRange: getAccuracyRange()
      }
    });

  } catch (error) {
    console.error('Model browse error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to browse models',
      message: error.message
    });
  }
});

// Purchase Model

router.post('/models/:modelId/purchase', async (req, res) => {
  try {
    const { modelId } = req.params;
    const { userId, licenseType = 'single_use', paymentMethod } = req.body;

    const model = brandModels.get(modelId);
    if (!model) {
      return res.status(404).json({
        success: false,
        error: 'Model not found'
      });
    }

    const specialist = brandSpecialists.get(model.specialistId);
    
    // Calculate price based on license type
    let finalPrice = model.pricing.price;
    if (licenseType === 'subscription') {
      finalPrice *= 0.75; // 25% discount for subscription
    } else if (licenseType === 'unlimited') {
      finalPrice *= 3; // 3x price for unlimited use
    }

    const purchaseId = `purchase_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const purchase = {
      purchaseId,
      modelId,
      userId,
      specialistId: model.specialistId,
      price: finalPrice,
      licenseType,
      purchaseDate: Date.now(),
      status: 'completed'
    };

    // Update model usage stats
    model.usage.downloads++;
    model.usage.activeUsers++;

    // Update specialist earnings
    const earnings = specialistEarnings.get(model.specialistId);
    earnings.totalEarnings += finalPrice * 0.85; // 85% to specialist, 15% platform fee
    earnings.modelSales += finalPrice * 0.85;
    specialist.stats.modelsSold++;
    specialist.stats.totalEarnings += finalPrice * 0.85;

    // Grant access to model
    const accessToken = generateModelAccessToken(userId, modelId, licenseType);

    res.json({
      success: true,
      purchase,
      accessToken,
      model: {
        modelId: model.modelId,
        brandName: model.brandName,
        modelTitle: model.modelTitle,
        accuracy: model.performance.accuracy,
        insights: model.insights
      },
      specialist: {
        name: specialist.userId,
        expertise: specialist.expertise
      },
      license: {
        type: licenseType,
        expiresAt: licenseType === 'subscription' ? Date.now() + 30 * 24 * 60 * 60 * 1000 : null
      },
      message: `${model.brandName} prediction model purchased successfully`
    });

  } catch (error) {
    console.error('Model purchase error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to purchase model',
      message: error.message
    });
  }
});

// Specialist Analytics

router.get('/specialists/:specialistId/analytics', async (req, res) => {
  try {
    const { specialistId } = req.params;
    
    const specialist = brandSpecialists.get(specialistId);
    if (!specialist) {
      return res.status(404).json({
        success: false,
        error: 'Specialist not found'
      });
    }

    const earnings = specialistEarnings.get(specialistId);
    const specialistModels = Array.from(brandModels.values())
      .filter(model => model.specialistId === specialistId);

    const analytics = {
      specialist: {
        ...specialist,
        totalEarnings: earnings.totalEarnings
      },
      performance: {
        modelsCreated: specialistModels.length,
        totalDownloads: specialistModels.reduce((sum, model) => sum + model.usage.downloads, 0),
        avgModelAccuracy: specialistModels.length > 0 ? 
          specialistModels.reduce((sum, model) => sum + model.performance.accuracy, 0) / specialistModels.length : 0,
        topPerformingModel: specialistModels.sort((a, b) => b.usage.downloads - a.usage.downloads)[0],
        brandExpertise: specialist.specializedBrands
      },
      earnings: {
        ...earnings,
        earningsPerModel: earnings.totalEarnings / Math.max(1, specialist.stats.modelsCreated),
        projectedMonthly: earnings.totalEarnings * 0.15, // Rough projection
        revenueStreams: {
          modelSales: earnings.modelSales,
          consultingFees: earnings.consultingFees,
          prizeWinnings: earnings.prizeWinnings,
          corporateContracts: earnings.corporateContracts
        }
      },
      marketPosition: {
        ranking: calculateSpecialistRanking(specialistId),
        marketShare: calculateMarketShare(specialistId, specialist.specializedBrands),
        competitorAnalysis: getCompetitorAnalysis(specialist.specializedBrands)
      }
    };

    res.json({
      success: true,
      analytics
    });

  } catch (error) {
    console.error('Specialist analytics error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch specialist analytics',
      message: error.message
    });
  }
});

// Brand Insights API

router.get('/insights/:brandName', async (req, res) => {
  try {
    const { brandName } = req.params;
    
    const insights = brandInsights.get(brandName.toLowerCase());
    if (!insights) {
      return res.status(404).json({
        success: false,
        error: 'No insights available for this brand'
      });
    }

    const brandModelsData = Array.from(brandModels.values())
      .filter(model => model.brandName === brandName.toLowerCase());

    const aggregatedInsights = {
      brand: brandName,
      totalModels: brandModelsData.length,
      avgAccuracy: brandModelsData.length > 0 ? 
        brandModelsData.reduce((sum, model) => sum + model.performance.accuracy, 0) / brandModelsData.length : 0,
      
      patterns: {
        commonTimingPatterns: aggregateTimingPatterns(brandModelsData),
        placementStrategies: aggregatePlacementStrategies(brandModelsData),
        eventTypePreferences: aggregateEventTypes(brandModelsData),
        seasonalTrends: aggregateSeasonalTrends(brandModelsData)
      },
      
      marketData: {
        topSpecialists: getTopSpecialistsForBrand(brandName),
        priceRange: getBrandModelPriceRange(brandModelsData),
        demandMetrics: calculateBrandDemand(brandModelsData),
        competitiveAnalysis: getBrandCompetitiveAnalysis(brandName)
      },
      
      recommendations: {
        optimalEventTypes: getOptimalEventTypes(brandModelsData),
        pricingRecommendations: getPricingRecommendations(brandModelsData),
        improvementAreas: getImprovementAreas(brandModelsData)
      }
    };

    res.json({
      success: true,
      insights: aggregatedInsights
    });

  } catch (error) {
    console.error('Brand insights error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch brand insights',
      message: error.message
    });
  }
});

// Helper Functions

function calculateValidationScore(trainingData, accuracy) {
  return Math.min(100, (trainingData.eventCount * 10 + accuracy * 50 + trainingData.dataPoints / 100));
}

function determinePriceTier(price) {
  if (price < 25) return 'basic';
  if (price < 100) return 'standard';
  if (price < 500) return 'premium';
  return 'enterprise';
}

function updateBrandInsights(brandName, insights) {
  const existing = brandInsights.get(brandName.toLowerCase()) || { patterns: [], updates: 0 };
  existing.patterns.push(insights);
  existing.updates++;
  existing.lastUpdated = Date.now();
  brandInsights.set(brandName.toLowerCase(), existing);
}

function generateModelAccessToken(userId, modelId, licenseType) {
  return `access_${userId}_${modelId}_${licenseType}_${Date.now()}`;
}

function getAvailableBrands() {
  return [...new Set(Array.from(brandModels.values()).map(model => model.brandName))];
}

function getAvailableCategories() {
  return [...new Set(Array.from(brandModels.values()).map(model => model.category))];
}

function getPriceRange() {
  const prices = Array.from(brandModels.values()).map(model => model.pricing.price);
  return { min: Math.min(...prices), max: Math.max(...prices) };
}

function getAccuracyRange() {
  const accuracies = Array.from(brandModels.values()).map(model => model.performance.accuracy);
  return { min: Math.min(...accuracies), max: Math.max(...accuracies) };
}

function calculateSpecialistRanking(specialistId) {
  const allSpecialists = Array.from(brandSpecialists.values());
  const sorted = allSpecialists.sort((a, b) => b.stats.totalEarnings - a.stats.totalEarnings);
  return sorted.findIndex(s => s.specialistId === specialistId) + 1;
}

function calculateMarketShare(specialistId, brands) {
  // Simplified market share calculation
  const specialist = brandSpecialists.get(specialistId);
  const totalModelsInBrands = Array.from(brandModels.values())
    .filter(model => brands.includes(model.brandName)).length;
  const specialistModels = Array.from(brandModels.values())
    .filter(model => model.specialistId === specialistId).length;
  
  return totalModelsInBrands > 0 ? (specialistModels / totalModelsInBrands) * 100 : 0;
}

function getCompetitorAnalysis(brands) {
  // Return top competitors for the specialist's brands
  return brands.map(brand => ({
    brand,
    topCompetitors: Array.from(brandSpecialists.values())
      .filter(s => s.specializedBrands.includes(brand))
      .sort((a, b) => b.stats.totalEarnings - a.stats.totalEarnings)
      .slice(0, 3)
      .map(s => ({ id: s.specialistId, earnings: s.stats.totalEarnings }))
  }));
}

// Additional helper functions would be implemented for aggregation and analysis...

module.exports = router; 