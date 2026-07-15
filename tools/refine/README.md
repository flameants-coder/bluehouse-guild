# Albion 精煉計算器（產生器）

> **這裡是唯一的程式源頭**（Blue House 公會 repo `tools/refine/`）。要改計算邏輯、欄位、設定就改這裡，不要在別的地方另存一份。

從 [Albion Online Data Project](https://www.albion-online-data.com/) 抓市場價，算出**各階精煉利潤**，
產生自包含網頁 `refine_profit.html`，供公會網站的「精煉計算器」分頁使用。

## 在公會網站的運作方式
- 產生的 `refine_profit.html` 會被複製到 **repo 根目錄的 `refine.html`**，由 GitHub Pages 提供、`index.html` 用 iframe 載入。
- **自動更新**：`.github/workflows/refine-calculator.yml` 每天自動執行本程式並更新 `refine.html`（也可到 Actions 頁手動 Run workflow）。
- 手動更新：`cd tools/refine && python refine_bot.py`，再把 `refine_profit.html` 複製成根目錄 `refine.html` 並 commit。
- 使用者說明頁是根目錄的靜態檔 `使用說明.html`（不由本程式產生，直接編輯即可）。

---


## 安裝
```
pip install requests
```

## 執行
```
python refine_bot.py
```
會在終端機印出表格，並產生 `refine_profit.csv`（用 Excel 直接開，不亂碼）。

## 設定（改 `config.py` 就好）

| 項目 | 說明 |
|------|------|
| `SERVER` | `east` 亞服 / `west` 美服 / `europe` 歐服 |
| `CITIES` | 要比較的城市清單 |
| `RETURN_RATE` | 返還率四個加成：`base` 基礎18、`city_bonus` 特產城(資源40/裝備15/無0)、`focus` 專注(有59/無0)、`event` 活動加成 |
| `PREMIUM` | 有無會員 → 交易稅 4%/8%，自動推導各項手續費 |
| `BUY_PRICE` / `SELL_PRICE` | 買料 max_buy(掛收購單+2.5%)/min_sell(吃賣單) ；賣品 min_sell(掛賣單6.5%)/max_buy(賣收購單4/8%) |
| `STATION_FEE` | 主城店鋪費（每 100 營養），店主自訂 |
| `SHOW_MARKET_VALUE` | 顯示「預估市值」欄（歷史成交均價，僅參考） |
| `LINES` / `ONLY_LINES` | 五條精煉線；`ONLY_LINES` 可只算其中幾條 |

### 交易成本（由 `PREMIUM` 自動推導）
| 動作 | 會員 | 無會員 |
|------|------|--------|
| 掛賣單賣成品 | 2.5%+4% = 6.5% | 10.5% |
| 賣給收購單(玩家) | 4% | 8% |
| 掛收購單買料 | 2.5% | 2.5% |
| 直接吃賣單買 | 0 | 0 |

### 價格基準：7 天成交均價（`PRICE_BASIS`）
- 買料與賣品**都用最近 7 天的成交量加權均價**，避開單一天價/地板假單造成的假利潤（例：T8 皮革曾因一筆 99,900 假掛單顯示 176%，改均價後回到務實的 ~48%）。
- `PRICE_BASIS = "current"` 可切回即時掛單價。
- **量少警示**（`LOW_VOLUME`，預設 300）：成品 7 天成交量低於門檻 → 標 `⚠量少` 並變洋紅，代表均價只由少量成交算出、參考性低。CSV 有「量少」欄。

### 城市選擇（`BUY_CITIES` / `SELL_CITIES`）
可分開指定買料城市與賣品城市（留 `None` = 都用 `CITIES`）。例：只在 Martlock 買、只在 Bridgewatch 賣。

### 網頁互動控制（即時重算，免重跑）
`refine_profit.html` 頂部可即時切換，全表利潤/成品賣價/成本/評級/排序/摘要卡立即重算：
- **買料城市 / 賣品城市** 下拉（全部 或 指定單一城）
- **灌專注(+59)** 開關、**活動加成 0/10/20%**

整套定價引擎（跨城取價、轉換、陣營之心、7日均價、現價回填、量少/偏離）都內嵌在網頁 JS，已用 Node 對 Python 逐列驗證一致（全城 115/115、指定城 104/104）。設定檔的 `BUY_CITIES`/`SELL_CITIES` 則作為初始值。

### 常見情境調整
- **沒灌專注**：`RETURN_RATE["focus"] = 0`（返還率變 0.367）
- **不在特產城精煉**：`RETURN_RATE["city_bonus"] = 0`
- **有返還率活動**：`RETURN_RATE["event"] = 活動加成率`

## 計算公式（對應你的表）
```
返還率 = 總加成 / (100 + 總加成)     # 總加成 = 基礎+特產+專注+活動
每原料單價 = min(原料價, 陣營之心價)  # 僅附魔且心較便宜時，取代其中 1 個原料
成本   = (下階成品價 + 每原料單價 + 原料價×(N-1)) × (1-返還率) × (1+買料手續費) + 0.1125×物品價值×(店鋪費/100)
利潤   = 成品賣價 × (1-賣品手續費) − 成本
```
- 精煉配方每階原料數 N = {T2:1, T3:2, T4:2, T5:3, T6:4, T7:5, T8:5}，外加 1 個下階成品。
- **附魔**（`ENCHANT_LEVELS`）：T{t}.{e} 成品 = T{t}.{e} 原料×N + **同附魔** T{t-1}.{e} 成品×1。物品價值每附魔級 ×2。
- **陣營之心**（`USE_FACTION_HEART`）：附魔精煉時，1 個原料可用 1 個陣營之心取代；原料比心貴才用（`.4` 不可用）。表格會標 `♥用心`。

### 轉換（Transmutation，`USE_TRANSMUTE`）
遊戲店鋪「轉換」可用**銀幣**把資源升級，機器人會自動比較「直接買附魔原料」vs 兩條轉換路，取最便宜當精煉成本（可遞迴）：
- **升附魔** `轉附`：T{t}.{e} ← T{t}.{e-1}（同階）+ 銀幣
- **升階** `轉階`：T{t}.{e} ← T{t-1}.{e}（同附魔）+ 銀幣

銀幣是**遊戲寫死的固定值**（店鋪費只影響 <1%，已驗證公式 `總額 = 固定值 + 0.1125×itemvalue×店鋪費/100`），全資源共用同一張表（`TRANSMUTE`）。**石材不能轉換**（`TRANSMUTE_EXCLUDE`）。來源欄會顯示如 `轉階[買Caer]`、`轉附[轉附[買Caer]]`。

### 陣營之心對照（已自動從 API 抓價）
| 資源 | 陣營之心 | 物品 ID | 最便宜城市 |
|------|---------|---------|-----------|
| 獸皮 HIDE | 野獸之心 Beastheart | `T1_FACTION_STEPPE_TOKEN_1` | Bridgewatch(黃) |
| 木頭 WOOD | 樹木之心 Treeheart | `T1_FACTION_FOREST_TOKEN_1` | Lymhurst(綠) |
| 礦石 ORE | 山脈之心 Mountainheart | `T1_FACTION_MOUNTAIN_TOKEN_1` | Fort Sterling(白) |
| 石頭 ROCK | 岩石之心 Rockheart | `T1_FACTION_HIGHLAND_TOKEN_1` | Martlock(藍) |
| 纖維 FIBER | 藤蔓之心 Vineheart | `T1_FACTION_SWAMP_TOKEN_1` | Thetford(紫) |

## 顏色標記（`USE_COLOR`）
終端機會依**利潤率**把每一列上色，一眼看出哪些階級值得做：

| 評級 | 利潤率 | 顏色 |
|------|--------|------|
| 賺爛 | ≥ 50% | 亮綠加粗 |
| 不錯 | ≥ 30% | 亮綠 |
| 普通 | ≥ 15% | 黃 |
| 微利 | ≥ 0% | 灰 |
| 虧損 | < 0% | 紅 |

門檻可在 `config.py` 的 `RATING_TIERS` 調整。CSV 也有「評級」欄，方便在 Excel 篩選排序。

## 注意事項
- **買點/賣點可能是不同城市**：表格會顯示各物品最便宜的購料城市與最高賣價城市。
  若兩者不同代表要跨城搬運；實務上通常在**特產城買料+精煉+就地賣**，可把 `CITIES` 縮到你的特產城。
- **資料新鮮度**：亞服部分冷門物品在 AODP 更新較慢；超過 `STALE_HOURS`(預設72h) 會標 `⚠過期`。
  想讓資料更即時，可安裝官方 [AODP Client](https://www.albion-online-data.com/) 邊玩邊上傳。
- 涵蓋**基礎 + 附魔 .1/.2/.3**（`.4` 未計）。缺市場資料的階級會自動略過。

## 下一步可以加的功能
- 定時自動抓（排程）+ 利潤達標時發 Discord/Email 通知
- 跨城套利：明確標出「A 城買料 → B 城賣成品」的最佳組合
- 鏈式精煉：自己精煉下階而非買市場價
- 其他資源的轉換表微調（目前全資源共用獸皮實測值，官方成本相同）
