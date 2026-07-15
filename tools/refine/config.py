# -*- coding: utf-8 -*-
"""
Albion 精煉利潤機器人 —— 設定檔
改這個檔就好，refine_bot.py 不用動。
公式來源：你的 Google Sheet「精煉成本計算機(皮革)」。
"""

# ── 伺服器 ──────────────────────────────────────────────
# west = 美服 / east = 亞服 / europe = 歐服
SERVER = "east"

# ── 城市設定 ──────────────────────────────────────────────
# 城市名（英文，照抄）：
#   Thetford（紫城）、Fort Sterling（白城）、Lymhurst（綠城）、
#   Bridgewatch（黃城）、Martlock（藍城）、Caerleon（紅城/中央）、Brecilien
#
# CITIES：預設要比較的城市清單（不指定買賣城市時就用這份）。
CITIES = [
    "Thetford",
    "Fort Sterling",
    "Lymhurst",
    "Bridgewatch",
    "Martlock",
    # "Caerleon",   # 地處中央、成品賣價偏高不切實際，暫不列入（要算再取消註解）
]

# 城市顏色（顯示在城市名後面，方便辨識）
CITY_COLOR = {
    "Thetford": "紫", "Fort Sterling": "白", "Lymhurst": "綠",
    "Bridgewatch": "黃", "Martlock": "藍", "Caerleon": "紅", "Brecilien": "青",
}

# ★ 選擇「在哪個城買料」與「在哪個城賣成品」★
#   - 留 None            → 用上面 CITIES 全部一起比（自動挑最便宜買、最貴賣的城）
#   - 填單一城市(字串)   → 只在那個城，例：BUY_CITIES = "Martlock"
#   - 填多個城市(清單)   → 只在這些城裡比，例：SELL_CITIES = ["Bridgewatch", "Martlock"]
#   常見用法：固定在某城精煉＝買賣同一城，例 BUY_CITIES="Martlock"、SELL_CITIES="Martlock"
BUY_CITIES = None
SELL_CITIES = None

# ── 返還率參數（對應你表 C1/L1/J1/E1）────────────────────
# 返還率 = 總加成 / (100 + 總加成)
RETURN_RATE = {
    "base": 18,        # 主城基礎產出率
    "city_bonus": 40,  # 特產城加成：資源加成=40 / 裝備加成=15 / 無=0
    "focus": 59,       # 專注加成：有灌=59 / 沒灌=0
    "event": 0,        # 活動加成(%)：有活動時填活動加成率
}

# ── 稅率與製作費（對應你表 E7/G7/E3）──────────────────────
# 交易成本：由「是否有會員」自動推導（依買/賣策略套用，見下方 BUY_PRICE / SELL_PRICE）
PREMIUM = True                        # 有會員→交易稅4%；無會員→8%
_SALES_TAX = 0.04 if PREMIUM else 0.08
_SETUP_FEE = 0.025                    # 掛單上架費（掛賣單/掛收購單才有）
# 買料：max_buy 掛收購單=2.5%上架費 / min_sell 直接吃賣單=0
BUY_FEE = {"max_buy": _SETUP_FEE, "min_sell": 0.0}
# 賣品：min_sell 掛賣單=2.5%+交易稅 / max_buy 賣給收購單(玩家)=只有交易稅
SELL_FEE = {"min_sell": _SETUP_FEE + _SALES_TAX, "max_buy": _SALES_TAX}
STATION_FEE = 444   # 主城店鋪稅率（店主設的每 100 營養費用）

# ── 精煉線（原料 → 成品）──────────────────────────────────
# key 是顯示名稱；raw / refined 是遊戲物品 ID 的字根
LINES = {
    "皮革 Leather": {"raw": "HIDE",  "refined": "LEATHER"},
    "金屬錠 Metal": {"raw": "ORE",   "refined": "METALBAR"},
    "布 Cloth":     {"raw": "FIBER", "refined": "CLOTH"},
    "木板 Plank":   {"raw": "WOOD",  "refined": "PLANKS"},
    "石材 Stone":   {"raw": "ROCK",  "refined": "STONEBLOCK"},
}

# 只想算某幾條線？把不要的註解掉，或改這個清單（空 = 全部）
ONLY_LINES = []  # 例：["皮革 Leather", "金屬錠 Metal"]

# ── 精煉配方（每階原料數 + 1 個下階成品）──────────────────
TIERS = [2, 3, 4, 5, 6, 7, 8]
RAW_PER_TIER = {2: 1, 3: 2, 4: 2, 5: 3, 6: 4, 7: 5, 8: 5}

# 物品價值（算店鋪費用用，對應你表 L 欄，基礎品質；附魔每級 ×2）
ITEM_VALUE = {2: 4, 3: 8, 4: 16, 5: 32, 6: 64, 7: 128, 8: 256}

# ── 附魔等級 ─────────────────────────────────────────────
# 0=基礎, 1=.1, 2=.2, 3=.3, 4=.4（極限）
# 精煉附魔配方（遊戲實際）：T{t}.{e} 成品 = T{t}.{e} 原料×N + T{t-1}.{e} 成品×1
ENCHANT_LEVELS = [0, 1, 2, 3, 4]

