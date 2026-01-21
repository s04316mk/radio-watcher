FROM python:3.9-slim

# ログを即座に出力させる設定
ENV PYTHONUNBUFFERED True

WORKDIR /app

# すべてのファイルをコンテナにコピー
COPY . .

# 必要なライブラリをインストール
# (requirements.txtに依存せず、ここで確実にインストールします)
RUN pip install --no-cache-dir requests beautifulsoup4 pandas pandas-gbq lxml google-auth pytz

# 実行コマンド
CMD ["python", "radiko_crawler.py"]
