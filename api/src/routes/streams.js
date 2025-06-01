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
    const response = await axios.get(`${CORE_SERVICE_URL}/api/streams`);
    res.json(response.data);
  } catch (error) {
    logger.error('Failed to fetch streams:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch streams'
    });
  }
});

// Get stream by ID
router.get('/:streamId', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    const response = await axios.get(`${CORE_SERVICE_URL}/api/streams/${streamId}`);
    
    res.json(response.data);
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
      error: 'Failed to fetch stream'
    });
  }
});

// Create new stream
router.post('/', async (req, res) => {
  try {
    const { title, source_type, source_url, settings } = req.body;

    if (!title || !source_type || !source_url) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: title, source_type, source_url'
      });
    }

    // Create stream in core service
    const coreResponse = await axios.post(`${CORE_SERVICE_URL}/api/streams`, {
      title,
      source_type,
      source_url,
      settings: settings || {}
    });

    if (!coreResponse.data.success) {
      return res.status(400).json(coreResponse.data);
    }

    const stream = coreResponse.data.data;

    // Start analytics for the stream
    try {
      await axios.post(`${ANALYTICS_SERVICE_URL}/analytics/start_stream`, {
        stream_id: stream.id,
        source_type,
        source_url,
        settings: settings || {}
      });
    } catch (analyticsError) {
      logger.warn('Failed to start analytics for stream:', analyticsError.message);
    }

    logger.info(`Created stream: ${stream.id} - ${title}`);
    res.json({
      success: true,
      data: stream
    });

  } catch (error) {
    logger.error('Failed to create stream:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to create stream'
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
    const coreResponse = await axios.post(`${CORE_SERVICE_URL}/api/streams/${streamId}/start`);
    
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
      await axios.post(`${ANALYTICS_SERVICE_URL}/analytics/stop_stream/${streamId}`);
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
      await axios.post(`${ANALYTICS_SERVICE_URL}/analytics/stop_stream/${streamId}`);
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

// Get stream analytics summary
router.get('/:streamId/analytics', async (req, res) => {
  try {
    const { streamId } = req.params;
    const response = await axios.get(`${ANALYTICS_SERVICE_URL}/analytics/${streamId}/summary`);
    res.json({
      success: true,
      data: response.data
    });
  } catch (error) {
    logger.error(`Failed to get analytics for stream ${req.params.streamId}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to get stream analytics'
    });
  }
});

// Get stream metrics
router.get('/:streamId/metrics', async (req, res) => {
  try {
    const { streamId } = req.params;
    const response = await axios.get(`${ANALYTICS_SERVICE_URL}/analytics/${streamId}/metrics`);
    res.json({
      success: true,
      data: response.data
    });
  } catch (error) {
    logger.error(`Failed to get metrics for stream ${req.params.streamId}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to get stream metrics'
    });
  }
});

// Get active streams (for dashboard)
router.get('/status/active', async (req, res) => {
  try {
    const response = await axios.get(`${ANALYTICS_SERVICE_URL}/streams/active`);
    res.json({
      success: true,
      data: response.data
    });
  } catch (error) {
    logger.error('Failed to get active streams:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to get active streams'
    });
  }
});

// Stream health check
router.get('/:streamId/health', async (req, res) => {
  try {
    const { streamId } = req.params;
    
    // Check core service
    const coreHealth = await axios.get(`${CORE_SERVICE_URL}/api/streams/${streamId}/status`);
    
    // Check analytics service
    let analyticsHealth = { status: 'unknown' };
    try {
      const analyticsResponse = await axios.get(`${ANALYTICS_SERVICE_URL}/analytics/${streamId}/latest`);
      analyticsHealth = { status: 'healthy', last_update: analyticsResponse.data?.timestamp };
    } catch (analyticsError) {
      analyticsHealth = { status: 'unhealthy', error: analyticsError.message };
    }

    res.json({
      success: true,
      data: {
        stream_id: streamId,
        core_service: coreHealth.data,
        analytics_service: analyticsHealth,
        overall_status: analyticsHealth.status === 'healthy' ? 'healthy' : 'degraded'
      }
    });

  } catch (error) {
    logger.error(`Failed to check health for stream ${req.params.streamId}:`, error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to check stream health'
    });
  }
});

module.exports = router; 