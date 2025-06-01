const express = require('express');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');
const { setWithExpiry, get, zadd, zrangeByScore } = require('../services/redis');
const auth = require('../middleware/auth');

const router = express.Router();

const CORE_SERVICE_URL = process.env.CORE_SERVICE_URL || 'http://localhost:3001';

// Bet types and their configurations
const BET_TYPES = {
  SPEED_MILESTONE: {
    name: 'speed_milestone',
    description: 'Bet on whether a tracked object will reach a certain speed',
    maxAmount: 100,
    minAmount: 1,
    basePayout: 2.5
  },
  POSE_EVENT: {
    name: 'pose_event',
    description: 'Bet on specific pose events or joint angles',
    maxAmount: 50,
    minAmount: 1,
    basePayout: 3.0
  },
  MOTION_PATTERN: {
    name: 'motion_pattern',
    description: 'Bet on motion patterns and behaviors',
    maxAmount: 75,
    minAmount: 1,
    basePayout: 2.2
  },
  DETECTION_COUNT: {
    name: 'detection_count',
    description: 'Bet on number of detections in time window',
    maxAmount: 80,
    minAmount: 1,
    basePayout: 2.8
  }
};

// Bet status enum
const BET_STATUS = {
  PENDING: 'pending',
  ACTIVE: 'active',
  WON: 'won',
  LOST: 'lost',
  CANCELLED: 'cancelled',
  EXPIRED: 'expired'
};

class BettingEngine {
  constructor() {
    this.activeBets = new Map();
    this.oddsCalculator = new OddsCalculator();
    this.settlementEngine = new SettlementEngine();
  }

  async placeBet(userId, streamId, betData) {
    try {
      // Validate bet data
      const validation = this.validateBet(betData);
      if (!validation.valid) {
        throw new Error(validation.error);
      }

      // Check user balance
      const userBalance = await this.getUserBalance(userId, streamId);
      if (userBalance < betData.amount) {
        throw new Error('Insufficient balance');
      }

      // Calculate odds
      const odds = await this.oddsCalculator.calculateOdds(streamId, betData);

      // Create bet
      const bet = {
        id: uuidv4(),
        userId,
        streamId,
        betType: betData.betType,
        amount: betData.amount,
        odds: odds,
        prediction: betData.prediction,
        timestamp: Date.now(),
        status: BET_STATUS.PENDING,
        expiresAt: Date.now() + (betData.duration || 60000), // Default 1 minute
        metadata: betData.metadata || {}
      };

      // Reserve funds
      await this.reserveFunds(userId, streamId, betData.amount);

      // Store bet
      await this.storeBet(bet);

      // Activate bet
      bet.status = BET_STATUS.ACTIVE;
      this.activeBets.set(bet.id, bet);

      // Schedule expiration
      this.scheduleExpiration(bet);

      logger.info(`Bet placed: ${bet.id} by user ${userId} on stream ${streamId}`);
      return bet;

    } catch (error) {
      logger.error(`Error placing bet: ${error.message}`);
      throw error;
    }
  }

  validateBet(betData) {
    if (!betData.betType || !BET_TYPES[betData.betType.toUpperCase()]) {
      return { valid: false, error: 'Invalid bet type' };
    }

    const betType = BET_TYPES[betData.betType.toUpperCase()];

    if (!betData.amount || betData.amount < betType.minAmount || betData.amount > betType.maxAmount) {
      return { valid: false, error: `Amount must be between ${betType.minAmount} and ${betType.maxAmount}` };
    }

    if (!betData.prediction) {
      return { valid: false, error: 'Prediction is required' };
    }

    return { valid: true };
  }

  async getUserBalance(userId, streamId) {
    try {
      const balance = await get(`balance:${userId}:${streamId}`);
      return parseFloat(balance) || 100.0; // Default starting balance
    } catch (error) {
      logger.error(`Error getting user balance: ${error.message}`);
      return 0;
    }
  }

