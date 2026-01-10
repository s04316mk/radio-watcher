import time
import requests
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional

# === 設定エリア（全国版） ===
# 東京・大阪・名古屋・福岡・北海道の主要局を網羅
STATION_IDS = [
    # 東京・関東
    "TBS", "QRR", "FMJ", "FMT", "INT", "LFR", "BAYFM78", "NACK5", "YFM",
    # 大阪・関西
    "ABC", "MBS", "OBC", "CCL", "802", "FMO",
    # 名古屋・東海
    "CBC", "TOKAI", "ZIP-FM", "FMAICHI",
    # 福岡・九州
    "RKB", "KBC", "LOVEFM", "CROSSFM", "FMFUKUOKA",
    # 北海道
    "HBC", "STV", "NORTHWAVE", "AIR-G"
]

# 監視する間隔（秒）
CHECK_INTERVAL = 60 
# データベースのファイル名
DB_NAME = "radiko_history.db"

# Now On AirのURL
RADIKO_NOA_URL_TEMPLATE = "https://radiko.jp/v3/feed/pc/noa/{station_id}.xml"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

@dataclass
class NowOnAirTrack:
    station_id: str
    title: str
    artist: str
    start_time: str

def init_db():
    """データベース準備"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 同じ局・同じ時間の曲は重複して保存しない
    c.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT,
            title TEXT,
            artist TEXT,
            start_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(station_id, start_time)
        )
    ''')
    conn.commit()
    conn.close()

def save_tracks(tracks: List[NowOnAirTrack]):
    """新しい曲を保存"""
    if not tracks:
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    new_count = 0
    
    for t in tracks:
        try:
            # データベースに登録
            c.execute('''
                INSERT INTO tracks (station_id, title, artist, start_time)
                VALUES (?, ?, ?, ?)
            ''', (t.station_id, t.title, t.artist, t.start_time))
            new_count += 1
            
            # 画面に表示！
            print(f"🎵 [NEW] {t.station_id}: {t.artist} - {t.title} ({t.start_time})")
            
        except sqlite3.IntegrityError:
            # すでに保存済みなら何もしない
            pass
            
    conn.commit()
    conn.close()
    if new_count > 0:
        print(f"✨ {new_count}曲を追加しました")

def parse_noa_xml(station_id: str, xml_text: str) -> List[NowOnAirTrack]:
    """XMLを解析"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    tracks = []
    for item in root.findall(".//item"):
        title = item.attrib.get("title")
        artist = item.attrib.get("artist")
        st = item.attrib.get("stamp")

        if title and artist and st:
            tracks.append(NowOnAirTrack(station_id, title, artist, st))
            
    return tracks

def fetch_all_stations():
    """全ステーションを回って曲を取得"""
    all_tracks = []
    print(f"📡 全国{len(STATION_IDS)}局を巡回中...", end="", flush=True)
    
    for station_id in STATION_IDS:
        url = RADIKO_NOA_URL_TEMPLATE.format(station_id=station_id)
        
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=5)
            if resp.status_code == 200:
                tracks = parse_noa_xml(station_id, resp.text)
                all_tracks.extend(tracks)
                print(".", end="", flush=True) # 進捗を表示
            else:
                print("x", end="", flush=True)
                
        except Exception:
            print("!", end="", flush=True)
        
        time.sleep(0.5) # 少しだけ間隔を詰めます（局数が多いので）
        
    print(" 完了！")
    return all_tracks

def main():
    print("🚀 ラジオ全自動監視システム（全国対応版）、起動します...")
    init_db()
    
    # 無限ループで監視開始
    while True:
        print(f"\n⏰ {time.strftime('%H:%M:%S')}")
        tracks = fetch_all_stations()
        save_tracks(tracks)
        
        print(f"😴 {CHECK_INTERVAL}秒待機します...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
