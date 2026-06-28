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

// 彙整記錄 - 依遊戲ID合併舊記錄，保留最新5000筆 (需管理員權限)
router.post('/aggregate', adminOnly, async (req, res) => {
    try {
        const KEEP_RECENT = 5000; // 保留最新的記錄數量
        const originalCount = await EnergyRecord.countDocuments();

        if (originalCount <= KEEP_RECENT) {
            return res.json({
                message: `記錄數量 (${originalCount}) 未超過 ${KEEP_RECENT} 筆，無需彙整`,
                originalCount,
                aggregatedCount: 0
            });
        }

        // 取得最新的 5000 筆記錄的 ID（這些要保留）
        const recentRecords = await EnergyRecord.find()
            .sort({ datetime: -1 })
            .limit(KEEP_RECENT)
            .select('_id');
        const recentIds = recentRecords.map(r => r._id);

        // 取得要彙整的舊記錄（不在最新 5000 筆中的）
        const oldRecords = await EnergyRecord.find({
            _id: { $nin: recentIds }
        });

        if (oldRecords.length === 0) {
            return res.json({
                message: '沒有舊記錄可彙整',
                originalCount,
                aggregatedCount: 0
            });
        }

        // 彙整舊記錄：依遊戲ID統計
        const aggregated = {};
        oldRecords.forEach(record => {
            const name = record.memberName;
            if (!aggregated[name]) {
                aggregated[name] = {
                    memberName: name,
                    totalIncome: 0,
                    totalExpense: 0,
                    recordCount: 0
                };
            }
            if (record.quantity > 0) {
                aggregated[name].totalIncome += record.quantity;
            } else {
                aggregated[name].totalExpense += record.quantity;
            }
            aggregated[name].recordCount++;
        });

        // 刪除舊記錄
        await EnergyRecord.deleteMany({ _id: { $nin: recentIds } });

        // 建立彙整後的記錄
        const now = new Date();
        const newRecords = [];

        Object.values(aggregated).forEach(member => {
            // 如果有收入，建立一筆收入彙整記錄
            if (member.totalIncome > 0) {
                newRecords.push({
                    memberName: member.memberName,
                    action: '收入',
                    quantity: member.totalIncome,
                    datetime: now,
                    note: `彙整記錄 (原 ${member.recordCount} 筆)`
                });
            }
            // 如果有支出，建立一筆支出彙整記錄
            if (member.totalExpense < 0) {
                newRecords.push({
                    memberName: member.memberName,
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

        const finalCount = await EnergyRecord.countDocuments();

        res.json({
            message: '記錄彙整完成',
            originalCount,
            keptRecent: KEEP_RECENT,
            oldRecordsAggregated: oldRecords.length,
            newAggregatedRecords: newRecords.length,
            finalCount,
            savedRecords: originalCount - finalCount
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
