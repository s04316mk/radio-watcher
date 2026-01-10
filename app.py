import streamlit as st
import sqlite3
import pandas as pd
import time

# ページの設定（タイトルやアイコン）
st.set_page_config(
    page_title="Radio Watcher",
    page_icon="📻",
    layout="wide"
)

# データベースファイル名
DB_NAME = "radiko_history.db"

def load_data(query, params=None):
    """データベースからデータを読み込んで表(DataFrame)にする"""
    conn = sqlite3.connect(DB_NAME)
    if params:
        df = pd.read_sql(query, conn, params=params)
    else:
        df = pd.read_sql(query, conn)
    conn.close()
    return df

# === 画面を作る ===
st.title("📻 推し活ラジオ・ウォッチ")
st.caption("現在監視中のラジオ局から、推しの曲を逆引き検索します")

# サイドバー（左側のメニュー）
with st.sidebar:
    st.header("🔍 検索設定")
    search_text = st.text_input("アーティスト名 / 曲名", placeholder="例: 星野源")
    st.markdown("---")
    if st.button("🔄 最新データに更新"):
        st.rerun()

# メイン画面の表示切り替え
if search_text:
    # === 検索モード ===
    st.subheader(f"🔎 「{search_text}」の検索結果")
    
    # SQLを作る（アーティストか曲名に含まれていればヒット）
    sql = """
        SELECT start_time as '放送日時', station_id as '放送局', artist as 'アーティスト', title as '曲名'
        FROM tracks 
        WHERE artist LIKE ? OR title LIKE ?
        ORDER BY start_time DESC
    """
    search_param = f"%{search_text}%"
    df = load_data(sql, (search_param, search_param))
    
    if len(df) > 0:
        st.success(f"{len(df)} 件見つかりました！")
        # 綺麗な表で表示
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("😢 まだ見つかりません。")

else:
    # === 待機モード（最新の履歴を表示） ===
    st.subheader("📡 最新のオンエア曲 (直近30件)")
    
    sql = """
        SELECT start_time as '放送日時', station_id as '放送局', artist as 'アーティスト', title as '曲名'
        FROM tracks 
        ORDER BY start_time DESC LIMIT 30
    """
    df = load_data(sql)
    
    # 自動更新ボタン
    if st.checkbox("リアルタイム更新モード（5秒毎）"):
        time.sleep(5)
        st.rerun()

    st.dataframe(df, use_container_width=True)
