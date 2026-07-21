const express = require('express');
const router = express.Router();
const Equipment = require('../models/Equipment');
const { adminOnly } = require('../middleware/auth');

// 取得所有裝備庫存
// 查詢參數：
//   tier: 依有效階級篩選（可選；傳 "none" 代表無階級）
//   search: 搜尋裝備名稱（可選）
router.get('/', async (req, res) => {
    try {
        const { tier, search } = req.query;
        const query = {};
        if (tier === 'none') {
            query.tier = null;
        } else if (tier) {
            query.tier = parseInt(tier);
        }
        if (search) {
            query.name = { $regex: search, $options: 'i' };
        }
        const equipment = await Equipment.find(query).sort({ tier: 1, name: 1 });
        res.json(equipment);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 新增裝備 (需管理員權限)
router.post('/', adminOnly, async (req, res) => {
    try {
        const equipment = new Equipment(req.body);
        const saved = await equipment.save();
        res.status(201).json(saved);
    } catch (error) {
        if (error.code === 11000) {
            return res.status(400).json({ message: '該名稱與階級的裝備已存在' });
        }
        res.status(400).json({ message: error.message });
    }
});

// 更新單一裝備 (需管理員權限)
router.put('/:id', adminOnly, async (req, res) => {
    try {
        const equipment = await Equipment.findByIdAndUpdate(
            req.params.id,
            { $set: req.body },
            { new: true, runValidators: true }
        );
        if (!equipment) {
            return res.status(404).json({ message: '找不到該裝備' });
        }
        res.json(equipment);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 累加匯入 (需管理員權限)
// body: { items: [{ name, tier, delta }] }
// 依 (name, tier) 對現有庫存做 $inc 累加，不存在則新建
router.post('/adjust', adminOnly, async (req, res) => {
    try {
        const { items } = req.body;
        if (!Array.isArray(items) || items.length === 0) {
            return res.status(400).json({ message: 'items 必須為非空陣列' });
        }
        const operations = items.map(it => ({
            updateOne: {
                filter: { name: it.name, tier: it.tier ?? null },
                update: {
                    $inc: { quantity: it.delta || 0 },
                    $setOnInsert: { minStock: 0, note: '' }
                },
                upsert: true
            }
        }));
        const result = await Equipment.bulkWrite(operations);
        res.json({ message: `已累加 ${items.length} 項裝備`, result });
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 刪除裝備 (需管理員權限)
router.delete('/:id', adminOnly, async (req, res) => {
    try {
        const equipment = await Equipment.findByIdAndDelete(req.params.id);
        if (!equipment) {
            return res.status(404).json({ message: '找不到該裝備' });
        }
        res.json({ message: '裝備已刪除' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 清空所有裝備 (需管理員權限)
router.delete('/', adminOnly, async (req, res) => {
    try {
        await Equipment.deleteMany({});
        res.json({ message: '所有裝備庫存已清空' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
