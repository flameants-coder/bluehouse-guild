# Blue House 公會管理系統 - 技術文檔

## 專案概述

Blue House 公會管理系統是一個用於管理遊戲公會的網頁應用程式，包含成員管理、能量記錄、力量點統計和抽獎系統。

## 架構總覽

```
公會管理/
├── index.html          # 前端單頁應用 (SPA)
├── CLAUDE.md           # 技術文檔
├── .gitignore          # Git 忽略規則
└── server/             # 後端 API 服務
    ├── index.js        # Express 主程式
    ├── package.json    # Node.js 依賴
    ├── .env            # 環境變數 (不上傳)
    ├── .env.example    # 環境變數範例
    ├── config/
    │   └── db.js       # MongoDB 連接設定
    ├── middleware/
    │   └── auth.js     # JWT 認證中間件
    ├── models/
    │   ├── Member.js       # 成員資料模型
    │   ├── EnergyRecord.js # 能量記錄模型
    │   ├── Season.js       # 賽季資料模型
    │   └── User.js         # 使用者模型 (認證)
    ├── routes/
    │   ├── auth.js     # 認證 API 路由
    │   ├── members.js  # 成員 API 路由
    │   ├── energy.js   # 能量 API 路由
    │   └── seasons.js  # 賽季 API 路由
    └── scripts/
        └── createAdmin.js  # 建立管理員帳號腳本
```

## 技術堆疊

### 前端
- **HTML/CSS/JavaScript** - 單頁應用
- **localStorage** - 本地資料備份
- **Fetch API** - 與後端 API 通訊

### 後端
- **Node.js + Express.js** - API 伺服器
- **Mongoose** - MongoDB ODM
- **JWT (jsonwebtoken)** - 身份認證
- **bcryptjs** - 密碼加密
- **CORS** - 跨域請求支援
- **dotenv** - 環境變數管理

### 資料庫
- **MongoDB Atlas** - 雲端 NoSQL 資料庫 (免費 M0 叢集)