  async reserveFunds(userId, streamId, amount) {
    try {
      const currentBalance = await this.getUserBalance(userId, streamId);
      const newBalance = currentBalance - amount;
      
      if (newBalance < 0) {
        throw new Error('Insufficient funds');
      }

      await setWithExpiry(`balance:${userId}:${streamId}`, newBalance.toString(), 86400);
      await zadd(`reserved:${userId}:${streamId}`, Date.now(), amount);

      logger.info(`Reserved ${amount} for user ${userId} on stream ${streamId}`);
    } catch (error) {
      logger.error(`Error reserving funds: ${error.message}`);
      throw error;
    }
  }

  async storeBet(bet) {
    try {
      // Store in Redis
      await setWithExpiry(`bet:${bet.id}`, JSON.stringify(bet), 86400); // 24 hour TTL

      // Add to user's bet history
      await zadd(`user:${bet.userId}:bets`, bet.timestamp, bet.id);

      // Add to stream's betting activity
      await zadd(`stream:${bet.streamId}:bets`, bet.timestamp, bet.id);

      // Limit history size
      await zremrangebyrank(`user:${bet.userId}:bets`, 0, -1001); // Keep last 1000
      await zremrangebyrank(`stream:${bet.streamId}:bets`, 0, -501); // Keep last 500

    } catch (error) {
      logger.error(`Error storing bet: ${error.message}`);
      throw error;
    }
  }

  scheduleExpiration(bet) {
    const timeUntilExpiry = bet.expiresAt - Date.now();
    
    if (timeUntilExpiry > 0) {
      setTimeout(async () => {
        if (this.activeBets.has(bet.id) && this.activeBets.get(bet.id).status === BET_STATUS.ACTIVE) {
          await this.expireBet(bet.id);
        }
      }, timeUntilExpiry);
    }
  }

  async expireBet(betId) {
    try {
      const bet = this.activeBets.get(betId);
      if (!bet) return;

      bet.status = BET_STATUS.EXPIRED;
      this.activeBets.delete(betId);

      // Refund reserved funds
      await this.refundBet(bet);

      // Update stored bet
      await setWithExpiry(`bet:${betId}`, JSON.stringify(bet), 86400);

      logger.info(`Bet expired: ${betId}`);
    } catch (error) {
      logger.error(`Error expiring bet: ${error.message}`);
    }
  }

  async refundBet(bet) {
    try {
      // Return reserved funds to balance
      const currentBalance = await this.getUserBalance(bet.userId, bet.streamId);
      const newBalance = currentBalance + bet.amount;
      
      await setWithExpiry(`balance:${bet.userId}:${bet.streamId}`, newBalance.toString(), 86400);
      await zdecrby(`reserved:${bet.userId}:${bet.streamId}`, bet.amount);

      logger.info(`Refunded ${bet.amount} to user ${bet.userId}`);
    } catch (error) {
      logger.error(`Error refunding bet: ${error.message}`);
    }
  }

  async settleBet(betId, outcome) {
    try {
      const bet = this.activeBets.get(betId);
      if (!bet || bet.status !== BET_STATUS.ACTIVE) {
        return false;
      }

      const won = this.settlementEngine.evaluateOutcome(bet, outcome);
      
      if (won) {
        const payout = bet.amount * bet.odds;
        bet.status = BET_STATUS.WON;
        bet.payout = payout;
        
        // Add winnings to balance
        const currentBalance = await this.getUserBalance(bet.userId, bet.streamId);
        const newBalance = currentBalance + payout;
        await setWithExpiry(`balance:${bet.userId}:${bet.streamId}`, newBalance.toString(), 86400);

        logger.info(`Bet won: ${betId}, payout: ${payout}`);
      } else {
        bet.status = BET_STATUS.LOST;
        logger.info(`Bet lost: ${betId}`);
      }

      // Remove reserved funds
      await zdecrby(`reserved:${bet.userId}:${bet.streamId}`, bet.amount);

      // Update bet
      bet.settledAt = Date.now();
      this.activeBets.delete(betId);
      await setWithExpiry(`bet:${betId}`, JSON.stringify(bet), 86400);

      return true;
    } catch (error) {
      logger.error(`Error settling bet: ${error.message}`);
      return false;
    }
  }
}

