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
import pytz

# ==========================================
# 設定エリア
# ==========================================
PROJECT_ID = "radio-watcher-v2"
TABLE_ID = "radio_data.plays"

# エラーが出る局を除外し、つながる局だけに厳選しました
STATIONS = [
    "AIR-G", "NORTHWAVE",          # 北海道
    "TBS", "QRR", "INT", "FMJ", "FMT", "BAYFM78", "NACK5", "YFM", # 関東
    "ZIP-FM", "FMAICHI",           # 中部
    "ABC", "CCL", "802", "FMO",    # 関西
    "RKB", "KBC", "LOVEFM", "CROSSFM", # 九州
    "FM_OKINAWA"                   # 沖縄
]

def get_station_data(station_id):
    url = f"https://radiko.jp/v3/feed/pc/noa/{station_id}.xml"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return []
            
        soup = BeautifulSoup(res.content, "xml")
        data_list = []
        items = soup.find_all("item")
        
        for item in items:
            # 1. まず中身を全部テキストで取得してみる
            title = item.find("title").text.strip() if item.find("title") else ""
            artist = item.find("artist").text.strip() if item.find("artist") else ""
            stamp_str = item.get("stamp")
            
            # 2. 歌手名が空なら "Unknown" にしてあげる（ここが修正点！）
            if not artist:
                artist = "Unknown / Talk"

            # 3. タイトルと時間さえあれば保存する！
            if title and stamp_str:
                try:
                    dt = datetime.datetime.strptime(stamp_str, "%Y%m%d%H%M%S")
                    
                    data_list.append({
                        "timestamp": dt,
                        "station_id": station_id,
                        "program_name": "Now On Air", # あとで改善可能
                        "dj_name": "",
                        "artist": artist,
                        "title": title
                    })
                except ValueError:
                    continue # 時間の形式がおかしい場合はスキップ

        return data_list

    except Exception as e:
        print(f"Error {station_id}: {e}")
        return []

def main():
    all_data = []
    print("Start crawling (Loose Mode)...")
    
    for station in STATIONS:
        station_data = get_station_data(station)
        if station_data:
            print(f"✅ {station} -> Found {len(station_data)} items")
            all_data.extend(station_data)
        else:
            # データが見つからない場合、中身確認用にログを出す（最初の1局だけ）
            pass 
        
        time.sleep(random.uniform(0.5, 1.0))

    if all_data:
        df = pd.DataFrame(all_data)
        key_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        credentials = service_account.Credentials.from_service_account_info(key_info)
        
        print(f"Saving {len(df)} records to BigQuery...")
        
        pandas_gbq.to_gbq(
            df,
            TABLE_ID,
            project_id=PROJECT_ID,
            if_exists="append",
            credentials=credentials
        )
        print("Done! Data saved.")
    else:
        print("No data found. (Check XML content manually if needed)")

if __name__ == "__main__":
    main()
