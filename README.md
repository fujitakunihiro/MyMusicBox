# フォルダ階層維持型 ローカルWeb音楽サーバー

指定したフォルダ以下の音楽ファイルを、ディレクトリ階層を維持したままブラウザで閲覧・再生する小さな Flask アプリです。

## 必要環境（直接起動）

- Python 3.9 以上
- Flask

## Docker Compose で起動（推奨）

Docker Desktop をインストールした環境で利用できます。

1. `.env.example` を `.env` にコピーします。
2. `.env` の `MUSIC_ROOT` を音楽フォルダの絶対パスに変更します。
3. コンテナを起動します。

PowerShell の例:

```powershell
Copy-Item .env.example .env
# .env を編集して MUSIC_ROOT=D:/Music などに設定
docker compose up -d --build
```

`.env` の例:

```dotenv
MUSIC_ROOT=D:/Users/ユーザー名/Music
MUSIC_PORT=8000
```

Windows では `D:/Music` のようにスラッシュ区切りで指定すると扱いやすくなります。Docker Desktop の Settings > Resources > File Sharing で、音楽フォルダを共有対象にする必要がある場合があります。

ブラウザで `http://127.0.0.1:8000` を開きます。同一ネットワーク上のスマホや別PCからは、サーバーPCのローカルIPを使って `http://<ローカルIP>:8000` にアクセスします。

停止・再起動・ログ確認:

```powershell
docker compose down
docker compose restart
docker compose logs -f
```

音楽フォルダはコンテナ内 `/music` に読み取り専用（`:ro`）でマウントされます。ホスト側のファイルは変更されません。

## 直接起動

## 起動方法

PowerShell / コマンドプロンプトで、このフォルダに移動して実行します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1       # PowerShell
python -m pip install flask
python app.py "C:\Users\ユーザー名\Music"
```

音楽フォルダを省略すると、現在のフォルダが公開対象になります。

```powershell
python app.py
```

既定ポートは `8000` です。ポートを変更する場合は次のようにします。

```powershell
python app.py "D:\Music" --port 8080
```

起動時に表示される URL をブラウザで開きます。

- サーバーPC: `http://127.0.0.1:8000`
- 同一ネットワーク上のスマホ・別PC: `http://<起動ログに表示されたローカルIP>:8000`

Windows Defender ファイアウォールが通信を確認した場合は、同一ネットワークからの Python の通信を許可してください。ネットワークの種類やルーターの設定によっては、端末間通信が制限されている場合があります。

## 機能

- 音楽ルートフォルダ配下だけを表示
- フォルダのパンくず移動
- 音楽ルート全体から曲名・フォルダ名を検索
- `.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg` の表示・再生
- 再生、一時停止、前曲、次曲、シーク、音量調整
- 現在のフォルダ内の曲を上から順に自動再生
- HTTP Range Requests によるシーク対応
- 外部 JavaScript ライブラリ不要

## セキュリティ上の注意

このアプリはローカルネットワーク向けの簡易サーバーです。指定した音楽ルートより上位のパス、`..` を使ったパス、ルート外を指すシンボリックリンクは公開しません。ただし、インターネットへ直接公開する用途の認証・TLS・アクセス制御は実装していません。

ブラウザ側の音声コーデック対応はブラウザに依存します。特に FLAC や一部の M4A は、使用するブラウザによって再生できない場合があります。
