const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const User = require('../models/User');
const { authenticateToken } = require('../middleware/auth');

// POST /api/auth/login - 登入
router.post('/login', async (req, res) => {
    try {
        const { username, password } = req.body;

        // 驗證輸入
        if (!username || !password) {
            return res.status(400).json({ message: '請輸入帳號和密碼' });
        }

        // 查找用戶
        const user = await User.findOne({ username: username.toLowerCase() });
        if (!user) {
            return res.status(401).json({ message: '帳號或密碼錯誤' });
        }

        // 驗證密碼
        const isMatch = await user.comparePassword(password);
        if (!isMatch) {
            return res.status(401).json({ message: '帳號或密碼錯誤' });
        }

        // 更新最後登入時間
        user.lastLogin = new Date();
        await user.save();

        // 產生 JWT Token
        const token = jwt.sign(
            {
                userId: user._id,
                username: user.username,
                role: user.role
            },
            process.env.JWT_SECRET,
            { expiresIn: '7d' }  // Token 有效期 7 天
        );

        res.json({
            message: '登入成功',
            token,
            user: {
                username: user.username,
                role: user.role
            }
        });
    } catch (error) {
        console.error('登入錯誤:', error);
        res.status(500).json({ message: '伺服器錯誤' });
    }
});

// GET /api/auth/me - 驗證 Token 並取得用戶資訊
router.get('/me', authenticateToken, async (req, res) => {
    try {
        const user = await User.findById(req.user.userId).select('-password');
        if (!user) {
            return res.status(404).json({ message: '用戶不存在' });
        }

        res.json({
            user: {
                username: user.username,
                role: user.role
            }
        });
    } catch (error) {
        console.error('取得用戶資訊錯誤:', error);
        res.status(500).json({ message: '伺服器錯誤' });
    }
});

// POST /api/auth/change-password - 修改密碼 (需認證)
router.post('/change-password', authenticateToken, async (req, res) => {
    try {
        const { currentPassword, newPassword } = req.body;

        if (!currentPassword || !newPassword) {
            return res.status(400).json({ message: '請提供當前密碼和新密碼' });
        }

        if (newPassword.length < 8) {
            return res.status(400).json({ message: '新密碼至少需要 8 個字元' });
        }

        const user = await User.findById(req.user.userId);
        const isMatch = await user.comparePassword(currentPassword);

        if (!isMatch) {
            return res.status(401).json({ message: '當前密碼錯誤' });
        }

        user.password = newPassword;
        await user.save();

        res.json({ message: '密碼已更新' });
    } catch (error) {
        console.error('修改密碼錯誤:', error);
        res.status(500).json({ message: '伺服器錯誤' });
    }
});

module.exports = router;
