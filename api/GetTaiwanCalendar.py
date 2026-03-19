import requests
import csv
import json
import re
import os
from io import StringIO
from flask import Flask, Response
from urllib.parse import unquote
from datetime import datetime

app = Flask(__name__)

# 自訂 JSON 編碼器，禁用 ASCII 轉義
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

# 設置 Flask JSON 編碼
app.json_encoder = CustomJSONEncoder
app.config['JSON_AS_ASCII'] = False

# 記憶體快取：日曆資料和網址列表
calendar_cache = {}
url_cache = {}

def load_url_cache():
    """從本地檔案載入網址列表，或返回記憶體快取"""
    if not os.getenv("VERCEL") and os.path.exists("calendar_urls.json"):
        try:
            with open("calendar_urls.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading calendar_urls.json: {e}")
    return url_cache

def save_url_cache(url_year_pairs):
    """儲存網址列表到本地檔案或記憶體快取"""
    url_dict = {year: url for url, year in url_year_pairs}
    if not os.getenv("VERCEL"):
        try:
            with open("calendar_urls.json", "w", encoding="utf-8") as f:
                json.dump(url_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing calendar_urls.json: {e}")
    url_cache.update(url_dict)

def extract_year_from_url(url):
    """從檔案名稱提取年份（例如 '114年' -> '114'）"""
    try:
        name = unquote(url.split("name=")[-1])
        match = re.search(r'(\d{3,4})年', name)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None

def fetch_calendar_data(year=None):
    """獲取日曆資料，若指定年份則返回該年份，否則使用當前年份"""
    # 先決定目標年份，避免本地模式在未帶年份時跳過現有 JSON 檔。
    if not year:
        current_year = datetime.now().year
        year = str(current_year - 1911)  # 例如 2025 - 1911 = 114

    # 本地：檢查 JSON 檔案
    if year and not os.getenv("VERCEL"):
        json_file = f"{year}yearCalendar.json"
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading {json_file}: {e}")

    # Vercel：檢查日曆快取
    if year and year in calendar_cache:
        return calendar_cache[year]

    # 載入網址列表
    url_dict = load_url_cache()

    # 如果年份在網址列表中，直接使用
    if year in url_dict:
        target_url = url_dict[year]
    else:
        # 呼叫 API 更新網址列表
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

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            return {"error": f"API request failed with status {response.status_code}, response content: {response.text}"}, 500

        data = response.json()
        if not data:
            return {"error": "No data found in API response"}, 404

        dataset = next((item for item in data if item["資料集識別碼"] == 14718), None)
        if not dataset:
            return {"error": "Dataset with nid 14718 not found"}, 404

        download_urls = dataset.get("資料下載網址", "")
        if not download_urls:
            return {"error": "No download URLs found"}, 404

        # 分隔並過濾網址
        urls = download_urls.split(";")
        url_year_pairs = []
        for url in urls:
            url = url.strip()
            if "google" in url.lower():
                continue
            year_from_url = extract_year_from_url(url)
            if year_from_url:
                url_year_pairs.append((url, year_from_url))

        if not url_year_pairs:
            return {"error": "No valid URLs found after filtering"}, 404

        # 儲存網址列表
        save_url_cache(url_year_pairs)
        url_dict = {year: url for url, year in url_year_pairs}

        # 檢查目標年份
        target_url = url_dict.get(year)
        if not target_url:
            return {"error": f"No calendar found for year {year}"}, 404

    # 檢查日曆快取
    if year in calendar_cache:
        return calendar_cache[year]

    # 下載 CSV
    csv_response = requests.get(target_url)
    if csv_response.status_code != 200:
        return {"error": f"Failed to download CSV from {target_url}"}, 500

    # 解析 CSV（UTF-8）
    csv_content = csv_response.text
    csv_file = StringIO(csv_content)
    csv_reader = csv.DictReader(csv_file, fieldnames=["西元日期", "星期", "是否放假", "備註"])
    next(csv_reader)  # 跳過標題行

    # 轉換為 JSON
    calendar_data = []
    for row in csv_reader:
        try:
            calendar_data.append({
                "date": row["西元日期"],
                "day_of_week": row["星期"],
                "is_holiday": int(row["是否放假"]),
                "note": row["備註"]
            })
        except ValueError:
            continue

    # 本地：儲存 JSON 檔案
    if not os.getenv("VERCEL"):
        json_file = f"{year}yearCalendar.json"
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(calendar_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing {json_file}: {e}")

    # Vercel：儲存到快取
    calendar_cache[year] = calendar_data

    return calendar_data

@app.route('/api/taiwan-calendar', methods=['GET'])
@app.route('/api/taiwan-calendar/<year>', methods=['GET'])
def get_calendar(year=None):
    result = fetch_calendar_data(year)
    if isinstance(result, tuple):
        return Response(
            json.dumps(result[0], ensure_ascii=False),
            status=result[1],
            mimetype='application/json'
        )
    return Response(
        json.dumps(result, ensure_ascii=False),
        mimetype='application/json'
    )

if __name__ == "__main__":
    app.run(debug=True)