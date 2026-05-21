from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
import yt_dlp
import os
import tempfile
import shutil

app = FastAPI(title="Render yt-dlp Tool")

class VideoUrl(BaseModel):
    url: str

@app.get("/", response_class=HTMLResponse)
async def root():
    """シンプルなUIを提供"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>yt-dlp on Render</title>
        <style>
            body { font-family: sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }
            input[type="text"] { width: 70%; padding: 0.5rem; }
            button { padding: 0.5rem 1rem; cursor: pointer; }
            .result { margin-top: 1rem; border: 1px solid #ccc; padding: 1rem; border-radius: 4px; }
            .error { color: red; }
            pre { background: #f4f4f4; padding: 0.5rem; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>📥 YouTube Downloader (on Render)</h1>
        <p>動画URLを入力してください。</p>
        <div>
            <input type="text" id="urlInput" placeholder="https://www.youtube.com/watch?v=..." />
            <button onclick="fetchInfo()">情報取得</button>
            <button onclick="downloadVideo()">ダウンロード</button>
        </div>
        <div id="output" class="result" style="display:none;"></div>

        <script>
            async function fetchInfo() {
                const url = document.getElementById('urlInput').value;
                const outputDiv = document.getElementById('output');
                outputDiv.style.display = 'block';
                outputDiv.innerHTML = '処理中...';
                
                try {
                    const res = await fetch('/api/info', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({url: url})
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail);
                    outputDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch (e) {
                    outputDiv.innerHTML = `<p class="error">エラー: ${e.message}</p>`;
                }
            }

            async function downloadVideo() {
                const url = document.getElementById('urlInput').value;
                const outputDiv = document.getElementById('output');
                outputDiv.style.display = 'block';
                outputDiv.innerHTML = 'ダウンロード準備中... (時間がかかる場合があります)';
                
                window.location.href = `/api/download?url=${encodeURIComponent(url)}`;
                setTimeout(() => { outputDiv.innerHTML = 'ダウンロードが開始されました。'; }, 2000);
            }
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/api/info")
async def get_video_info(video: VideoUrl):
    """動画のメタデータを取得"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False, # 完全な情報を取得
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video.url, download=False)
            # シリアライズ可能な形に整形（一部巨大なフィールドは除外）
            safe_info = {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "view_count": info.get("view_count"),
                "thumbnail": info.get("thumbnail"),
                "formats_count": len(info.get("formats", [])),
                "url": video.url
            }
            return safe_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/download")
async def download_video(url: str = Query(...)):
    """動画をダウンロードしてストリーミング返却"""
    # 一時ディレクトリの作成
    temp_dir = tempfile.mkdtemp()
    filename_template = os.path.join(temp_dir, '%(title)s.%(ext)s')
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # MP4優先、なければベスト
        'outtmpl': filename_template,
        'quiet': True,
        'no_warnings': True,
        # 必要に応じて Cookie や Proxy をここに追加
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise HTTPException(status_code=404, detail="Video not found")
            
            # ダウンロードされたファイルパスを特定
            downloaded_path = ydl.prepare_filename(info)
            
            # ファイルが存在するか確認（フォーマット統合などで拡張子が変わる場合があるため調整が必要なら此处を強化）
            if not os.path.exists(downloaded_path):
                # .webm や他の拡張子を試す（簡易的なフォールバック）
                base_name = os.path.splitext(downloaded_path)[0]
                for ext in ['.mp4', '.webm', '.mkv']:
                    if os.path.exists(base_name + ext):
                        downloaded_path = base_name + ext
                        break
            
            if not os.path.exists(downloaded_path):
                raise HTTPException(status_code=500, detail="Downloaded file not found")

            # ファイル名を安全に（日本語などを含む場合があるため）
            file_name = os.path.basename(downloaded_path)
            
            def iterfile():
                with open(downloaded_path, mode="rb") as file_like:
                    yield from file_like
            
            return StreamingResponse(iterfile(), media_type="video/mp4", headers={"Content-Disposition": f"attachment; filename={file_name}"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
    finally:
        # 後処理：一時ディレクトリを削除（ただし、StreamingResponse が完了する前に消えないよう注意が必要だが、
        # Pythonのガベージコレクションやレスポンス終了後の処理としては単純なtry/finallyで十分ではない場合がある。
        # 今回はシンプルさ優先とし、OSの/tmp定期清掃に任せるか、バックグラウンドで削除する設計が理想だが、
        # Renderのエフェメラルファイルシステムなので、プロセス終了時に消えれば問題ないことが多い。）
        # ※実際には StreamingResponse が完了するまで待たずに finally が実行されるため、
        # 厳密には別スレッドで削除するか、OSのクリーンアップに任せるのが安全。
        # ここでは簡易実装のため、あえて即時削除はせず、OS依存とする（Renderは再起動でクリアされるため）。
        pass 

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
