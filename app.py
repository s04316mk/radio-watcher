import streamlit as st
import pandas as pd
import pandas_gbq
from google.oauth2 import service_account
import json
import os

# ==========================================
# 設定エリア
# ==========================================
PROJECT_ID = "radio-watcher-v2"

st.set_page_config(page_title="Radio Watcher Pro", layout="wide")

@st.cache_data(ttl=300)
def load_data():
    # 認証情報の読み込み (Streamlit CloudのSecretsから)
    key_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    credentials = service_account.Credentials.from_service_account_info(key_info)
    
    # 重複排除して最新データを取得
    query = f"""
    SELECT DISTINCT
        timestamp,
        station_id,
        program_name,
        dj_name,
        artist,
        title
    FROM
        `{PROJECT_ID}.radio_data.plays`
    ORDER BY
        timestamp DESC
    LIMIT 2000
    """
    
    df = pandas_gbq.read_gbq(query, project_id=PROJECT_ID, credentials=credentials)
    return df

st.title("📻 Radio Watcher Pro (BigQuery版)")
st.caption("全国のラジオ局を5分間隔で全自動監視中")

try:
    df = load_data()
    
    # 検索機能
    search_word = st.text_input("キーワード検索（番組名やDJ名でも検索できます！）")
    
    if search_word:
        mask = (
            df['artist'].str.contains(search_word, case=False, na=False) |
            df['title'].str.contains(search_word, case=False, na=False) |
            df['program_name'].str.contains(search_word, case=False, na=False) |
            df['dj_name'].str.contains(search_word, case=False, na=False)
        )
        df_display = df[mask]
    else:
        df_display = df

    st.write(f"取得件数: {len(df_display)}件")
    
    # 見やすい順序で表示
    st.dataframe(
        df_display[['timestamp', 'station_id', 'program_name', 'dj_name', 'artist', 'title']],
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.info("まだデータが溜まっていないか、設定中の可能性があります。")
