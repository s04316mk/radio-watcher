import requests

def main():
    print("🕵️‍♂️ SPY MODE STARTED (ラジコの中身を盗み見ます)")
    
    # テストとして、確実に放送している「TOKYO FM」だけを見に行きます
    target_station = "FMT"
    url = f"https://radiko.jp/v3/feed/pc/noa/{target_station}.xml"
    
    # 偽装工作（普通のブラウザのふりをする）
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Connecting to {url}...")
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        print(f"📡 Status Code: {res.status_code}")
        
        print("\n▼▼▼▼▼ 実際の受信データ (最初の1000文字) ▼▼▼▼▼")
        # ここに表示される内容が「答え」です
        print(res.text[:1000]) 
        print("▲▲▲▲▲ 受信データ終了 ▲▲▲▲▲\n")
        
        if "<item>" in res.text:
            print("💡 'item' タグが見つかりました！データはあるはずです！")
        else:
            print("⚠️ 'item' タグが見当たりません。これが原因です！")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    main()
