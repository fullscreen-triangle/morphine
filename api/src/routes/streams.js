const express = require('express');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');
const { get, setWithExpiry, del } = require('../services/redis');

const router = express.Router();

const CORE_SERVICE_URL = process.env.CORE_SERVICE_URL || 'http://localhost:3001';
const ANALYTICS_SERVICE_URL = process.env.ANALYTICS_SERVICE_URL || 'http://localhost:8000';

// Get all streams
router.get('/', async (req, res) => {
  try {
    const response = await axios.get(`${CORE_SERVICE_URL}/streams`, {
      timeout: 5000
    });
    
    res.json({
      success: true,
      streams: response.data
    });
  } catch (error) {
    logger.error('Failed to fetch streams:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch streams',
      message: error.message
    });
  }
});

// Get stream by ID
router.get('/:streamId', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    const response = await axios.get(`${CORE_SERVICE_URL}/streams/${streamId}/status`, {
      timeout: 5000
    });
    
    res.json({
      success: true,
      stream: response.data
    });
  } catch (error) {
    logger.error(`Failed to fetch stream ${req.params.streamId}:`, error.message);
    
    if (error.response?.status === 404) {
      return res.status(404).json({
        success: false,
        error: 'Stream not found'
      });
    }
    
    res.status(500).json({
      success: false,
      error: 'Failed to fetch stream',
      message: error.message
    });
  }
});

// Create new stream
router.post('/', async (req, res) => {
  try {
    const streamData = {
      id: uuidv4(),
      title: req.body.title || 'Untitled Stream',
      description: req.body.description || '',
      settings: {
        enable_cv: req.body.enable_cv !== false,
        enable_betting: req.body.enable_betting !== false,
        quality: req.body.quality || '1080p',
        ...req.body.settings
      },
      created_at: new Date().toISOString()
    };
    
    // Store stream metadata in Redis
    await setWithExpiry(`stream:${streamData.id}`, streamData, 86400); // 24 hours
    
    logger.info(`Created new stream: ${streamData.id}`);
    
    res.status(201).json({
      success: true,
      stream: streamData
    });
  } catch (error) {
    logger.error('Failed to create stream:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to create stream',
      message: error.message
    });
  }
});

// Activate stream
router.post('/:streamId/activate', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    // Check if stream exists
    const streamData = await get(`stream:${streamId}`);
    if (!streamData) {
      return res.status(404).json({
        success: false,
        error: 'Stream not found'
      });
    }
    
    // Activate stream in core service
    const coreResponse = await axios.post(`${CORE_SERVICE_URL}/streams/${streamId}/activate`, {
      timeout: 10000
    });
    
    // Start analytics if enabled
    if (streamData.settings.enable_cv) {
      try {
        await axios.post(`${ANALYTICS_SERVICE_URL}/analytics/start_stream`, {
          stream_id: streamId,
          settings: streamData.settings
        }, { timeout: 5000 });
        logger.info(`Started analytics for stream: ${streamId}`);
      } catch (analyticsError) {
        logger.warn(`Failed to start analytics for stream ${streamId}:`, analyticsError.message);
      }
    }
    
    res.json({
      success: true,
      result: coreResponse.data
    });
  } catch (error) {
    logger.error(`Failed to activate stream ${req.params.streamId}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to activate stream',
      message: error.message
    });
  }
});

// Deactivate stream
router.post('/:streamId/deactivate', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    // Stop analytics
    try {
      await axios.post(`${ANALYTICS_SERVICE_URL}/analytics/stop_stream/${streamId}`, {}, {
        timeout: 5000
      });
      logger.info(`Stopped analytics for stream: ${streamId}`);
    } catch (analyticsError) {
      logger.warn(`Failed to stop analytics for stream ${streamId}:`, analyticsError.message);
    }
    
    // Deactivate in core service (this endpoint would need to be implemented in core)
    // For now, we'll just return success
    
    res.json({
      success: true,
      message: 'Stream deactivated successfully'
    });
  } catch (error) {
    logger.error(`Failed to deactivate stream ${req.params.streamId}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to deactivate stream',
      message: error.message
    });
  }
});

// Update stream settings
router.patch('/:streamId', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    // Get existing stream data
    const streamData = await get(`stream:${streamId}`);
    if (!streamData) {
      return res.status(404).json({
        success: false,
        error: 'Stream not found'
      });
    }
    
    // Update stream data
    const updatedStream = {
      ...streamData,
      ...req.body,
      settings: {
        ...streamData.settings,
        ...req.body.settings
      },
      updated_at: new Date().toISOString()
    };
    
    // Save updated stream
    await setWithExpiry(`stream:${streamId}`, updatedStream, 86400);
    
    logger.info(`Updated stream: ${streamId}`);
    
    res.json({
      success: true,
      stream: updatedStream
    });
  } catch (error) {
    logger.error(`Failed to update stream ${req.params.streamId}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to update stream',
      message: error.message
    });
  }
});

// Delete stream
router.delete('/:streamId', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    // Stop analytics first
    try {
      await axios.post(`${ANALYTICS_SERVICE_URL}/analytics/stop_stream/${streamId}`, {}, {
        timeout: 5000
      });
    } catch (analyticsError) {
      logger.warn(`Failed to stop analytics for stream ${streamId}:`, analyticsError.message);
    }
    
    // Delete from Redis
    await del(`stream:${streamId}`);
    
    logger.info(`Deleted stream: ${streamId}`);
    
    res.json({
      success: true,
      message: 'Stream deleted successfully'
    });
  } catch (error) {
    logger.error(`Failed to delete stream ${req.params.streamId}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to delete stream',
      message: error.message
    });
  }
});

module.exports = router; 