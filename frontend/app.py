import streamlit as st
import pandas as pd
import pandas_gbq
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

# カスタムCSS
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #00ADB5;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data():
    # --- 修正箇所：鍵ファイル読み込みを削除 ---
    # Cloud Runでは credentials を渡さなくても自動で認証してくれます
    
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
    
    # credentials引数を削除しました（これで顔パスになります）
    df = pandas_gbq.read_gbq(query, project_id=PROJECT_ID)
    return df

try:
    df = load_data()
    
    # 時間を「そのまま」表示する（余計な時差変換をしない）
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)

    # サイドバー
    with st.sidebar:
        st.header("設定")
        if st.button("データを最新にする"):
            st.cache_data.clear()
            st.rerun()
    
    # タイトル
    st.title("📻 Radio Watcher Pro")
    now_time = datetime.datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')
    st.caption(f"Last Update: {now_time}")

    if not df.empty:
        # --- ダッシュボード ---
        col1, col2, col3, col4 = st.columns(4)
        
        today = datetime.datetime.now(pytz.timezone('Asia/Tokyo')).date()
        df['date'] = df['timestamp'].dt.date
        today_count = len(df[df['date'] == today])
        
        with col1:
            st.metric("本日の収集数", f"{today_count:,} 曲")
        with col2:
            st.metric("監視ステーション", f"{df['station_id'].nunique()} 局")
        with col3:
            top_artist = df['artist'].mode()[0] if not df.empty else "-"
            st.metric("Trend Artist", top_artist)
        with col4:
             st.metric("Total Archive", f"{len(df):,} 件")

        st.divider()

        # --- 検索エリア ---
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search_word = st.text_input("🔍 キーワード検索", placeholder="アーティスト名、曲名など...")
        with col_filter:
            station_filter = st.multiselect("放送局で絞り込み", df['station_id'].unique())

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
                "timestamp": st.column_config.DatetimeColumn("On Air Time", format="MM/DD HH:mm:ss"),
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