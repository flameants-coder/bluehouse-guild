const mongoose = require('mongoose');

const energyRecordSchema = new mongoose.Schema({
    memberName: {
        type: String,
        required: true,
        trim: true
    },
    action: {
        type: String,
        enum: ['收入', '支出'],
        required: true
    },
    quantity: {
        type: Number,
        required: true
    },
    datetime: {
        type: Date,
        required: true
    },
    note: {
        type: String,
        default: ''
    }
}, {
    timestamps: true
});

// 建立索引以優化查詢
energyRecordSchema.index({ memberName: 1 });
energyRecordSchema.index({ datetime: -1 });
energyRecordSchema.index({ action: 1 });

module.exports = mongoose.model('EnergyRecord', energyRecordSchema);
