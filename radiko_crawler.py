import os
import time
import json
import hashlib
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import gspread
from google.oauth2.service_account import Credentials

# === 設定エリア ===
# 監視する局（全国版）
DEFAULT_STATIONS = "TBS,QRR,FMJ,FMT,INT,LFR,BAYFM78,NACK5,YFM,ABC,MBS,OBC,CCL,802,FMO,CBC,TOKAI,ZIP-FM,FMAICHI,RKB,KBC,LOVEFM,CROSSFM,FMFUKUOKA,HBC,STV,NORTHWAVE,AIR-G"
STATION_IDS = [s.strip() for s in os.environ.get("STATION_IDS", DEFAULT_STATIONS).split(",") if s.strip()]

RADIKO_AUTH1_URL = "https://radiko.jp/v2/api/auth1"
RADIKO_NOA_URL_TEMPLATE = "https://radiko.jp/v3/feed/pc/noa/{station_id}.xml"
SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
WORKSHEET_NAME = "plays"

DEFAULT_HEADERS = {
    "X-Radiko-Device": "pc",
    "X-Radiko-App": "pc_html5",
    "X-Radiko-App-Version": "0.0.1",
    "X-Radiko-User": "test-user",
    "User-Agent": "Mozilla/5.0 (compatible; RadikoCrawler/1.0)",
}

def get_auth_token(session: requests.Session) -> str:
    resp = session.get(RADIKO_AUTH1_URL, headers=DEFAULT_HEADERS, timeout=10)
    if resp.status_code != 200:
        # Auth失敗時は公開APIとして振る舞うため空文字を返す手もあるが、今回はエラーにする
        print(f"[WARN] Auth failed: {resp.status_code}")
        return ""
    return resp.headers.get("X-Radiko-AuthToken", "")

def parse_noa_xml(xml_text: str) -> List[Dict[str, str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    results = []
    # itemタグの属性からデータを抜く（v3形式）
    for item in root.findall(".//item"):
        title = item.attrib.get("title")
        artist = item.attrib.get("artist")
        start_time = item.attrib.get("stamp")
        
        # 終了時間は必須ではないが、あれば取る
        end_time = "" 
        
        if title and artist and start_time:
            results.append({
                "title": title,
                "artist": artist,
                "start_time": start_time,
                "end_time": end_time,
            })
    return results

def make_key(station_id: str, artist: str, title: str, start_time: str) -> str:
    """重複チェック用のIDを作る"""
    base = f"{station_id}|{artist}|{title}|{start_time}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

def connect_sheet():
    sa_json_str = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(sa_json_str)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

def main():
    print(f"🚀 全国{len(STATION_IDS)}局の巡回を開始します...")
    
    # シートに接続
    try:
        ws = connect_sheet()
        # 既存のキーを取得（直近3000行分くらい）して重複を防ぐ
        existing_keys = set()
        try:
            # G列がkeyと想定
            records = ws.get_values("G2:G3000")
            for r in records:
                if r: existing_keys.add(r[0])
        except Exception as e:
            print(f"[WARN] 既存データの取得に失敗(初回かも): {e}")

    except Exception as e:
        print(f"[ERROR] シート接続エラー: {e}")
        return

    sess = requests.Session()
    token = get_auth_token(sess)
    headers = DEFAULT_HEADERS.copy()
    if token:
        headers["X-Radiko-AuthToken"] = token

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
                        # 新しい曲だ！
                        existing_keys.add(k)
                        new_rows.append([
                            now_utc,
                            station_id,
                            t["start_time"],
                            t["end_time"],
                            t["artist"],
                            t["title"],
                            k
                        ])
                        print(f"🎵 [NEW] {station_id}: {t['artist']} - {t['title']}")
            else:
                print(f"[WARN] {station_id}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[ERROR] {station_id}: {e}")
        
        time.sleep(0.5) # 負荷対策

    # まとめて書き込み
    if new_rows:
        print(f"💾 {len(new_rows)}件をシートに追記します...")
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        print("✅ 完了！")
    else:
        print("💤 新しい曲はありませんでした。")

if __name__ == "__main__":
    main()
