# TaiwanCalendar
臺灣行事曆

2025.6.26 更新114年行事曆json、新增115年行事曆json

提供臺灣政府行政機關辦公日曆 API，部署方式以 Vercel 為主；本機也可直接用 Flask 啟動 API。

## 專案結構

- `api/GetTaiwanCalendar.py`：Flask API 入口。
- `public/index.html`：靜態首頁。
- `112yearCalendar.json` 到 `115yearCalendar.json`：已內建的年度日曆資料。
- `calendar_urls.json`：遠端資料來源網址快取。
- `vercel.json`：Vercel 路由與 Python Runtime 設定。

## 環境需求

- Python 3.12 以上
- pip
- 選用：Vercel CLI（若要在本機模擬完整 Vercel 路由）

## 安裝

```bash
pip install -r requirements.txt
```

## 本機執行

### 方式一：直接啟動 Flask API

先啟用虛擬環境，或直接使用 `.venv` 內的 Python。

PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python api/GetTaiwanCalendar.py
```

如果不想啟用虛擬環境，也可以直接執行：

```bash
.\.venv\Scripts\python.exe api/GetTaiwanCalendar.py
```

預設會啟動在 `http://127.0.0.1:5000`。

可直接測試：

```bash
curl http://127.0.0.1:5000/api/taiwan-calendar
curl http://127.0.0.1:5000/api/taiwan-calendar/114
```

說明：

- `/api/taiwan-calendar`：回傳當前年份對應的民國年資料。
- `/api/taiwan-calendar/<year>`：回傳指定民國年的資料，例如 `114`、`115`。
- 本機模式會優先讀取專案根目錄既有的 `XXXyearCalendar.json`；若本地沒有對應年份，才會往外抓政府資料並產生新的 JSON 檔。

### 方式二：用 Vercel CLI 模擬完整站點

先安裝 CLI：

```bash
npm install -g vercel
```

然後在專案根目錄執行：

```bash
vercel dev
```

這種方式會套用 `vercel.json`，可同時測到：

- `/` 對應 `public/index.html`
- `/api/taiwan-calendar`
- `/api/taiwan-calendar/<year>`

## API 回傳格式

每筆資料格式如下：

```json
{
	"date": "20250101",
	"day_of_week": "三",
	"is_holiday": 2,
	"note": "開國紀念日"
}
```

欄位說明：

- `date`：西元日期，格式為 `YYYYMMDD`
- `day_of_week`：星期
- `is_holiday`：是否放假
- `note`：備註

## 部署到 Vercel

專案已包含 `vercel.json`，可直接部署：

```bash
vercel
```

正式發佈：

```bash
vercel --prod
```

目前設定：

- Python Runtime 使用 `@vercel/python`
- 入口檔案是 `api/GetTaiwanCalendar.py`
- 首頁路由 `/` 指向 `public/index.html`
- API 路由 `/api/taiwan-calendar(/(.*))?` 指向 Flask 應用程式

## 注意事項

- 本機如果已存在對應年份的 JSON，API 會直接讀本地檔，不需要連外。
- 若要抓取新年份資料，執行環境需要可以正常連線到政府資料來源。
- 若遇到遠端 SSL 憑證驗證問題，本機仍可先使用專案內建的年度 JSON 提供既有年份資料。