class OddsCalculator {
  async calculateOdds(streamId, betData) {
    try {
      // Get historical data for this bet type on this stream
      const historicalData = await this.getHistoricalData(streamId, betData.betType);
      
      // Base odds from bet type
      const betType = BET_TYPES[betData.betType.toUpperCase()];
      let odds = betType.basePayout;

      // Adjust based on prediction difficulty
      const difficultyMultiplier = this.calculateDifficultyMultiplier(betData);
      odds *= difficultyMultiplier;

      // Adjust based on current stream activity
      const activityMultiplier = await this.calculateActivityMultiplier(streamId);
      odds *= activityMultiplier;

      // Adjust based on recent outcomes
      const outcomeMultiplier = this.calculateOutcomeMultiplier(historicalData);
      odds *= outcomeMultiplier;

      // Ensure minimum odds
      odds = Math.max(odds, 1.1);

      // Round to 2 decimal places
      return Math.round(odds * 100) / 100;

    } catch (error) {
      logger.error(`Error calculating odds: ${error.message}`);
      return BET_TYPES[betData.betType.toUpperCase()].basePayout;
    }
  }

  calculateDifficultyMultiplier(betData) {
    switch (betData.betType.toLowerCase()) {
      case 'speed_milestone':
        // Higher speeds = higher odds
        const targetSpeed = betData.prediction.targetSpeed || 10;
        return Math.min(1 + (targetSpeed / 50), 5.0);
      
      case 'pose_event':
        // Extreme angles = higher odds
        const targetAngle = betData.prediction.targetAngle || 90;
        const extremeness = Math.abs(90 - targetAngle) / 90;
        return 1 + (extremeness * 2);
      
      default:
        return 1.0;
    }
  }

  async calculateActivityMultiplier(streamId) {
    try {
      // Get current analytics to assess activity level
      const analytics = await get(`analytics:${streamId}:latest`);
      if (!analytics) return 1.0;

      const data = JSON.parse(analytics);
      const detectionCount = data.vibrio?.detections?.length || 0;
      const motionEnergy = data.vibrio?.motion_energy?.motion_energy || 0;

      // More activity = slightly lower odds (easier to predict)
      const activityScore = (detectionCount * 0.1) + (motionEnergy * 0.5);
      return Math.max(0.8, 1.2 - (activityScore * 0.1));

    } catch (error) {
      return 1.0;
    }
  }

  calculateOutcomeMultiplier(historicalData) {
    if (!historicalData || historicalData.length === 0) return 1.0;

    // If recent bets of this type have been winning a lot, increase odds
    const recentWins = historicalData.filter(bet => bet.status === BET_STATUS.WON).length;
    const winRate = recentWins / historicalData.length;

    if (winRate > 0.6) {
      return 1.2; // Increase odds if too many wins
    } else if (winRate < 0.3) {
      return 0.9; // Decrease odds if too many losses
    }

    return 1.0;
  }

  async getHistoricalData(streamId, betType) {
    try {
      // Get recent bets of this type on this stream
      const betIds = await zrevrange(`stream:${streamId}:bets`, 0, 49); // Last 50 bets
      const bets = [];

      for (const betId of betIds) {
        const betData = await get(`bet:${betId}`);
        if (betData) {
          const bet = JSON.parse(betData);
          if (bet.betType === betType) {
            bets.push(bet);
          }
        }
      }

      return bets;
    } catch (error) {
      return [];
    }
  }
}

