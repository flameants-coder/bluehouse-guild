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

// 抽獎券類別的子 schema（每個賽季可自訂：由哪些分數欄位合併、門檻、每張間隔）
const ticketCategorySchema = new mongoose.Schema({
    label: { type: String, required: true, maxlength: 30 },
    slots: { type: [String], default: [] },   // 對應 scores 的欄位鍵，多個代表合併計算
    threshold: { type: Number, default: 0, min: 0 },   // 達此分數得第 1 張
    increment: { type: Number, default: 0, min: 0 }    // 之後每隔此分數多 1 張（0 = 只給 1 張）
}, { _id: false });

// 賽季活動設定（每賽季獨立的活動名稱與抽獎券規則；未設定則前端套用預設）
const activityConfigSchema = new mongoose.Schema({
    labels: {
        hideoutCore: { type: String, maxlength: 30 },
        crystalSpider: { type: String, maxlength: 30 },
        hellGate: { type: String, maxlength: 30 },
        bottomlessAbyss: { type: String, maxlength: 30 }
    },
    ticketCategories: { type: [ticketCategorySchema], default: undefined }
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
    // 每賽季活動設定（活動名稱 + 抽獎券規則）；未設定時前端套用預設
    activityConfig: activityConfigSchema,
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
