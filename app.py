import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# ページ設定
st.set_page_config(page_title="Radio Watcher", page_icon="📻", layout="wide")

# 定数
SHEET_ID = st.secrets["GOOGLE_SHEET_ID"]
WORKSHEET_NAME = "plays"

# スプレッドシート接続（キャッシュして高速化）
@st.cache_resource
def connect_sheet():
    # SecretsからJSON文字列を取得して辞書に変換
    json_str = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(json_str)
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

# データ読み込み（キャッシュしてAPI制限対策）
@st.cache_data(ttl=60) # 60秒間はデータを再取得しない
def load_data():
    try:
        ws = connect_sheet()
        # 全データ取得
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return pd.DataFrame()

# === メイン画面 ===
st.title("📻 推し活ラジオ・ウォッチ (Cloud版)")
st.caption("全国のラジオ局を24時間監視中。データは自動更新されます。")

# データ読み込み
with st.spinner('スプレッドシートから最新データを取得中...'):
    df = load_data()

if df.empty:
    st.warning("まだデータがありません。")
    st.stop()

# 表示用に列を整理
if "ts_utc" in df.columns:
    # 1. まず日付型に変換
    df["ts_utc"] = pd.to_datetime(df["ts_utc"])
    
    # 2. 【ここを修正！】元がUTCであることを明示してから、JSTに変換
    df["放送日時(JST)"] = df["ts_utc"].dt.tz_localize("UTC").dt.tz_convert("Asia/Tokyo").dt.strftime("%Y-%m-%d %H:%M:%S")

# 検索フィルター
with st.sidebar:
    st.header("🔍 検索")
    artist_input = st.text_input("アーティスト名", placeholder="例: 星野源")
    song_input = st.text_input("曲名", placeholder="例: 恋")
    
    if st.button("🔄 最新データに更新"):
        load_data.clear() # キャッシュをクリア
        st.rerun()

# フィルタリング処理
results = df.copy()
if artist_input:
    results = results[results["artist"].astype(str).str.contains(artist_input, case=False, na=False)]
if song_input:
    results = results[results["title"].astype(str).str.contains(song_input, case=False, na=False)]

# 結果表示
if artist_input or song_input:
    st.subheader(f"🔎 検索結果: {len(results)} 件")
else:
    st.subheader(f"📡 最新のオンエア（全{len(results)}件）")

# 表示するカラムを選ぶ
display_cols = ["放送日時(JST)", "station_id", "artist", "title", "start_time"]
# データフレームにないカラムは除外
display_cols = [c for c in display_cols if c in results.columns]

# 新しい順に並べ替え
if "放送日時(JST)" in results.columns:
    results = results.sort_values("放送日時(JST)", ascending=False)

st.dataframe(results[display_cols], use_container_width=True, hide_index=True)
