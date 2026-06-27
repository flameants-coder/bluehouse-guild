const mongoose = require('mongoose');

const memberSchema = new mongoose.Schema({
    name: {
        type: String,
        required: true,
        trim: true
    },
    role: {
        type: String,
        enum: ['成員', '公會長'],
        default: '成員'
    },
    joinDate: {
        type: Date,
        default: Date.now
    }
}, {
    timestamps: true
});

// 建立名稱索引（不區分大小寫搜尋）
memberSchema.index({ name: 1 });

module.exports = mongoose.model('Member', memberSchema);
