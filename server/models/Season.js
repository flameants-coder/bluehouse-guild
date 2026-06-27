const mongoose = require('mongoose');

const seasonSchema = new mongoose.Schema({
    name: {
        type: String,
        required: true,
        trim: true
    },
    isActive: {
        type: Boolean,
        default: true
    },
    // 力量點分數
    scores: {
        hideoutCore: [{
            player: String,
            score: Number
        }],
        crystalSpider: [{
            player: String,
            score: Number
        }],
        hellGate: [{
            player: String,
            score: Number
        }],
        bottomlessAbyss: [{
            player: String,
            score: Number
        }]
    },
    // 抽獎數據
    lottery: {
        prizes: [String],
        history: [{
            player: String,
            prize: String,
            prizeIndex: Number,
            time: Date
        }],
        usedTickets: {
            type: Map,
            of: Number,
            default: {}
        }
    }
}, {
    timestamps: true
});

module.exports = mongoose.model('Season', seasonSchema);
