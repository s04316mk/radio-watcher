import requests
from bs4 import BeautifulSoup
import pandas as pd
import pandas_gbq
import time
import random
import datetime
import pytz

# ==========================================
# 設定エリア
# ==========================================
PROJECT_ID = "radio-watcher-v2"  # ※もしGCP上のIDが違う場合は修正してください
TABLE_ID = "radio_data.plays"

STATIONS = [
    "AIR-G", "NORTHWAVE",           # 北海道
    "TBS", "QRR", "INT", "FMJ", "FMT", "BAYFM78", "NACK5", "YFM", # 関東
    "ZIP-FM", "FMAICHI",            # 中部
    "ABC", "CCL", "802", "FMO",     # 関西
    "RKB", "KBC", "LOVEFM", "CROSSFM", # 九州
    "FM_OKINAWA"                    # 沖縄
]

def parse_radiko_date(date_str):
    """日付フォーマットの揺らぎに対応する関数"""
    if not date_str:
        return None
    
    # パターン1: 2026-01-21 18:30:00 (ハイフンあり)
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
        
    # パターン2: 20260121183000 (ハイフンなし)
    try:
        return datetime.datetime.strptime(date_str, "%Y%m%d%H%M%S")
    except ValueError:
        return None

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
            title = item.get("title") or ""
            artist = item.get("artist") or ""
            stamp_str = item.get("stamp")
            
            if not artist:
                artist = "Unknown / Talk"

            if title and stamp_str:
                dt = parse_radiko_date(stamp_str)
                
                if dt:
                    data_list.append({
                        "timestamp": dt,
                        "station_id": station_id,
                        "program_name": "Now On Air",
                        "dj_name": "",
                        "artist": artist,
                        "title": title
                    })
                else:
                    print(f"⚠️ Unparsable date: {stamp_str}")

        return data_list

    except Exception as e:
        print(f"Error {station_id}: {e}")
        return []

def main():
    all_data = []
    print("Start crawling (Cloud Run Version)...")
    
    for station in STATIONS:
        station_data = get_station_data(station)
        if station_data:
            print(f"✅ {station} -> Found {len(station_data)} songs")
            all_data.extend(station_data)
        
        time.sleep(random.uniform(0.5, 1.0))

    if all_data:
        df = pd.DataFrame(all_data)
        
        # Cloud Run上では認証情報を自動取得するため、credentialsの指定は不要です
        print(f"Saving {len(df)} records to BigQuery...")
        
        pandas_gbq.to_gbq(
            df,
            TABLE_ID,
            project_id=PROJECT_ID,
            if_exists="append"
            # credentials=credentials ← 削除しました
        )
        print("Done! Data saved.")
    else:
        print("No data found (or all dates failed parsing).")

if __name__ == "__main__":
    main()
