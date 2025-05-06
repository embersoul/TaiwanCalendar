import requests
import csv
import json
from io import StringIO

# 定義 API 網址和 POST 參數
url = "https://data.gov.tw/api/front/dataset/search-export"
payload = {
    "format": "json",
    "bool": [
        {"fulltext": {"value": "中華民國政府行政機關辦公日曆表"}},
        {"nid": {"value": "14718"}}
    ],
    "filter": [],
    "sort": "_score_desc"
}

# 發送 POST 請求
response = requests.post(url, json=payload)
if response.status_code != 200:
    raise Exception(f"API request failed with status {response.status_code}, response content: {response.text}")

# 解析 API 回應
data = response.json()
if not data:
    raise Exception("No data found in API response")

# 提取資料集識別碼為 14718 的資料
dataset = next((item for item in data if item["資料集識別碼"] == 14718), None)
if not dataset:
    raise Exception("Dataset with nid 14718 not found")

# 提取資料下載網址並以分號分隔
download_urls = dataset.get("資料下載網址", "")
if not download_urls:
    raise Exception("No download URLs found")

# 過濾掉包含 "google" 的網址，選擇最後一筆（最新的）CSV 檔案
urls = [url.strip() for url in download_urls.split(";") if "google" not in url.lower()]
if not urls:
    raise Exception("No valid URLs found after filtering")
latest_url = urls[-1]  # 選擇最後一筆（最新）

# 下載 CSV 檔案
csv_response = requests.get(latest_url)
if csv_response.status_code != 200:
    raise Exception(f"Failed to download CSV from {latest_url}")

# 解析 CSV 內容（使用 UTF-8 編碼）
csv_content = csv_response.text
print("CSV first 5 lines:", csv_content.splitlines()[:5])  # 打印前 5 行以確認格式
csv_file = StringIO(csv_content)

# 使用 csv.DictReader 並指定欄位名稱，假設第一行為標題行
csv_reader = csv.DictReader(csv_file, fieldnames=["西元日期", "星期", "是否放假", "備註"])
next(csv_reader)  # 跳過標題行

# 轉換為 JSON 格式
calendar_data = []
for row in csv_reader:
    try:
        calendar_data.append({
            "date": row["西元日期"],
            "day_of_week": row["星期"],
            "is_holiday": int(row["是否放假"]),
            "note": row["備註"]
        })
    except ValueError as e:
        print(f"Skipping row due to error: {row}, error: {e}")
        continue

# 將結果轉為 JSON 字串
json_output = json.dumps(calendar_data, ensure_ascii=False, indent=2)

# 輸出 JSON 結果
print(json_output)

# 將 JSON 儲存為檔案（可選）
with open("calendar.json", "w", encoding="utf-8") as f:
    f.write(json_output)