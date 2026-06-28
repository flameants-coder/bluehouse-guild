const mongoose = require('mongoose');

// 分數項目的子 schema
const scoreEntrySchema = new mongoose.Schema({
    player: {
        type: String,
        required: true,
        maxlength: [50, '玩家名稱不可超過 50 個字元']
    },
    score: {
        type: Number,
        required: true,
        min: [0, '分數不可為負數'],
        max: [99999999, '分數不可超過 99,999,999']
    }
}, { _id: false });

// 抽獎記錄的子 schema
const lotteryHistorySchema = new mongoose.Schema({
    player: {
        type: String,
        required: true,
        maxlength: [50, '玩家名稱不可超過 50 個字元']
    },
    prize: {
        type: String,
        required: true,
        maxlength: [100, '獎品名稱不可超過 100 個字元']
    },
    prizeIndex: {
        type: Number,
        min: 0
    },
    time: {
        type: Date,
        default: Date.now
    }
}, { _id: false });

const seasonSchema = new mongoose.Schema({
    name: {
        type: String,
        required: [true, '賽季名稱為必填'],
        trim: true,
        minlength: [1, '賽季名稱至少需要 1 個字元'],
        maxlength: [50, '賽季名稱不可超過 50 個字元']
    },
    isActive: {
        type: Boolean,
        default: true
    },
    // 力量點分數
    scores: {
        hideoutCore: [scoreEntrySchema],
        crystalSpider: [scoreEntrySchema],
        hellGate: [scoreEntrySchema],
        bottomlessAbyss: [scoreEntrySchema]
    },
    // 抽獎數據
    lottery: {
        prizes: {
            type: [String],
            validate: {
                validator: function(v) {
                    return v.every(prize => typeof prize === 'string' && prize.length <= 100);
                },
                message: '獎品名稱不可超過 100 個字元'
            }
        },
        history: [lotteryHistorySchema],
        usedTickets: {
            type: Map,
            of: Number,
            default: new Map()
        }
    }
}, {
    timestamps: true
});

// 建立索引
seasonSchema.index({ createdAt: -1 });
seasonSchema.index({ isActive: 1 });

module.exports = mongoose.model('Season', seasonSchema);
