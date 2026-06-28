/**
 * 轉義正則表達式特殊字符，防止 ReDoS 攻擊
 * @param {string} str - 要轉義的字串
 * @returns {string} 轉義後的字串
 */
function escapeRegex(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * 驗證 MongoDB ObjectId 格式
 * @param {string} id - 要驗證的 ID
 * @returns {boolean} 是否為有效的 ObjectId
 */
function isValidObjectId(id) {
    return /^[0-9a-fA-F]{24}$/.test(id);
}

/**
 * 清理和驗證分頁參數
 * @param {object} query - 請求的 query 參數
 * @param {object} defaults - 預設值
 * @returns {object} 清理後的分頁參數
 */
function sanitizePagination(query, defaults = { page: 1, limit: 50, maxLimit: 1000 }) {
    let page = parseInt(query.page) || defaults.page;
    let limit = parseInt(query.limit) || defaults.limit;

    // 確保在合理範圍內
    page = Math.max(1, page);
    limit = Math.min(Math.max(1, limit), defaults.maxLimit);

    return { page, limit, skip: (page - 1) * limit };
}

module.exports = {
    escapeRegex,
    isValidObjectId,
    sanitizePagination
};
