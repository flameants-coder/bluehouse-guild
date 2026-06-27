const express = require('express');
const router = express.Router();
const Season = require('../models/Season');

// 取得所有賽季
router.get('/', async (req, res) => {
    try {
        const seasons = await Season.find().sort({ createdAt: -1 });
        res.json(seasons);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 取得單一賽季
router.get('/:id', async (req, res) => {
    try {
        const season = await Season.findById(req.params.id);
        if (!season) {
            return res.status(404).json({ message: '找不到該賽季' });
        }
        res.json(season);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// 新增賽季
router.post('/', async (req, res) => {
    try {
        const season = new Season({
            name: req.body.name,
            scores: {
                hideoutCore: [],
                crystalSpider: [],
                hellGate: [],
                bottomlessAbyss: []
            },
            lottery: {
                prizes: [],
                history: [],
                usedTickets: {}
            }
        });
        const savedSeason = await season.save();
        res.status(201).json(savedSeason);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 刪除賽季
router.delete('/:id', async (req, res) => {
    try {
        const season = await Season.findByIdAndDelete(req.params.id);
        if (!season) {
            return res.status(404).json({ message: '找不到該賽季' });
        }
        res.json({ message: '賽季已刪除' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// ==================== 力量點相關 ====================

// 更新力量點分數
router.put('/:id/scores/:activity', async (req, res) => {
    try {
        const { id, activity } = req.params;
        const { scores } = req.body;

        const validActivities = ['hideoutCore', 'crystalSpider', 'hellGate', 'bottomlessAbyss'];
        if (!validActivities.includes(activity)) {
            return res.status(400).json({ message: '無效的活動類型' });
        }

        const season = await Season.findById(id);
        if (!season) {
            return res.status(404).json({ message: '找不到該賽季' });
        }

        season.scores[activity] = scores;
        await season.save();

        res.json(season);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 清除賽季力量點數據
router.delete('/:id/scores', async (req, res) => {
    try {
        const season = await Season.findById(req.params.id);
        if (!season) {
            return res.status(404).json({ message: '找不到該賽季' });
        }

        season.scores = {
            hideoutCore: [],
            crystalSpider: [],
            hellGate: [],
            bottomlessAbyss: []
        };
        await season.save();

        res.json({ message: '力量點數據已清除' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// ==================== 抽獎相關 ====================

// 更新獎品列表
router.put('/:id/lottery/prizes', async (req, res) => {
    try {
        const season = await Season.findById(req.params.id);
        if (!season) {
            return res.status(404).json({ message: '找不到該賽季' });
        }

        season.lottery.prizes = req.body.prizes;
        await season.save();

        res.json(season.lottery);
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 記錄抽獎結果
router.post('/:id/lottery/draw', async (req, res) => {
    try {
        const season = await Season.findById(req.params.id);
        if (!season) {
            return res.status(404).json({ message: '找不到該賽季' });
        }

        const { player, prize, prizeIndex } = req.body;
        const playerKey = player.toLowerCase();

        // 新增中獎記錄
        season.lottery.history.push({
            player,
            prize,
            prizeIndex,
            time: new Date()
        });

        // 更新已使用的抽獎券
        const currentUsed = season.lottery.usedTickets.get(playerKey) || 0;
        season.lottery.usedTickets.set(playerKey, currentUsed + 1);

        await season.save();

        res.json({
            message: '抽獎結果已記錄',
            history: season.lottery.history,
            usedTickets: Object.fromEntries(season.lottery.usedTickets)
        });
    } catch (error) {
        res.status(400).json({ message: error.message });
    }
});

// 清除抽獎記錄
router.delete('/:id/lottery/history', async (req, res) => {
    try {
        const season = await Season.findById(req.params.id);
        if (!season) {
            return res.status(404).json({ message: '找不到該賽季' });
        }

        season.lottery.history = [];
        season.lottery.usedTickets = new Map();
        await season.save();

        res.json({ message: '抽獎記錄已清除' });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;
