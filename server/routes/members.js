const express = require('express');
const router = express.Router();
const Member = require('../models/Member');
const { adminOnly } = require('../middleware/auth');

// 取得成員（支援分頁）
// 查詢參數：
//   page: 頁碼（從 1 開始，預設 1）
//   limit: 每頁數量（不提供則返回全部，向後相容）
//   search: 搜尋成員名稱（可選）
router.get('/', async (req, res) => {
    try {
        const { page, limit, search } = req.query;

        // 建立查詢條件
        const query = {};
        if (search) {
            query.name = { $regex: search, $options: 'i' };
        }

        // 無分頁參數時，返回全部資料（向後相容）
        if (!limit) {
            const members = await Member.find(query).sort({ name: 1 });
            return res.json(members);
        }

        // 有分頁參數時，返回分頁結果
        const pageNum = Math.max(1, parseInt(page) || 1);
        const limitNum = Math.max(1, Math.min(500, parseInt(limit) || 50));
        const skip = (pageNum - 1) * limitNum;

        const [members, total] = await Promise.all([
            Member.find(query).sort({ name: 1 }).skip(skip).limit(limitNum),
            Member.countDocuments(query)
        ]);

        res.json({
            data: members,
            pagination: {
                page: pageNum,
                limit: limitNum,
                total,
                totalPages: Math.ceil(total / limitNum)
            }
        });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 新增成員 (需管理員權限)
router.post('/', adminOnly, async (req, res) => {
    try {
        const member = new Member(req.body);
        const savedMember = await member.save();
        res.status(201).json(savedMember);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 批量新增/更新成員 (需管理員權限)
router.post('/bulk', adminOnly, async (req, res) => {
    try {
        const { members } = req.body;
        const operations = members.map(m => ({
            updateOne: {
                filter: { name: m.name },
                update: { $set: m },
                upsert: true
            }
        }));
        const result = await Member.bulkWrite(operations);
        res.json({ message: `已處理 ${members.length} 筆成員資料`, result });
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 刪除成員 (需管理員權限)
router.delete('/:id', adminOnly, async (req, res) => {
    try {
        const member = await Member.findByIdAndDelete(req.params.id);
        if (!member) {
            return res.status(404).json({ message: '找不到該成員' });
        }
        res.json({ message: '成員已刪除' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 清空所有成員 (需管理員權限)
router.delete('/', adminOnly, async (req, res) => {
    try {
        await Member.deleteMany({});
        res.json({ message: '所有成員已清空' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
