require('dotenv').config();
const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const mongoose = require('mongoose');
const connectDB = require('./config/db');

// 路由
const authRouter = require('./routes/auth');
const membersRouter = require('./routes/members');
const energyRouter = require('./routes/energy');
const seasonsRouter = require('./routes/seasons');
const equipmentRouter = require('./routes/equipment');

const app = express();

// 連接數據庫
connectDB();

// CORS 白名單設定
const allowedOrigins = [
    'https://flameants-coder.github.io',
    'http://localhost:3000',
    'http://localhost:5500',
    'http://127.0.0.1:5500'
];

const corsOptions = {
    origin: function (origin, callback) {
        // 允許無 origin 的請求（如 Postman、curl）在開發環境
        if (!origin && process.env.NODE_ENV !== 'production') {
            return callback(null, true);
        }
        if (!origin || allowedOrigins.includes(origin)) {
            callback(null, true);
        } else {
            callback(new Error('CORS 不允許此來源'));
        }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
};

// 通用速率限制：15 分鐘內最多 200 次請求
const generalLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 200,
    message: { message: '請求過於頻繁，請稍後再試' },
    standardHeaders: true,
    legacyHeaders: false
});

// 登入端點嚴格限制：1 小時內最多 10 次嘗試
const loginLimiter = rateLimit({
    windowMs: 60 * 60 * 1000,
    max: 10,
    message: { message: '登入嘗試次數過多，請 1 小時後再試' },
    standardHeaders: true,
    legacyHeaders: false
});

// 中間件
app.use(cors(corsOptions));
app.use(express.json({ limit: '2mb' }));
app.use('/api/', generalLimiter);

// API 路由（登入端點加上嚴格速率限制）
app.use('/api/auth/login', loginLimiter);
app.use('/api/auth', authRouter);
app.use('/api/members', membersRouter);
app.use('/api/energy', energyRouter);
app.use('/api/seasons', seasonsRouter);
app.use('/api/equipment', equipmentRouter);

// 健康檢查端點
app.get('/health', (req, res) => {
    const dbState = mongoose.connection.readyState;
    const dbStatus = {
        0: 'disconnected',
        1: 'connected',
        2: 'connecting',
        3: 'disconnecting'
    };

    res.json({
        status: dbState === 1 ? 'healthy' : 'unhealthy',
        timestamp: new Date().toISOString(),
        uptime: Math.floor(process.uptime()),
        database: dbStatus[dbState] || 'unknown',
        version: '1.0.0'
    });
});

// 根路由
app.get('/', (req, res) => {
    res.json({
        message: 'Blue House 公會管理系統 API',
        version: '1.0.0',
        endpoints: {
            auth: '/api/auth',
            members: '/api/members',
            energy: '/api/energy',
            seasons: '/api/seasons',
            equipment: '/api/equipment',
            health: '/health'
        }
    });
});

// 404 處理
app.use((req, res, next) => {
    res.status(404).json({ message: '找不到該端點' });
});

// 全局錯誤處理
app.use((err, req, res, next) => {
    console.error(`[${new Date().toISOString()}] Error:`, err.message);

    // CORS 錯誤
    if (err.message === 'CORS 不允許此來源') {
        return res.status(403).json({ message: err.message });
    }

    // Mongoose 驗證錯誤
    if (err.name === 'ValidationError') {
        const messages = Object.values(err.errors).map(e => e.message);
        return res.status(400).json({ message: '資料驗證失敗', errors: messages });
    }

    // Mongoose CastError (無效 ID)
    if (err.name === 'CastError') {
        return res.status(400).json({ message: '無效的 ID 格式' });
    }

    // JWT 錯誤
    if (err.name === 'JsonWebTokenError') {
        return res.status(401).json({ message: '無效的認證令牌' });
    }

    if (err.name === 'TokenExpiredError') {
        return res.status(401).json({ message: '認證令牌已過期' });
    }

    // 預設錯誤
    const statusCode = err.statusCode || 500;
    const message = process.env.NODE_ENV === 'production'
        ? '伺服器錯誤'
        : err.message;

    res.status(statusCode).json({ message });
});

const PORT = process.env.PORT || 3000;

// 優雅關閉
const server = app.listen(PORT, () => {
    console.log(`伺服器運行於 port ${PORT}`);
});

process.on('SIGTERM', () => {
    console.log('收到 SIGTERM，開始優雅關閉...');
    server.close(() => {
        mongoose.connection.close(false, () => {
            console.log('資料庫連接已關閉');
            process.exit(0);
        });
    });
});
