"""A small folder-preserving local music server.

Usage:
    python app.py "C:\\Users\\me\\Music"
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import socket
from pathlib import Path
from flask import Flask, abort, jsonify, render_template, request, send_file


SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".flac", ".ogg"}
MAX_SEARCH_RESULTS = 500
MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
}


def create_app(music_root: Path) -> Flask:
    """Create the Flask application for one fixed, resolved music root."""

    root = music_root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"音楽ルートフォルダが存在しないか、フォルダではありません: {root}")

    app = Flask(__name__)
    app.config["MUSIC_ROOT"] = root

    def safe_path(relative_path: str = "") -> Path:
        """Resolve a path and ensure it remains below the configured root.

        Resolving before checking also prevents a symlink inside the music
        folder from exposing files outside it.
        """

        relative_path = relative_path.replace("\\", "/")
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            abort(404)
        return candidate

    def relative_url_path(path: Path) -> str:
        return path.relative_to(root).as_posix()

    @app.get("/")
    def index():
        return render_template("index.html", root_name=root.name or str(root))

    @app.get("/api/browse")
    def browse():
        relative_path = request.args.get("path", "")
        folder = safe_path(relative_path)
        if not folder.is_dir():
            abort(404)

        directories: list[dict[str, str]] = []
        tracks: list[dict[str, str]] = []
        try:
            entries = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
            for entry in entries:
                # Ignore entries that resolve outside the root, including
                # symlinked directories/files.
                try:
                    entry.resolve().relative_to(root)
                except ValueError:
                    continue

                relative = relative_url_path(entry)
                if entry.is_dir():
                    directories.append({"name": entry.name, "path": relative})
                elif entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                    tracks.append(
                        {
                            "name": entry.name,
                            "path": relative,
                            "extension": entry.suffix.lower().lstrip("."),
                        }
                    )
        except OSError:
            abort(404)

        return jsonify(
            {
                "path": relative_path.replace("\\", "/").strip("/"),
                "directories": directories,
                "tracks": tracks,
            }
        )

    @app.get("/api/search")
    def search():
        query = request.args.get("q", "").strip().casefold()
        if not query:
            return jsonify({"query": "", "results": []})

        results: list[dict[str, str]] = []
        for current_dir, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current_dir)
            # Do not descend into symlinked directories or directories that
            # resolve outside the configured music root.
            directory_names[:] = [
                name
                for name in directory_names
                if not (current_path / name).is_symlink()
                and _is_below_root((current_path / name).resolve(), root)
            ]

            for file_name in file_names:
                file_path = current_path / file_name
                if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS or not file_path.is_file():
                    continue
                try:
                    resolved = file_path.resolve()
                    resolved.relative_to(root)
                except (OSError, ValueError):
                    continue

                relative = relative_url_path(file_path)
                if query not in file_name.casefold() and query not in relative.casefold():
                    continue
                results.append({"name": file_name, "path": relative})
                if len(results) >= MAX_SEARCH_RESULTS:
                    break
            if len(results) >= MAX_SEARCH_RESULTS:
                break

        results.sort(key=lambda item: item["path"].casefold())
        return jsonify({"query": query, "results": results})

    @app.get("/media/<path:relative_path>")
    def media(relative_path: str):
        audio_file = safe_path(relative_path)
        if not audio_file.is_file() or audio_file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            abort(404)

        # Flask's conditional send_file response supports HTTP Range requests,
        # which enables seeking and progressive playback in the browser.
        return send_file(
            audio_file,
            mimetype=MIME_TYPES.get(audio_file.suffix.lower(), mimetypes.guess_type(audio_file.name)[0]),
            conditional=True,
            etag=True,
            max_age=0,
        )

    return app


def _is_below_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def local_ip() -> str:
    """Return the LAN-facing address used for the startup hint."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ローカルネットワーク用のフォルダ階層維持型音楽サーバー")
    parser.add_argument(
        "music_root",
        nargs="?",
        default=".",
        help="公開する音楽ルートフォルダ（省略時は現在のフォルダ）",
    )
    parser.add_argument("--port", type=int, default=8000, help="待ち受けポート（既定値: 8000）")
    parser.add_argument("--host", default="0.0.0.0", help="待ち受けアドレス（既定値: 0.0.0.0）")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app = create_app(Path(args.music_root))
    print(f"音楽ルート: {Path(args.music_root).expanduser().resolve()}")
    print(f"このPCから: http://127.0.0.1:{args.port}")
    print(f"同一ネットワークから: http://{local_ip()}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)
