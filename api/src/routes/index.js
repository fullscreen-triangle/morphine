const express = require('express');
const router = express.Router();

// Import route modules
const authRoutes = require('./auth');
const streamRoutes = require('./streams');
const analyticsRoutes = require('./analytics');
const { router: bettingRoutes } = require('./betting'); // Updated to destructure router

// Mount routes
router.use('/auth', authRoutes);
router.use('/streams', streamRoutes);
router.use('/analytics', analyticsRoutes);
router.use('/betting', bettingRoutes);

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({
    success: true,
    message: 'API service is healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    version: process.env.npm_package_version || '1.0.0'
  });
});

// Root endpoint
router.get('/', (req, res) => {
  res.json({
    success: true,
    message: 'Morphine Platform API',
    version: '1.0.0',
    endpoints: {
      auth: '/api/auth',
      streams: '/api/streams',
      analytics: '/api/analytics',
      betting: '/api/betting'
    }
  });
});

module.exports = router; 