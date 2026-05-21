# Render 用 yt-dlp ツール

このアプリケーションは、[Render](https://render.com) 上で動作する、`yt-dlp` を利用した動画ダウンロードツールです。

## 機能

- **Web UI**: ブラウザから動画 URL を入力して操作可能
- **情報取得**: 動画のタイトル、投稿者、再生時間などのメタデータを取得
- **ダウンロード**: 動画を MP4 フォーマットでダウンロード

## デプロイ方法 (Render)

1. このリポジトリを GitHub にプッシュします。
2. Render のダッシュボードにログインし、「New Web Service」を作成します。
3. GitHub リポジトリを選択します。
4. 以下の設定を確認・入力します：
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Environment**: Python 3
5. 「Create Web Service」をクリックしてデプロイを開始します。

## 注意点

- **ストレージ**: Render の無料枠はエフェメラル（一時的）なファイルシステムを使用しています。ダウンロードされたファイルはリクエスト終了後に消去されますが、容量制限（ディスク使用量）に注意してください。
- **CPU/メモリ**: 長時間の動画や高画質の動画は処理に時間がかかり、タイムアウトする可能性があります。
- **利用規約**: YouTube やその他のサイトの利用規約に従って利用してください。私的利用の範囲で使用することを推奨します。

## API エンドポイント

- `GET /`: Web UI
- `POST /api/info`: 動画情報の取得 (JSON)
  - Body: `{"url": "https://..."}`
- `GET /api/download?url=...`: 動画のダウンロード

## ローカルでの実行

```bash
pip install -r requirements.txt
python main.py
```

ブラウザで `http://localhost:8000` にアクセスしてください。
