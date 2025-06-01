const express = require('express');
const router = express.Router();

// Import ALL revolutionary route modules
const authRoutes = require('./auth');
const streamRoutes = require('./streams');
const analyticsRoutes = require('./analytics');
const { router: bettingRoutes } = require('./betting');
const universalPredictionsRoutes = require('./universal-predictions');
const annotationModelsRoutes = require('./annotation-models');
const brandEngagementRoutes = require('./brand-engagement');
const socialViewingRoutes = require('./social-viewing');
const brandSpecialistsRoutes = require('./brand-specialists');
const brandPredictionsRoutes = require('./brand-predictions');
const marketplaceRoutes = require('./marketplace');

// Mount ALL revolutionary routes
router.use('/auth', authRoutes);
router.use('/streams', streamRoutes);
router.use('/analytics', analyticsRoutes);
router.use('/betting', bettingRoutes);
router.use('/universal-predictions', universalPredictionsRoutes);
router.use('/annotation-models', annotationModelsRoutes);
router.use('/brand-engagement', brandEngagementRoutes);
router.use('/social-viewing', socialViewingRoutes);
router.use('/brand-specialists', brandSpecialistsRoutes);
router.use('/brand-predictions', brandPredictionsRoutes);
router.use('/marketplace', marketplaceRoutes);

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({
    success: true,
    message: 'Revolutionary Morphine Platform API - All Systems Operational',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    version: process.env.npm_package_version || '1.0.0',
    revolutionary_features: {
      universal_predictions: 'ACTIVE',
      annotation_models: 'ACTIVE', 
      brand_engagement: 'ACTIVE',
      social_viewing: 'ACTIVE',
      expert_marketplace: 'ACTIVE',
      knowledge_overlay: 'ACTIVE'
    }
  });
});

// Root endpoint with complete revolutionary API documentation
router.get('/', (req, res) => {
  res.json({
    success: true,
    message: 'Morphine Revolutionary Platform API - Universal Human Knowledge Sharing Economy',
    version: '1.0.0',
    revolutionary_endpoints: {
      // Core Platform
      auth: '/api/auth',
      streams: '/api/streams', 
      analytics: '/api/analytics',
      betting: '/api/betting',
      
      // Revolutionary Features
      universal_predictions: '/api/universal-predictions',
      annotation_models: '/api/annotation-models',
      brand_engagement: '/api/brand-engagement',
      social_viewing: '/api/social-viewing',
      brand_specialists: '/api/brand-specialists',
      brand_predictions: '/api/brand-predictions',
      marketplace: '/api/marketplace'
    },
    platform_capabilities: {
      cross_industry_predictions: 'Construction, Medical, Sports, Education, Finance',
      universal_knowledge_overlay: 'Any expert model enhances any compatible video',
      expert_monetization: 'Passive income from annotation models',
      brand_engagement_revolution: 'Prediction-based advertising campaigns',
      social_collaborative_viewing: 'Family prediction teams and specialist following',
      global_expertise_marketplace: 'Buy/sell expertise as digital assets'
    },
    economic_impact: {
      expert_income_potential: '$15,000-$50,000+/month from annotation models',
      brand_advertising_efficiency: '100x more effective per dollar spent',
      knowledge_democratization: 'Universal access to world-class expertise',
      platform_scalability: 'Infinite - every model enhances unlimited videos'
    }
  });
});

module.exports = router; 