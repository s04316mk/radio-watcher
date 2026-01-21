import requests
from bs4 import BeautifulSoup
import pandas as pd
import pandas_gbq
from google.oauth2 import service_account
import os
import json
import time
import random
import datetime

# ==========================================
# 設定エリア
# ==========================================
PROJECT_ID = "radio-watcher-v2"
TABLE_ID = "radio_data.plays"

STATIONS = [
    "HBC", "STV", "AIR-G", "NORTHWAVE",
    "RAB", "IBC", "TBC", "DATEFM",
    "TBS", "QRR", "LFR", "INT", "FMJ", "FMT",
    "BAYFM78", "NACK5", "YFM",
    "CBC", "TOKAI", "ZIP-FM", "FMAICHI",
    "ABC", "MBS", "OBC", "CCL", "802", "FMO",
    "RKB", "KBC", "LOVEFM", "CROSSFM",
    "RBC", "ROK", "FM_OKINAWA"
]

def get_station_data(station_id):
    url = f"https://radiko.jp/v3/feed/pc/noa/{station_id}.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        
        # ★【診断ポイント】ステータスコードをチェック
        if res.status_code != 200:
            print(f"❌ {station_id} -> Error: {res.status_code}")
            return []
            
        soup = BeautifulSoup(res.content, "xml")
        data_list = []
        items = soup.find_all("item")
        
        # ★【診断ポイント】曲が見つからなかった場合
        if len(items) == 0:
            print(f"⚠️ {station_id} -> Access OK but 0 songs found. (Response len: {len(res.text)})")
            # 中身が「地域外エラー」などのHTMLか確認するため、少しだけ表示
            # print(f"   Content snippet: {res.text[:100]}...") 
        
        for item in items:
            title = item.find("title").text if item.find("title") else ""
            artist = item.find("artist").text if item.find("artist") else ""
            stamp_str = item.get("stamp")
            
            if title and artist and stamp_str:
                dt = datetime.datetime.strptime(stamp_str, "%Y%m%d%H%M%S")
                data_list.append({
                    "timestamp": dt,
                    "station_id": station_id,
                    "program_name": "Unknown",
                    "dj_name": "",
                    "artist": artist,
                    "title": title
                })
        
        return data_list

    except Exception as e:
        # ★【診断ポイント】エラー内容を隠さずに表示
        print(f"❌ {station_id} -> Exception: {e}")
        return []

def main():
    all_data = []
    print("Start crawling (Diagnosis Mode)...")
    
    for station in STATIONS:
        station_data = get_station_data(station)
        if station_data:
            print(f"✅ {station} -> Found {len(station_data)} songs")
            all_data.extend(station_data)
        
        time.sleep(random.uniform(0.5, 1.0))

    if all_data:
        df = pd.DataFrame(all_data)
        key_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        credentials = service_account.Credentials.from_service_account_info(key_info)
        print(f"Saving {len(df)} records to BigQuery...")
        pandas_gbq.to_gbq(df, TABLE_ID, project_id=PROJECT_ID, if_exists="append", credentials=credentials)
        print("Done!")
    else:
        print("No data found. Check the logs above for ❌ or ⚠️ marks.")

if __name__ == "__main__":
    main()
