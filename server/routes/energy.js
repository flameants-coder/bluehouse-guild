const express = require('express');
const router = express.Router();
const EnergyRecord = require('../models/EnergyRecord');
const { adminOnly } = require('../middleware/auth');
const { escapeRegex, sanitizePagination } = require('../utils/helpers');

// 取得所有記錄（支援分頁和篩選）
router.get('/', async (req, res) => {
    try {
        const { member, action, startDate, endDate } = req.query;
        // 虹吸能量記錄可能較多，提高 maxLimit 至 100000
        const { page, limit, skip } = sanitizePagination(req.query, { page: 1, limit: 50, maxLimit: 100000 });

        const query = {};
        // 使用轉義後的正則表達式防止 ReDoS 攻擊
        if (member) {
            query.memberName = new RegExp(escapeRegex(member), 'i');
        }
        if (action && ['收入', '支出'].includes(action)) {
            query.action = action;
        }
        if (startDate || endDate) {
            query.datetime = {};
            if (startDate) query.datetime.$gte = new Date(startDate);
            if (endDate) query.datetime.$lte = new Date(endDate);
        }

        const [records, total] = await Promise.all([
            EnergyRecord.find(query)
                .sort({ datetime: -1 })
                .skip(skip)
                .limit(limit)
                .lean(),
            EnergyRecord.countDocuments(query)
        ]);

        res.json({
            records,
            pagination: {
                page,
                limit,
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

        // 使用 ordered: false 讓 MongoDB 繼續處理即使遇到重複
        // 重複的記錄會被跳過，其他記錄仍會被插入
        const result = await EnergyRecord.insertMany(records, {
            ordered: false
        }).catch(err => {
            // 處理批量插入錯誤（包含重複鍵錯誤）
            if (err.code === 11000 || err.writeErrors) {
                // 返回成功插入的記錄
                return err.insertedDocs || [];
            }
            throw err;
        });

        const savedRecords = Array.isArray(result) ? result : [];
        const skippedCount = records.length - savedRecords.length;

        res.status(201).json({
            message: `已新增 ${savedRecords.length} 筆記錄` +
                     (skippedCount > 0 ? `，跳過 ${skippedCount} 筆重複記錄` : ''),
            records: savedRecords,
            skippedDuplicates: skippedCount
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

// 修復數據 - 確保 action 與 quantity 符號一致 (需管理員權限)
router.post('/fix-data', adminOnly, async (req, res) => {
    try {
        // 找出 action 與 quantity 符號不一致的記錄
        const inconsistentRecords = await EnergyRecord.find({
            $or: [
                { action: '收入', quantity: { $lt: 0 } },
                { action: '支出', quantity: { $gt: 0 } }
            ]
        });

        if (inconsistentRecords.length === 0) {
            return res.json({
                message: '所有記錄符號一致，無需修復',
                fixedCount: 0
            });
        }

        // 修復每筆記錄
        let fixedCount = 0;
        for (const record of inconsistentRecords) {
            if (record.action === '收入' && record.quantity < 0) {
                record.quantity = Math.abs(record.quantity);
            } else if (record.action === '支出' && record.quantity > 0) {
                record.quantity = -Math.abs(record.quantity);
            }
            await record.save();
            fixedCount++;
        }

        res.json({
            message: `數據修復完成`,
            fixedCount,
            details: `已修正 ${fixedCount} 筆記錄的符號一致性`
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
