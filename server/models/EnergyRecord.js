const mongoose = require('mongoose');

const energyRecordSchema = new mongoose.Schema({
    memberName: {
        type: String,
        required: [true, '成員名稱為必填'],
        trim: true,
        maxlength: [50, '成員名稱不可超過 50 個字元']
    },
    action: {
        type: String,
        enum: {
            values: ['收入', '支出'],
            message: '操作類型必須是「收入」或「支出」'
        },
        required: [true, '操作類型為必填']
    },
    quantity: {
        type: Number,
        required: [true, '數量為必填'],
        validate: {
            validator: function(v) {
                return Math.abs(v) <= 99999999;
            },
            message: '數量不可超過 99,999,999'
        }
    },
    datetime: {
        type: Date,
        required: [true, '日期時間為必填'],
        validate: {
            validator: function(v) {
                // 允許未來 1 天內的時間（考慮時區差異）
                const tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                return v <= tomorrow;
            },
            message: '日期不能是未來時間'
        }
    },
    note: {
        type: String,
        default: '',
        maxlength: [200, '備註不可超過 200 個字元']
    }
}, {
    timestamps: true
});

// Pre-save hook: 強制 action 與 quantity 符號一致性
energyRecordSchema.pre('save', function(next) {
    // 收入必須為正數，支出必須為負數
    if (this.action === '收入' && this.quantity < 0) {
        this.quantity = Math.abs(this.quantity);
    } else if (this.action === '支出' && this.quantity > 0) {
        this.quantity = -Math.abs(this.quantity);
    }
    next();
});

// Pre-insertMany hook: 批量插入時也強制一致性
energyRecordSchema.pre('insertMany', function(next, docs) {
    docs.forEach(doc => {
        if (doc.action === '收入' && doc.quantity < 0) {
            doc.quantity = Math.abs(doc.quantity);
        } else if (doc.action === '支出' && doc.quantity > 0) {
            doc.quantity = -Math.abs(doc.quantity);
        }
    });
    next();
});

// 建立索引以優化查詢
energyRecordSchema.index({ memberName: 1 });
energyRecordSchema.index({ datetime: -1 });
energyRecordSchema.index({ action: 1 });
// 複合索引：常用的查詢組合
energyRecordSchema.index({ memberName: 1, datetime: -1 });
energyRecordSchema.index({ action: 1, datetime: -1 });
// 唯一複合索引：防止相同時間戳記的重複記錄
energyRecordSchema.index(
    { memberName: 1, datetime: 1, quantity: 1 },
    { unique: true, background: true }
);

module.exports = mongoose.model('EnergyRecord', energyRecordSchema);