class SettlementEngine {
  evaluateOutcome(bet, analyticsOutcome) {
    switch (bet.betType.toLowerCase()) {
      case 'speed_milestone':
        return this.evaluateSpeedMilestone(bet, analyticsOutcome);
      
      case 'pose_event':
        return this.evaluatePoseEvent(bet, analyticsOutcome);
      
      case 'motion_pattern':
        return this.evaluateMotionPattern(bet, analyticsOutcome);
      
      case 'detection_count':
        return this.evaluateDetectionCount(bet, analyticsOutcome);
      
      default:
        return false;
    }
  }

  evaluateSpeedMilestone(bet, outcome) {
    const targetSpeed = bet.prediction.targetSpeed;
    const actualMaxSpeed = outcome.vibrio?.tracks?.reduce((max, track) => 
      Math.max(max, track.speed || 0), 0) || 0;

    if (bet.prediction.direction === 'over') {
      return actualMaxSpeed > targetSpeed;
    } else if (bet.prediction.direction === 'under') {
      return actualMaxSpeed < targetSpeed;
    }

    return Math.abs(actualMaxSpeed - targetSpeed) < (bet.prediction.tolerance || 2);
  }

  evaluatePoseEvent(bet, outcome) {
    const targetJoint = bet.prediction.joint;
    const targetAngle = bet.prediction.targetAngle;
    const tolerance = bet.prediction.tolerance || 10;

    const jointAngles = outcome.moriarty?.biomechanics?.joint_angles || {};
    const actualAngle = jointAngles[targetJoint];

    if (actualAngle === undefined) return false;

    return Math.abs(actualAngle - targetAngle) <= tolerance;
  }

  evaluateMotionPattern(bet, outcome) {
    const targetPattern = bet.prediction.pattern;
    
    if (targetPattern === 'high_motion') {
      const motionEnergy = outcome.vibrio?.motion_energy?.motion_energy || 0;
      return motionEnergy > (bet.prediction.threshold || 50);
    }
    
    if (targetPattern === 'stable_tracking') {
      const tracks = outcome.vibrio?.tracks || [];
      const stableTracks = tracks.filter(track => track.age > 10);
      return stableTracks.length >= (bet.prediction.minTracks || 2);
    }

    return false;
  }

  evaluateDetectionCount(bet, outcome) {
    const actualCount = outcome.vibrio?.detections?.length || 0;
    const predictedCount = bet.prediction.count;
    const tolerance = bet.prediction.tolerance || 1;

    return Math.abs(actualCount - predictedCount) <= tolerance;
  }
}

// Initialize betting engine
const bettingEngine = new BettingEngine();

// Routes

// Place a bet
router.post('/place', auth, async (req, res) => {
  try {
    const { streamId, betType, amount, prediction, duration, metadata } = req.body;
    const userId = req.user.id;

    if (!streamId || !betType || !amount || !prediction) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: streamId, betType, amount, prediction'
      });
    }

    const betData = {
      betType,
      amount: parseFloat(amount),
      prediction,
      duration: duration ? parseInt(duration) : undefined,
      metadata
    };

    const bet = await bettingEngine.placeBet(userId, streamId, betData);

    res.json({
      success: true,
      data: bet
    });

  } catch (error) {
    logger.error('Error placing bet:', error);
    res.status(400).json({
      success: false,
      error: error.message
    });
  }
});

