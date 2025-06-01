const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { createServer } = require('http');
const WebSocket = require('ws');
require('dotenv').config();

const logger = require('./utils/logger');
const { connectRedis } = require('./services/redis');
const { initializeWebSocket } = require('./services/websocket');

// Import ALL revolutionary routes
const routes = require('./routes');

const app = express();
const server = createServer(app);

// Middleware
app.use(helmet());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3002'],
  credentials: true
}));
app.use(compression());
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } }));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});
app.use('/api/', limiter);

// Revolutionary Platform Health Check
app.get('/health', (req, res) => {
  res.json({
    status: 'Revolutionary Platform Operational',
    platform: 'Morphine - Universal Human Knowledge Sharing Economy',
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

// Mount ALL revolutionary API routes
app.use('/api', routes);

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Revolutionary Platform Route Not Found',
    message: `Route ${req.originalUrl} not found`,
    available_endpoints: '/api/ for complete revolutionary API documentation'
  });
});

// Initialize services and start revolutionary platform server
async function startServer() {
  try {
    // Connect to Redis
    await connectRedis();
    logger.info('Revolutionary Platform: Connected to Redis');

    // Initialize WebSocket server for real-time revolutionary features
    const wss = new WebSocket.Server({ server });
    initializeWebSocket(wss);
    logger.info('Revolutionary Platform: WebSocket server initialized');

    // Start Revolutionary Platform HTTP server
    const PORT = process.env.PORT || 3000;
    server.listen(PORT, () => {
      logger.info(`🚀 MORPHINE REVOLUTIONARY PLATFORM ACTIVE 🚀`);
      logger.info(`🌟 Universal Human Knowledge Sharing Economy: port ${PORT}`);
      logger.info(`⚡ Environment: ${process.env.NODE_ENV || 'development'}`);
      logger.info(`💫 Revolutionary Features: ALL SYSTEMS OPERATIONAL`);
      logger.info(`🎯 API Documentation: http://localhost:${PORT}/api/`);
    });

  } catch (error) {
    logger.error('Failed to start Revolutionary Platform server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down Revolutionary Platform gracefully');
  server.close(() => {
    logger.info('Revolutionary Platform terminated');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down Revolutionary Platform gracefully'); 
  server.close(() => {
    logger.info('Revolutionary Platform terminated');
    process.exit(0);
  });
});

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
  logger.error('Revolutionary Platform Uncaught Exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Revolutionary Platform Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

startServer(); 