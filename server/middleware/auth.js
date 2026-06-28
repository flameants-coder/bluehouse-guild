const jwt = require('jsonwebtoken');

// 驗證 Token 中間件
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ message: '未提供認證 Token' });
    }

    const token = authHeader.split(' ')[1];

    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        req.user = decoded;
        next();
    } catch (error) {
        if (error.name === 'TokenExpiredError') {
            return res.status(401).json({ message: 'Token 已過期，請重新登入' });
        }
        return res.status(401).json({ message: 'Token 無效' });
    }
};

// 驗證管理員權限中間件
const requireAdmin = (req, res, next) => {
    if (!req.user || req.user.role !== 'admin') {
        return res.status(403).json({ message: '需要管理員權限' });
    }
    next();
};

// 組合：驗證 Token + 驗證管理員
const adminOnly = [authenticateToken, requireAdmin];

module.exports = {
    authenticateToken,
    requireAdmin,
    adminOnly
};
