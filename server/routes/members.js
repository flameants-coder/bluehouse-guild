const express = require('express');
const router = express.Router();
const Member = require('../models/Member');

// 取得所有成員
router.get('/', async (req, res) => {
    try {
        const members = await Member.find().sort({ name: 1 });
        res.json(members);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 新增成員
router.post('/', async (req, res) => {
    try {
        const member = new Member(req.body);
        const savedMember = await member.save();
        res.status(201).json(savedMember);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 批量新增/更新成員
router.post('/bulk', async (req, res) => {
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

// 刪除成員
router.delete('/:id', async (req, res) => {
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

// 清空所有成員
router.delete('/', async (req, res) => {
    try {
        await Member.deleteMany({});
        res.json({ message: '所有成員已清空' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
