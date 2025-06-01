const express = require('express');
const axios = require('axios');
const logger = require('../utils/logger');

const router = express.Router();

const ANALYTICS_SERVICE_URL = process.env.ANALYTICS_SERVICE_URL || 'http://localhost:8000';

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

module.exports = router; 