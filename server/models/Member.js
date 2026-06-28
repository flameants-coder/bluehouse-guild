const mongoose = require('mongoose');

const memberSchema = new mongoose.Schema({
    name: {
        type: String,
        required: [true, '成員名稱為必填'],
        trim: true,
        minlength: [1, '成員名稱至少需要 1 個字元'],
        maxlength: [50, '成員名稱不可超過 50 個字元']
    },
    roles: {
        type: [String],
        default: [],
        validate: {
            validator: function(v) {
                return v.every(role => typeof role === 'string' && role.length <= 30);
            },
            message: '職位名稱不可超過 30 個字元'
        }
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

// 建立索引
memberSchema.index({ name: 1 });
memberSchema.index({ role: 1 });

module.exports = mongoose.model('Member', memberSchema);
