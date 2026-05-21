# yt-dlp Web Downloader (FastAPI)

このリポジトリは `yt-dlp` を利用したシンプルな Web ダウンローダーの MVP です。

特徴:
- `FastAPI` ベースの Web UI + JSON API
- `yt-dlp` で動画をダウンロードし、`ffmpeg` による変換（MP4 マージ / MP3 抽出）をサポート
- ダウンロードはインスタンス内の一時ディレクトリに保存（`FILE_TTL_MIN` で自動削除）
- シンプルな Bearer トークン認証（`AUTH_TOKEN` 環境変数）

ローカルでの実行 (venv 使用例):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export AUTH_TOKEN=changeme
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Docker:

```bash
docker build -t ytdlp-web .
docker run -p 8080:8080 -e AUTH_TOKEN=changeme ytdlp-web
```

Render でのデプロイ:
- `Dockerfile` ベースの Web Service を作成し、環境変数: `AUTH_TOKEN`, `MAX_CONCURRENT_DOWNLOADS`, `FILE_TTL_MIN` を設定してください。

注意:
- この実装は学習/個人利用向けの MVP です。大量利用や公開サービスとして運用する場合は、S3 などの外部ストレージ、バックグラウンドワーカー、レート制限、監査ログ、利用規約や著作権に関する注意喚起などが必要です。
