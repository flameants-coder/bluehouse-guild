const mongoose = require('mongoose');

// 戰備庫庫存
// 每一筆代表一個「物品基礎名 + 有效階級」的庫存項目
// 有效階級 = 基礎階級(老手T4/專家T5/大師T6/宗師T7/禪師T8) + 附魔等級
// 品質不列入區分；無階級前綴的物品 tier 為 null（歸類為「其他」）
const equipmentSchema = new mongoose.Schema({
    name: {
        type: String,
        required: [true, '裝備名稱為必填'],
        trim: true,
        minlength: [1, '裝備名稱至少需要 1 個字元'],
        maxlength: [60, '裝備名稱不可超過 60 個字元']
    },
    tier: {
        type: Number,
        default: null,
        min: [1, '階級不可小於 1'],
        max: [20, '階級不可大於 20']
    },
    quantity: {
        type: Number,
        default: 0
    },
    minStock: {
        type: Number,
        default: 0,
        min: [0, '所需庫存量不可為負數']
    },
    note: {
        type: String,
        trim: true,
        default: '',
        maxlength: [200, '備註不可超過 200 個字元']
    },
    // 手動覆寫部位分類；空字串代表依名稱自動判斷
    category: {
        type: String,
        trim: true,
        default: '',
        enum: ['', '頭', '身體', '鞋子', '武器', '副手', '披風', '其他']
    }
}, {
    timestamps: true
});

// 以「名稱 + 有效階級」作為唯一鍵
equipmentSchema.index({ name: 1, tier: 1 }, { unique: true });

module.exports = mongoose.model('Equipment', equipmentSchema);