# ── 陣營之心（Faction Heart）替代原料 ─────────────────────
# 附魔精煉時，可用 1 個陣營之心取代 1 個原料；若原料比心貴就自動用心。
# .4 極限資源不能用陣營之心 → 只允許 .1~.3。
USE_FACTION_HEART = True
HEART_ENCHANT_MAX = 3   # 陣營之心可用的最高附魔級（.4 不可用）
FACTION_HEARTS = {
    "HIDE":  "T1_FACTION_STEPPE_TOKEN_1",    # 野獸之心（草原/黃城 Bridgewatch）
    "WOOD":  "T1_FACTION_FOREST_TOKEN_1",    # 樹木之心（森林 Lymhurst）
    "ORE":   "T1_FACTION_MOUNTAIN_TOKEN_1",  # 山脈之心（山脈 Fort Sterling）
    "ROCK":  "T1_FACTION_HIGHLAND_TOKEN_1",  # 岩石之心（高地 Martlock）
    "FIBER": "T1_FACTION_SWAMP_TOKEN_1",     # 藤蔓之心（沼澤 Thetford）
}
# 各資源對應的陣營之心名稱（顯示在備註）
FACTION_HEART_NAME = {
    "HIDE": "野獸之心", "WOOD": "樹木之心", "ORE": "山脈之心",
    "ROCK": "岩石之心", "FIBER": "藤蔓之心",
}

# ── 轉換（Transmutation）：用銀幣把資源升級 ────────────────
# 遊戲店鋪「轉換」有兩條路，機器人會自動比較「直接買」vs 兩條轉換路，取最便宜當精煉原料成本：
#   enchant 升附魔：目標 T{t}.{e} ← T{t}.{e-1}（同階）+ 銀幣
#   tier    升階  ：目標 T{t}.{e} ← T{t-1}.{e}（同附魔）+ 銀幣
# 銀幣≈遊戲寫死固定值（店鋪費只影響 <1%），直接填遊戲「轉換」介面看到的數字。
# 以下為獸皮 HIDE 實測（店鋪費 998；k 為遊戲四捨五入值）。其他資源請自行補。
USE_TRANSMUTE = True
TRANSMUTE_EXCLUDE = ["ROCK"]   # 石材 Stone 不能轉換（遊戲限制）
# 全資源共用一份（獸皮/礦石/木/纖維 的轉換成本一樣，因為 item value 相同）
TRANSMUTE = {
    "enchant": {   # T{t}.{e} ← T{t}.{e-1}（同階升附魔）
        (4, 1): 1744, (4, 2): 3493, (4, 3): 6991, (4, 4): 27835,
        (5, 1): 1816, (5, 2): 3630, (5, 3): 7260, (5, 4): 28946,
        (6, 1): 2903, (6, 2): 5806, (6, 3): 19113, (6, 4): 76308,
        (7, 1): 5799, (7, 2): 18233, (7, 3): 60094, (7, 4): 240000,
        (8, 1): 17367, (8, 2): 54641, (8, 3): 180000, (8, 4): 900000,
    },
    "tier": {      # T{t}.{e} ← T{t-1}.{e}（同附魔升階）
        (5, 0): 907, (5, 1): 2320, (5, 2): 4640, (5, 3): 9280, (5, 4): 37024,
        (6, 0): 1451, (6, 1): 3480, (6, 2): 6960, (6, 3): 22921, (6, 4): 91541,
        (7, 0): 2899, (7, 1): 5568, (7, 2): 17506, (7, 3): 57695, (7, 4): 231000,
        (8, 0): 5799, (8, 1): 16675, (8, 2): 52460, (8, 3): 173000, (8, 4): 864000,
    },
}

# ── 抓價策略（會連動上面的交易成本）──────────────────────
# 買原料：min_sell = 吃最低賣單(你當下真的買得到的價, 推薦) / max_buy = 用最高收購單價
#   ⚠ max_buy 會抓到「別人想收的低價單」(如某冷門品只有人掛收600)，不是你買得到的價，
#     會嚴重低估成本、產生假利潤。除非你真的都靠掛收購單慢慢等，否則用 min_sell。
BUY_PRICE = "min_sell"
# 賣成品：min_sell = 掛賣單(6.5%) / max_buy = 賣給玩家收購單(較快, 4~8%)
SELL_PRICE = "min_sell"

# 買料與賣品的價格基準：avg7 = 用 7 天市場成交均價(買賣皆用, 避開天價/地板假單, 推薦)
#              current = 買用最低賣單、賣用最高賣單(即時但易受異常掛單影響)
PRICE_BASIS = "avg7"
# 7 天成交量低於此值 → 標「量少」，代表均價只由少量成交算出、參考性低
LOW_VOLUME = 300
# 7 天中位均價 與 當下掛單 差超過此比例 → 標「偏離現價」提示（例 0.35 = 35%）
PRICE_DEVIATION = 0.35

# 價格超過幾小時就標記為過期（亞服部分冷門物品資料較少）
STALE_HOURS = 72

# 顯示「預估市值」欄（成品歷史成交均價，僅參考、不影響利潤計算）
SHOW_MARKET_VALUE = True
# 假單警示：採用的賣價 > 預估市值 × 此倍數 → 標記 ⚠假單（該列變洋紅提醒）
FAKE_ORDER_RATIO = 1.5

# 輸出 CSV 檔名（放這個資料夾）
CSV_OUT = "refine_profit.csv"

# 輸出互動式網頁報表（可排序/篩選/顏色標記），用瀏覽器開
MAKE_HTML = True
HTML_OUT = "refine_profit.html"

# ── 顏色標記（依利潤率分級）──────────────────────────────
USE_COLOR = True
# 利潤率門檻（由高到低）：>=門檻 → 該顏色/評級；低於最後一個且<0 → 虧損(紅)
RATING_TIERS = [
    (0.50, "賺爛", "\033[1;92m"),  # 亮綠加粗
    (0.30, "不錯", "\033[92m"),    # 亮綠
    (0.15, "普通", "\033[93m"),    # 黃
    (0.00, "微利", "\033[90m"),    # 灰
]