// Get bet by ID
router.get('/:betId', auth, async (req, res) => {
  try {
    const { betId } = req.params;
    const betData = await get(`bet:${betId}`);
    
    if (!betData) {
      return res.status(404).json({
        success: false,
        error: 'Bet not found'
      });
    }

    const bet = JSON.parse(betData);
    
    // Check if user owns this bet or is admin
    if (bet.userId !== req.user.id && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    res.json({
      success: true,
      data: bet
    });

  } catch (error) {
    logger.error('Error getting bet:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

// Cancel a bet
router.post('/:betId/cancel', auth, async (req, res) => {
  try {
    const { betId } = req.params;
    const userId = req.user.id;

    const betData = await get(`bet:${betId}`);
    if (!betData) {
      return res.status(404).json({
        success: false,
        error: 'Bet not found'
      });
    }

    const bet = JSON.parse(betData);
    
    if (bet.userId !== userId) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    if (bet.status !== BET_STATUS.PENDING && bet.status !== BET_STATUS.ACTIVE) {
      return res.status(400).json({
        success: false,
        error: 'Bet cannot be cancelled'
      });
    }

    // Cancel bet
    bet.status = BET_STATUS.CANCELLED;
    bet.cancelledAt = Date.now();

    // Refund bet
    await bettingEngine.refundBet(bet);

    // Update stored bet
    await setWithExpiry(`bet:${betId}`, JSON.stringify(bet), 86400);

    // Remove from active bets
    bettingEngine.activeBets.delete(betId);

    res.json({
      success: true,
      data: bet
    });

  } catch (error) {
    logger.error('Error cancelling bet:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

// Get user's betting history
router.get('/user/:userId/history', auth, async (req, res) => {
  try {
    const { userId } = req.params;
    const { limit = 50, offset = 0 } = req.query;

    // Check access
    if (userId !== req.user.id && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const betIds = await zrevrange(`user:${userId}:bets`, offset, offset + limit - 1);
    const bets = [];

    for (const betId of betIds) {
      const betData = await get(`bet:${betId}`);
      if (betData) {
        bets.push(JSON.parse(betData));
      }
    }

    const total = await zcard(`user:${userId}:bets`);

    res.json({
      success: true,
      data: bets,
      total,
      limit: parseInt(limit),
      offset: parseInt(offset),
      hasMore: (offset + limit) < total
    });

  } catch (error) {
    logger.error('Error getting betting history:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

// Get stream betting activity
router.get('/stream/:streamId/activity', async (req, res) => {
  try {
    const { streamId } = req.params;
    const { limit = 100 } = req.query;

    const betIds = await zrevrange(`stream:${streamId}:bets`, 0, limit - 1);
    const recentBets = [];

    for (const betId of betIds) {
      const betData = await get(`bet:${betId}`);
      if (betData) {
        const bet = JSON.parse(betData);
        // Remove sensitive user info for public display
        recentBets.push({
          id: bet.id,
          betType: bet.betType,
          amount: bet.amount,
          odds: bet.odds,
          status: bet.status,
          timestamp: bet.timestamp
        });
      }
    }

    // Calculate statistics
    const totalBets = await zcard(`stream:${streamId}:bets`);
    const totalAmount = recentBets.reduce((sum, bet) => sum + bet.amount, 0);
    const activeBets = recentBets.filter(bet => bet.status === BET_STATUS.ACTIVE).length;

    res.json({
      success: true,
      data: {
        recentBets,
        statistics: {
          totalBets,
          totalAmount,
          activeBets
        }
      }
    });

  } catch (error) {
    logger.error('Error getting stream betting activity:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

// Get available bet types
router.get('/types', (req, res) => {
  res.json({
    success: true,
    data: Object.values(BET_TYPES)
  });
});

// Get user balance
router.get('/balance/:streamId', auth, async (req, res) => {
  try {
    const { streamId } = req.params;
    const userId = req.user.id;

    const balance = await bettingEngine.getUserBalance(userId, streamId);
    const reserved = parseFloat(await get(`reserved:${userId}:${streamId}`)) || 0;

    res.json({
      success: true,
      data: {
        balance,
        reserved,
        available: balance - reserved
      }
    });

  } catch (error) {
    logger.error('Error getting balance:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

// Admin route to settle bets (would normally be called by orchestrator)
router.post('/:betId/settle', auth, async (req, res) => {
  try {
    if (!req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Admin access required'
      });
    }

    const { betId } = req.params;
    const { outcome } = req.body;

    const result = await bettingEngine.settleBet(betId, outcome);

    res.json({
      success: result,
      message: result ? 'Bet settled' : 'Failed to settle bet'
    });

  } catch (error) {
    logger.error('Error settling bet:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

// Export betting engine for use by orchestrator
module.exports = { router, bettingEngine }; 