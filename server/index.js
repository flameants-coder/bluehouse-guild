require('dotenv').config();
const express = require('express');
const cors = require('cors');
const connectDB = require('./config/db');

// 路由
const authRouter = require('./routes/auth');
const membersRouter = require('./routes/members');
const energyRouter = require('./routes/energy');
const seasonsRouter = require('./routes/seasons');

const app = express();

// 連接數據庫
connectDB();

// 中間件
app.use(cors());
app.use(express.json());

// API 路由
app.use('/api/auth', authRouter);
app.use('/api/members', membersRouter);
app.use('/api/energy', energyRouter);
app.use('/api/seasons', seasonsRouter);

// 根路由
app.get('/', (req, res) => {
    res.json({
        message: 'Blue House 公會管理系統 API',
        version: '1.0.0',
        endpoints: {
            auth: '/api/auth',
            members: '/api/members',
            energy: '/api/energy',
            seasons: '/api/seasons'
        }
    });
});

// 錯誤處理
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ message: '伺服器錯誤' });
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
    console.log(`伺服器運行於 port ${PORT}`);
});
