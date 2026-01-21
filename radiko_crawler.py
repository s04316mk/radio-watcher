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

# 監視する放送局リスト (ID修正済み)
# ※ NOA(Now On Air)フィードに対応していない局は除外またはエラーになりますが、続行します
STATIONS = [
    "HBC", "STV", "AIR-G", "NORTHWAVE",          # 北海道
    "RAB", "IBC", "TBC", "DATEFM",               # 東北
    "TBS", "QRR", "LFR", "INT", "FMJ", "FMT",    # 関東 (TOKYOFM->FMTに修正)
    "BAYFM78", "NACK5", "YFM",
    "CBC", "TOKAI", "ZIP-FM", "FMAICHI",         # 中部
    "ABC", "MBS", "OBC", "CCL", "802", "FMO",    # 関西
    "RKB", "KBC", "LOVEFM", "CROSSFM",           # 九州
    "RBC", "ROK", "FM_OKINAWA"                   # 沖縄
]

def get_station_data(station_id):
    """RadikoのNOA(Now On Air) XMLから楽曲情報を取得する"""
    url = f"https://radiko.jp/v3/feed/pc/noa/{station_id}.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        # XML解析
        soup = BeautifulSoup(res.content, "xml")
        data_list = []
        
        # 【修正】 <prog>ではなく、直接 <item> を探す
        items = soup.find_all("item")
        
        for item in items:
            title = item.find("title").text if item.find("title") else ""
            artist = item.find("artist").text if item.find("artist") else ""
            stamp_str = item.get("stamp")
            
            # 番組情報はNOAフィードに含まれない場合が多いが、あれば取得
            # 構造が異なる場合があるため、簡易的に親要素などを探す形は取らず、まずは曲優先
            program_name = "Unknown Program"
            dj_name = ""
            
            # もしitemの中にprogramタグがあれば取得（局による）
            # なければ "Unknown" のままでOK（まずは曲を確保）
            
            if title and artist and stamp_str:
                dt = datetime.datetime.strptime(stamp_str, "%Y%m%d%H%M%S")
                
                data_list.append({
                    "timestamp": dt,
                    "station_id": station_id,
                    "program_name": program_name,
                    "dj_name": dj_name,
                    "artist": artist,
                    "title": title
                })
        
        return data_list

    except Exception as e:
        # 404などのエラーは無視して次へ（ログには残す）
        # print(f"Skipping {station_id}: {e}") 
        return []

def main():
    all_data = []
    print("Start crawling (Fixed V2)...")
    
    for station in STATIONS:
        # print(f"Checking {station}...")
        station_data = get_station_data(station)
        if station_data:
            print(f"  -> Found {len(station_data)} songs in {station}")
            all_data.extend(station_data)
        
        time.sleep(random.uniform(0.5, 1.5))

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
        print("No data found (Maybe late night or API limitations).")

if __name__ == "__main__":
    main()
