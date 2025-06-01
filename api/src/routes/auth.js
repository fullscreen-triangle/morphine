const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');
const { setWithExpiry, get } = require('../services/redis');

const router = express.Router();

const JWT_SECRET = process.env.JWT_SECRET || 'your_jwt_secret_here';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '24h';

// Register new user
router.post('/register', async (req, res) => {
  try {
    const { username, email, password } = req.body;

    // Validate input
    if (!username || !email || !password) {
      return res.status(400).json({
        success: false,
        error: 'Username, email, and password are required'
      });
    }

    // Check if user already exists
    const existingUser = await get(`user:email:${email}`);
    if (existingUser) {
      return res.status(409).json({
        success: false,
        error: 'User with this email already exists'
      });
    }

    // Hash password
    const saltRounds = 10;
    const hashedPassword = await bcrypt.hash(password, saltRounds);

    // Create user
    const user = {
      id: uuidv4(),
      username,
      email,
      password: hashedPassword,
      created_at: new Date().toISOString(),
      last_login: null,
      is_active: true
    };

    // Store user data
    await setWithExpiry(`user:${user.id}`, user, 86400 * 30); // 30 days
    await setWithExpiry(`user:email:${email}`, user.id, 86400 * 30);
    await setWithExpiry(`user:username:${username}`, user.id, 86400 * 30);

    // Generate JWT token
    const token = jwt.sign(
      { userId: user.id, email: user.email },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    logger.info(`User registered: ${user.id} (${email})`);

    // Return user data without password
    const { password: _, ...userWithoutPassword } = user;

    res.status(201).json({
      success: true,
      user: userWithoutPassword,
      token
    });
  } catch (error) {
    logger.error('Registration failed:', error.message);
    res.status(500).json({
      success: false,
      error: 'Registration failed',
      message: error.message
    });
  }
});

// Login user
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    // Validate input
    if (!email || !password) {
      return res.status(400).json({
        success: false,
        error: 'Email and password are required'
      });
    }

    // Get user by email
    const userId = await get(`user:email:${email}`);
    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    const user = await get(`user:${userId}`);
    if (!user || !user.is_active) {
      return res.status(401).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    // Verify password
    const isPasswordValid = await bcrypt.compare(password, user.password);
    if (!isPasswordValid) {
      return res.status(401).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    // Update last login
    user.last_login = new Date().toISOString();
    await setWithExpiry(`user:${user.id}`, user, 86400 * 30);

    // Generate JWT token
    const token = jwt.sign(
      { userId: user.id, email: user.email },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    logger.info(`User logged in: ${user.id} (${email})`);

    // Return user data without password
    const { password: _, ...userWithoutPassword } = user;

    res.json({
      success: true,
      user: userWithoutPassword,
      token
    });
  } catch (error) {
    logger.error('Login failed:', error.message);
    res.status(500).json({
      success: false,
      error: 'Login failed',
      message: error.message
    });
  }
});

// Get user profile
router.get('/profile', authenticateToken, async (req, res) => {
  try {
    const user = await get(`user:${req.user.userId}`);
    if (!user) {
      return res.status(404).json({
        success: false,
        error: 'User not found'
      });
    }

    // Return user data without password
    const { password: _, ...userWithoutPassword } = user;

    res.json({
      success: true,
      user: userWithoutPassword
    });
  } catch (error) {
    logger.error('Failed to fetch user profile:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch user profile',
      message: error.message
    });
  }
});

// Update user profile
router.patch('/profile', authenticateToken, async (req, res) => {
  try {
    const user = await get(`user:${req.user.userId}`);
    if (!user) {
      return res.status(404).json({
        success: false,
        error: 'User not found'
      });
    }

    // Update allowed fields
    const allowedUpdates = ['username', 'email'];
    const updates = {};
    
    for (const field of allowedUpdates) {
      if (req.body[field] !== undefined) {
        updates[field] = req.body[field];
      }
    }

    // Update user
    const updatedUser = {
      ...user,
      ...updates,
      updated_at: new Date().toISOString()
    };

    await setWithExpiry(`user:${user.id}`, updatedUser, 86400 * 30);

    logger.info(`User profile updated: ${user.id}`);

    // Return user data without password
    const { password: _, ...userWithoutPassword } = updatedUser;

    res.json({
      success: true,
      user: userWithoutPassword
    });
  } catch (error) {
    logger.error('Failed to update user profile:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to update user profile',
      message: error.message
    });
  }
});

// Middleware to authenticate JWT token
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({
      success: false,
      error: 'Access token required'
    });
  }

  jwt.verify(token, JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({
        success: false,
        error: 'Invalid or expired token'
      });
    }
    req.user = user;
    next();
  });
}

module.exports = router; 