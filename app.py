import streamlit as st
import pandas as pd
import pandas_gbq
from google.oauth2 import service_account
import json
import datetime
import pytz

# ==========================================
# 設定エリア
# ==========================================
PROJECT_ID = "radio-watcher-v2"

st.set_page_config(
    page_title="Radio Watcher Pro",
    page_icon="📻",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# カスタムCSS（KPIカードをおしゃれに）
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #00ADB5; /* ネオンカラー */
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    key_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    credentials = service_account.Credentials.from_service_account_info(key_info)
    
    # 最新3000件を取得
    query = f"""
    SELECT DISTINCT
        timestamp,
        station_id,
        program_name,
        artist,
        title
    FROM
        `{PROJECT_ID}.radio_data.plays`
    ORDER BY
        timestamp DESC
    LIMIT 3000
    """
    df = pandas_gbq.read_gbq(query, project_id=PROJECT_ID, credentials=credentials)
    return df

try:
    df = load_data()
    
    # データを東京時間に変換
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('Asia/Tokyo')

    # サイドバー（更新ボタン）
    with st.sidebar:
        st.header("設定")
        if st.button("データを最新にする"):
            st.cache_data.clear()
            st.rerun()
    
    # タイトル
    st.title("📻 Radio Watcher Pro")
    st.caption(f"Last Update: {datetime.datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')}")

    if not df.empty:
        # --- ダッシュボードエリア ---
        col1, col2, col3, col4 = st.columns(4)
        
        # 今日の日付のデータをカウント
        today = datetime.datetime.now(pytz.timezone('Asia/Tokyo')).date()
        df['date'] = df['timestamp'].dt.date
        today_count = len(df[df['date'] == today])
        
        with col1:
            st.metric("本日の収集数", f"{today_count:,} 曲")
        with col2:
            st.metric("監視ステーション", f"{df['station_id'].nunique()} 局")
        with col3:
            # 一番多く流れているアーティスト
            top_artist = df['artist'].mode()[0] if not df.empty else "-"
            st.metric("Trend Artist", top_artist)
        with col4:
             st.metric("Total Archive", f"{len(df):,} 件")

        st.divider()

        # --- 検索＆フィルタエリア ---
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search_word = st.text_input("🔍 キーワード検索", placeholder="アーティスト名、曲名など...")
        with col_filter:
            station_filter = st.multiselect("放送局で絞り込み", df['station_id'].unique())

        # フィルタリング
        df_display = df.copy()
        if search_word:
            mask = (
                df_display['artist'].str.contains(search_word, case=False, na=False) |
                df_display['title'].str.contains(search_word, case=False, na=False)
            )
            df_display = df_display[mask]
        
        if station_filter:
            df_display = df_display[df_display['station_id'].isin(station_filter)]

        # --- メインテーブル ---
        st.dataframe(
            df_display[['timestamp', 'station_id', 'program_name', 'artist', 'title']],
            column_config={
                "timestamp": st.column_config.DatetimeColumn("On Air Time", format="MM/DD HH:mm"),
                "station_id": "Station",
                "artist": st.column_config.TextColumn("Artist", width="medium"),
                "title": st.column_config.TextColumn("Title", width="medium"),
                "program_name": "Program",
            },
            use_container_width=True,
            hide_index=True,
            height=600
        )
    else:
        st.info("データ収集中です...")

except Exception as e:
    st.error(f"システムエラー: {e}")
