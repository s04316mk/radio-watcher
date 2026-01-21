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

# 監視する放送局リスト (28局)
STATIONS = [
    "HBC", "STV", "AIR-G", "NORTHWAVE",
    "RAB", "IBC", "TBC", "DATEFM",
    "TBS", "QRR", "LFR", "INT", "FMJ", "TOKYOFM", "BAYFM78", "NACK5", "YFM",
    "CBC", "TOKAI", "ZIP-FM", "FMAICHI",
    "ABC", "MBS", "OBC", "CCL", "802", "FMO",
    "RKB", "KBC", "LOVEFM", "CROSSFM",
    "RBC", "ROK", "FM_OKINAWA"
]

def get_station_data(station_id):
    url = f"https://radiko.jp/v3/feed/pc/noa/{station_id}.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, "xml")
        
        data_list = []
        progs = soup.find_all("prog")
        
        for prog in progs:
            program_name = prog.find("title").text if prog.find("title") else ""
            dj_name = prog.find("pfm").text if prog.find("pfm") else ""
            
            songs = prog.find_all("item")
            for song in songs:
                title = song.find("title").text if song.find("title") else ""
                artist = song.find("artist").text if song.find("artist") else ""
                stamp_str = song.get("stamp")
                
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
        print(f"Error fetching {station_id}: {e}")
        return []

def main():
    all_data = []
    print("Start crawling...")
    
    for station in STATIONS:
        print(f"Checking {station}...")
        station_data = get_station_data(station)
        all_data.extend(station_data)
        sleep_time = random.uniform(1, 3)
        time.sleep(sleep_time)

    if all_data:
        df = pd.DataFrame(all_data)
        
        # 認証情報の読み込み
        key_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        credentials = service_account.Credentials.from_service_account_info(key_info)
        
        print(f"Saving {len(df)} records to BigQuery...")
        
        # BigQueryへ保存
        pandas_gbq.to_gbq(
            df,
            TABLE_ID,
            project_id=PROJECT_ID,
            if_exists="append",
            credentials=credentials
        )
        print("Done!")
    else:
        print("No data found.")

if __name__ == "__main__":
    main()
