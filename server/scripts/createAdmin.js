require('dotenv').config();
const mongoose = require('mongoose');
const User = require('../models/User');

const createAdmin = async () => {
    try {
        // 連接資料庫
        await mongoose.connect(process.env.MONGODB_URI);
        console.log('MongoDB 連接成功');

        // 檢查是否已有管理員
        const existingAdmin = await User.findOne({ role: 'admin' });
        if (existingAdmin) {
            console.log('管理員帳號已存在:', existingAdmin.username);
            console.log('如需重設密碼，請使用登入後的修改密碼功能');
            process.exit(0);
        }

        // 從命令列參數或環境變數取得帳密
        const username = process.argv[2] || process.env.ADMIN_USERNAME || 'admin';
        const password = process.argv[3] || process.env.ADMIN_PASSWORD;

        if (!password) {
            console.error('請提供密碼！');
            console.log('使用方式: node scripts/createAdmin.js <username> <password>');
            console.log('或設定環境變數 ADMIN_PASSWORD');
            process.exit(1);
        }

        if (password.length < 8) {
            console.error('密碼至少需要 8 個字元');
            process.exit(1);
        }

        // 建立管理員
        const admin = new User({
            username,
            password,
            role: 'admin'
        });

        await admin.save();
        console.log('管理員帳號建立成功！');
        console.log(`帳號: ${username}`);
        console.log('請妥善保管密碼，並在首次登入後更改密碼。');

    } catch (error) {
        console.error('建立管理員失敗:', error.message);
    } finally {
        await mongoose.disconnect();
        process.exit(0);
    }
};

createAdmin();