### 部署
- **前端**: GitHub Pages (https://flameants-coder.github.io/bluehouse-guild/)
- **後端**: Render.com (https://bluehouse-guild-api.onrender.com)

## API 端點

### 基礎 URL
```
https://bluehouse-guild-api.onrender.com/api
```

### 認證 `/api/auth`
| 方法 | 端點 | 說明 | 權限 |
|------|------|------|------|
| POST | `/login` | 登入取得 Token | 公開 |
| GET | `/me` | 驗證 Token 取得用戶資訊 | 需認證 |
| POST | `/change-password` | 修改密碼 | 需認證 |

### 成員管理 `/api/members`
| 方法 | 端點 | 說明 | 權限 |
|------|------|------|------|
| GET | `/` | 取得所有成員 | 公開 |
| POST | `/` | 新增成員 | 管理員 |
| POST | `/bulk` | 批次更新成員 (覆蓋全部) | 管理員 |
| PUT | `/:id` | 更新單一成員 | 管理員 |
| DELETE | `/:id` | 刪除成員 | 管理員 |

### 能量記錄 `/api/energy`
| 方法 | 端點 | 說明 | 權限 |
|------|------|------|------|
| GET | `/` | 取得所有記錄 | 公開 |
| GET | `/stats` | 取得統計數據 | 公開 |
| POST | `/` | 新增記錄 | 管理員 |
| POST | `/bulk` | 批次新增記錄 | 管理員 |
| DELETE | `/:id` | 刪除記錄 | 管理員 |
| DELETE | `/` | 清除所有記錄 | 管理員 |

### 賽季管理 `/api/seasons`
| 方法 | 端點 | 說明 | 權限 |
|------|------|------|------|
| GET | `/` | 取得所有賽季 | 公開 |
| GET | `/:id` | 取得單一賽季 | 公開 |
| POST | `/` | 新增賽季 | 管理員 |
| DELETE | `/:id` | 刪除賽季 | 管理員 |
| PUT | `/:id/scores/:activity` | 更新力量點分數 | 管理員 |
| DELETE | `/:id/scores` | 清除力量點數據 | 管理員 |
| PUT | `/:id/lottery/prizes` | 更新獎品列表 | 管理員 |
| POST | `/:id/lottery/draw` | 記錄抽獎結果 | 管理員 |
| DELETE | `/:id/lottery/history` | 清除抽獎記錄 | 管理員 |

## 資料模型

### Member (成員)
```javascript
{
  name: String,        // 成員名稱
  energy: Number,      // 能量值 (預設 0)
  tickets: Number,     // 抽獎券數量 (預設 0)
  createdAt: Date
}
```

### EnergyRecord (能量記錄)
```javascript
{
  name: String,        // 成員名稱
  energy: Number,      // 能量變動值
  type: String,        // 類型: 'add' | 'deduct'
  reason: String,      // 原因 (選填)
  createdAt: Date
}
```

### Season (賽季)
```javascript
{
  name: String,        // 賽季名稱
  scores: {
    hideoutCore: [],       // 藏身處核心
    crystalSpider: [],     // 水晶蜘蛛
    hellGate: [],          // 地獄之門
    bottomlessAbyss: []    // 無底深淵
  },
  lottery: {
    prizes: [],            // 獎品列表
    history: [],           // 中獎記錄
    usedTickets: Map       // 已使用抽獎券
  },
  createdAt: Date
}
```

### User (使用者)
```javascript
{
  username: String,    // 使用者名稱 (唯一, 小寫)
  password: String,    // 密碼 (bcrypt 加密)
  role: String,        // 角色: 'admin' | 'guest'
  lastLogin: Date,     // 最後登入時間
  createdAt: Date
}
```

## 部署指南

### 後端部署 (Render)

1. 前往 [Render Dashboard](https://dashboard.render.com/)
2. 建立新的 Web Service
3. 連接 GitHub 儲存庫
4. 設定：
   - **Root Directory**: `server`
   - **Build Command**: `npm install`
   - **Start Command**: `npm start`
5. 新增環境變數：
   - `MONGODB_URI`: MongoDB 連接字串
   - `PORT`: 3000
   - `JWT_SECRET`: JWT 密鑰 (隨機長字串，至少 32 字元)

### 建立管理員帳號

部署後端後，需要建立管理員帳號才能使用管理功能：

```bash
# 透過 Render Shell 執行
cd server
node scripts/createAdmin.js admin your-secure-password
```

或在本地執行（需先設定 `.env`）：
```bash
cd server
npm run create-admin admin your-secure-password
```

### 前端部署 (GitHub Pages)

1. 前往 GitHub 儲存庫設定
2. Pages → Source → Deploy from a branch
3. 選擇 `main` 分支，根目錄 `/`
4. 儲存後等待部署完成

### MongoDB Atlas 設定

1. 登入 [MongoDB Atlas](https://cloud.mongodb.com/)
2. 確保 Network Access 允許 `0.0.0.0/0` (Render 需要)
3. 連接字串格式：
```
mongodb+srv://<username>:<password>@cluster0.oxeluaa.mongodb.net/bluehouse-guild?retryWrites=true&w=majority
```

## 常見維護任務

### 更新前端程式碼
```bash
cd C:\Users\flame\Desktop\公會管理
git add .
git commit -m "更新說明"
git push
```
GitHub Pages 會自動部署。

### 更新後端程式碼
```bash
cd C:\Users\flame\Desktop\公會管理
git add .
git commit -m "更新說明"
git push
```
Render 會自動從 GitHub 拉取並重新部署。

### 本地開發後端
```bash
cd server
npm install
npm run dev
```
伺服器會在 http://localhost:3000 運行。

### 檢視 API 日誌
前往 Render Dashboard → 選擇服務 → Logs

### 檢視資料庫
前往 MongoDB Atlas → Browse Collections

## 認證系統

### 角色說明
- **管理員 (admin)**: 可執行所有操作（匯入資料、刪除、修改等）
- **訪客 (guest)**: 只能檢視資料（所有頁面可見，但無法執行寫入操作）

### 前端認證流程
1. 訪問網站時顯示登入彈窗
2. 可選擇登入管理員帳號或使用訪客模式
3. 登入後 Token 存在 localStorage，有效期 7 天
4. Token 過期後需重新登入

### 後端認證機制
- 使用 JWT (JSON Web Token) 進行身份驗證
- 密碼使用 bcrypt 加密儲存
- 所有寫入 API (POST/PUT/DELETE) 需要管理員權限
- 讀取 API (GET) 公開存取

## 重要設定檔位置

| 檔案 | 用途 |
|------|------|
| `server/.env` | 環境變數 (含資料庫密碼和 JWT 密鑰，勿上傳) |
| `index.html` | 前端 SPA，含認證邏輯 |
| `server/middleware/auth.js` | JWT 驗證中間件 |
| `server/config/db.js` | 資料庫連接邏輯 |

## 故障排除

### API 無回應
1. 檢查 Render 服務狀態
2. 免費方案會在閒置後休眠，首次請求需等待約 30 秒喚醒

### 資料庫連接失敗
1. 檢查 MongoDB Atlas 的 Network Access 是否允許 `0.0.0.0/0`
2. 確認 `.env` 中的連接字串正確

### 前端無法取得資料
1. 檢查瀏覽器 Console 是否有 CORS 錯誤
2. 確認 `API_BASE_URL` 設定正確
3. 資料會從 localStorage 讀取作為備份

## GitHub 儲存庫

- **儲存庫**: https://github.com/flameants-coder/bluehouse-guild
- **GitHub Pages**: https://flameants-coder.github.io/bluehouse-guild/

## 聯絡資訊

如需新增協作者，請前往 GitHub 儲存庫：
Settings → Collaborators → Add people
