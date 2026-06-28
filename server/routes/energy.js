const express = require('express');
const router = express.Router();
const EnergyRecord = require('../models/EnergyRecord');
const { adminOnly } = require('../middleware/auth');

// 取得所有記錄（支援分頁和篩選）
router.get('/', async (req, res) => {
    try {
        const { page = 1, limit = 50, member, action, startDate, endDate } = req.query;

        const query = {};
        if (member) query.memberName = new RegExp(member, 'i');
        if (action) query.action = action;
        if (startDate || endDate) {
            query.datetime = {};
            if (startDate) query.datetime.$gte = new Date(startDate);
            if (endDate) query.datetime.$lte = new Date(endDate);
        }

        const records = await EnergyRecord.find(query)
            .sort({ datetime: -1 })
            .skip((page - 1) * limit)
            .limit(parseInt(limit));

        const total = await EnergyRecord.countDocuments(query);

        res.json({
            records,
            pagination: {
                page: parseInt(page),
                limit: parseInt(limit),
                total,
                pages: Math.ceil(total / limit)
            }
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 取得統計數據
router.get('/stats', async (req, res) => {
    try {
        const stats = await EnergyRecord.aggregate([
            {
                $group: {
                    _id: '$action',
                    total: { $sum: '$quantity' },
                    count: { $sum: 1 }
                }
            }
        ]);

        const memberStats = await EnergyRecord.aggregate([
            {
                $group: {
                    _id: '$memberName',
                    income: {
                        $sum: { $cond: [{ $eq: ['$action', '收入'] }, '$quantity', 0] }
                    },
                    expense: {
                        $sum: { $cond: [{ $eq: ['$action', '支出'] }, '$quantity', 0] }
                    },
                    recordCount: { $sum: 1 }
                }
            },
            { $sort: { expense: -1 } }
        ]);

        res.json({ stats, memberStats });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 新增記錄 (需管理員權限)
router.post('/', adminOnly, async (req, res) => {
    try {
        const record = new EnergyRecord(req.body);
        const savedRecord = await record.save();
        res.status(201).json(savedRecord);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 批量新增記錄 (需管理員權限)
router.post('/bulk', adminOnly, async (req, res) => {
    try {
        const { records } = req.body;
        const savedRecords = await EnergyRecord.insertMany(records);
        res.status(201).json({
            message: `已新增 ${savedRecords.length} 筆記錄`,
            records: savedRecords
        });
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 刪除記錄 (需管理員權限)
router.delete('/:id', adminOnly, async (req, res) => {
    try {
        const record = await EnergyRecord.findByIdAndDelete(req.params.id);
        if (!record) {
            return res.status(404).json({ message: '找不到該記錄' });
        }
        res.json({ message: '記錄已刪除' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 清空所有記錄 (需管理員權限)
router.delete('/', adminOnly, async (req, res) => {
    try {
        await EnergyRecord.deleteMany({});
        res.json({ message: '所有記錄已清空' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 彙整記錄 - 依遊戲ID合併所有記錄 (需管理員權限)
router.post('/aggregate', adminOnly, async (req, res) => {
    try {
        // 先統計每個成員的收入和支出總量
        const aggregation = await EnergyRecord.aggregate([
            {
                $group: {
                    _id: '$memberName',
                    totalIncome: {
                        $sum: { $cond: [{ $eq: ['$action', '收入'] }, '$quantity', 0] }
                    },
                    totalExpense: {
                        $sum: { $cond: [{ $eq: ['$action', '支出'] }, '$quantity', 0] }
                    },
                    recordCount: { $sum: 1 }
                }
            }
        ]);

        if (aggregation.length === 0) {
            return res.json({ message: '沒有記錄可彙整', aggregatedCount: 0 });
        }

        const originalCount = await EnergyRecord.countDocuments();

        // 刪除所有舊記錄
        await EnergyRecord.deleteMany({});

        // 建立彙整後的記錄
        const now = new Date();
        const newRecords = [];

        aggregation.forEach(member => {
            // 如果有收入，建立一筆收入彙整記錄
            if (member.totalIncome > 0) {
                newRecords.push({
                    memberName: member._id,
                    action: '收入',
                    quantity: member.totalIncome,
                    datetime: now,
                    note: `彙整記錄 (原 ${member.recordCount} 筆)`
                });
            }
            // 如果有支出，建立一筆支出彙整記錄
            if (member.totalExpense < 0) {
                newRecords.push({
                    memberName: member._id,
                    action: '支出',
                    quantity: member.totalExpense,
                    datetime: now,
                    note: `彙整記錄 (原 ${member.recordCount} 筆)`
                });
            }
        });

        // 插入彙整後的記錄
        if (newRecords.length > 0) {
            await EnergyRecord.insertMany(newRecords);
        }

        res.json({
            message: '記錄彙整完成',
            originalCount,
            aggregatedCount: newRecords.length,
            memberCount: aggregation.length,
            savedRecords: originalCount - newRecords.length
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
