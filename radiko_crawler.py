import os
import sys
import time
import json
import hashlib
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict
import gspread
from google.oauth2.service_account import Credentials
import traceback

# === 設定エリア ===
DEFAULT_STATIONS = "TBS,QRR,FMJ,FMT,INT,LFR,BAYFM78,NACK5,YFM,ABC,MBS,OBC,CCL,802,FMO,CBC,TOKAI,ZIP-FM,FMAICHI,RKB,KBC,LOVEFM,CROSSFM,FMFUKUOKA,HBC,STV,NORTHWAVE,AIR-G"
STATION_IDS = [s.strip() for s in os.environ.get("STATION_IDS", DEFAULT_STATIONS).split(",") if s.strip()]

RADIKO_AUTH1_URL = "https://radiko.jp/v2/api/auth1"
RADIKO_NOA_URL_TEMPLATE = "https://radiko.jp/v3/feed/pc/noa/{station_id}.xml"
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
WORKSHEET_NAME = "plays"

DEFAULT_HEADERS = {
    "X-Radiko-Device": "pc",
    "X-Radiko-App": "pc_html5",
    "X-Radiko-App-Version": "0.0.1",
    "X-Radiko-User": "test-user",
    "User-Agent": "Mozilla/5.0 (compatible; RadikoCrawler/1.0)",
}

def get_auth_token(session: requests.Session) -> str:
    try:
        resp = session.get(RADIKO_AUTH1_URL, headers=DEFAULT_HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.headers.get("X-Radiko-AuthToken", "")
    except Exception:
        pass
    return ""

def parse_noa_xml(xml_text: str) -> List[Dict[str, str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    results = []
    for item in root.findall(".//item"):
        title = item.attrib.get("title")
        artist = item.attrib.get("artist")
        start_time = item.attrib.get("stamp")
        if title and artist and start_time:
            results.append({
                "title": title,
                "artist": artist,
                "start_time": start_time,
                "end_time": ""
            })
    return results

def make_key(station_id: str, artist: str, title: str, start_time: str) -> str:
    base = f"{station_id}|{artist}|{title}|{start_time}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

def connect_sheet():
    json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not json_str:
        raise ValueError("Secret 'GOOGLE_SERVICE_ACCOUNT_JSON' が設定されていません")
    
    info = json.loads(json_str)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    
    try:
        sh = gc.open_by_key(SHEET_ID)
    except Exception as e:
        raise ValueError(f"スプレッドシートが見つかりません (ID: {SHEET_ID})。エラー: {e}")

    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        raise ValueError(f"シート名 '{WORKSHEET_NAME}' が見つかりません。タブ名を 'plays' に変更してください。")
        
    return ws

def main():
    print(f"🚀 全国{len(STATION_IDS)}局の巡回を開始します...")
    
    try:
        ws = connect_sheet()
        existing_keys = set()
        # 直近のデータを取得して重複防止
        try:
            records = ws.get_values("G2:G3000")
            for r in records:
                if r: existing_keys.add(r[0])
        except Exception:
            pass 
            
    except Exception:
        print("❌ シート接続エラー")
        traceback.print_exc()
        sys.exit(1) # エラーなら即終了（赤×にする）

    sess = requests.Session()
    token = get_auth_token(sess)
    headers = DEFAULT_HEADERS.copy()
    if token: headers["X-Radiko-AuthToken"] = token

    new_rows = []
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    for station_id in STATION_IDS:
        url = RADIKO_NOA_URL_TEMPLATE.format(station_id=station_id)
        try:
            resp = sess.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                tracks = parse_noa_xml(resp.text)
                for t in tracks:
                    k = make_key(station_id, t["artist"], t["title"], t["start_time"])
                    if k not in existing_keys:
                        existing_keys.add(k)
                        new_rows.append([now_utc, station_id, t["start_time"], t["end_time"], t["artist"], t["title"], k])
                        print(f"🎵 [NEW] {station_id}: {t['artist']} - {t['title']}")
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️ {station_id}: {e}")

    if new_rows:
        print(f"💾 {len(new_rows)}件を書き込み中...")
        try:
            ws.append_rows(new_rows, value_input_option="USER_ENTERED")
            print("✅ 書き込み完了！")
        except Exception:
            print("❌ 書き込み失敗")
            traceback.print_exc()
            sys.exit(1)
    else:
        print("💤 新しい曲はありませんでした。")

if __name__ == "__main__":
    main()
