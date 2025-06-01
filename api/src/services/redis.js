const redis = require('redis');
const logger = require('../utils/logger');

let client = null;

async function connectRedis() {
  try {
    const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
    
    client = redis.createClient({
      url: redisUrl,
      retry_strategy: (options) => {
        if (options.error && options.error.code === 'ECONNREFUSED') {
          logger.error('Redis server refused connection');
          return new Error('Redis server refused connection');
        }
        if (options.total_retry_time > 1000 * 60 * 60) {
          logger.error('Redis retry time exhausted');
          return new Error('Retry time exhausted');
        }
        if (options.attempt > 10) {
          logger.error('Redis max retry attempts reached');
          return undefined;
        }
        // Reconnect after
        return Math.min(options.attempt * 100, 3000);
      }
    });

    client.on('error', (err) => {
      logger.error('Redis Client Error:', err);
    });

    client.on('connect', () => {
      logger.info('Connected to Redis');
    });

    client.on('reconnecting', () => {
      logger.info('Reconnecting to Redis...');
    });

    client.on('ready', () => {
      logger.info('Redis client ready');
    });

    await client.connect();
    
    // Test the connection
    await client.ping();
    logger.info('Redis connection established successfully');
    
    return client;
  } catch (error) {
    logger.error('Failed to connect to Redis:', error);
    throw error;
  }
}

function getRedisClient() {
  if (!client) {
    throw new Error('Redis client not initialized. Call connectRedis() first.');
  }
  return client;
}

async function disconnectRedis() {
  if (client) {
    await client.quit();
    client = null;
    logger.info('Disconnected from Redis');
  }
}

// Helper functions for common Redis operations
async function setWithExpiry(key, value, expirySeconds = 3600) {
  const redisClient = getRedisClient();
  return await redisClient.setEx(key, expirySeconds, JSON.stringify(value));
}

async function get(key) {
  const redisClient = getRedisClient();
  const value = await redisClient.get(key);
  return value ? JSON.parse(value) : null;
}

async function del(key) {
  const redisClient = getRedisClient();
  return await redisClient.del(key);
}

async function exists(key) {
  const redisClient = getRedisClient();
  return await redisClient.exists(key);
}

async function zadd(key, score, member) {
  const redisClient = getRedisClient();
  return await redisClient.zAdd(key, { score, value: JSON.stringify(member) });
}

async function zrange(key, start, stop) {
  const redisClient = getRedisClient();
  const results = await redisClient.zRange(key, start, stop);
  return results.map(item => JSON.parse(item));
}

async function zrangeByScore(key, min, max) {
  const redisClient = getRedisClient();
  const results = await redisClient.zRangeByScore(key, min, max);
  return results.map(item => JSON.parse(item));
}

module.exports = {
  connectRedis,
  getRedisClient,
  disconnectRedis,
  setWithExpiry,
  get,
  del,
  exists,
  zadd,
  zrange,
  zrangeByScore
}; 