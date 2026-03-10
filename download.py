#!/usr/bin/env python3

import argparse
import sys
import os
import subprocess
import shutil
import json
import re
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError
from base64 import b64encode

def load_env():
    """Загружает переменные из .env файла рядом со скриптом."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and value:
                os.environ.setdefault(key, value)

def check_dependencies():
    """Проверяет наличие yt-dlp и ffmpeg."""
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if missing:
        print(f"❌ Не найдены: {', '.join(missing)}")
        print("   brew install yt-dlp ffmpeg")
        sys.exit(1)

def detect_source(url: str) -> str:
    """Определяет источник по URL."""
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "soundcloud.com" in url:
        return "soundcloud"
    if "spotify.com" in url or "spotify:" in url:
        return "spotify"
    return "unknown"


class SpotifyClient:
    """Минимальный Spotify API клиент на чистом urllib."""

    TOKEN_URL = "https://accounts.spotify.com/api/token"
    API_BASE = "https://api.spotify.com/v1"

    def __init__(self):
        client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            env_path = Path(__file__).resolve().parent / ".env"
            print("❌ Для работы со Spotify нужны API credentials.")
            print()
            print("   1. Зайди на https://developer.spotify.com/dashboard")
            print("   2. Создай приложение (любое имя, Redirect URI: http://localhost)")
            print("   3. Скопируй Client ID и Client Secret")
            print(f"   4. Создай файл .env рядом со скриптом:")
            print(f"      {env_path}")
            print()
            print('   SPOTIFY_CLIENT_ID=твой_client_id')
            print('   SPOTIFY_CLIENT_SECRET=твой_client_secret')
            sys.exit(1)
        self._token = self._auth(client_id, client_secret)

    def _auth(self, client_id: str, client_secret: str) -> str:
        """Client Credentials Flow — получает access token."""
        creds = b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req = Request(
            self.TOKEN_URL,
            data=urlencode({"grant_type": "client_credentials"}).encode(),
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())["access_token"]
        except Exception as e:
            print(f"❌ Ошибка авторизации Spotify: {e}")
            sys.exit(1)

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """GET запрос к Spotify API."""
        url = f"{self.API_BASE}/{endpoint}"
        if params:
            url += "?" + urlencode(params)
        req = Request(url, headers={"Authorization": f"Bearer {self._token}"})
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            if e.code == 429:
                retry = int(e.headers.get("Retry-After", 3))
                print(f"⏳ Rate limit, жду {retry}с...")
                time.sleep(retry)
                return self._get(endpoint, params)
            raise

    def _parse_url(self, url: str) -> tuple[str, str]:
        """Извлекает тип и ID из Spotify URL / URI."""
        # URI: spotify:track:4iV5W9uYEdYUVa79Axb7Rh
        uri_match = re.match(r"spotify:(track|album|playlist):(\w+)", url)
        if uri_match:
            return uri_match.group(1), uri_match.group(2)
        # URL: https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh?si=...
        url_match = re.search(r"open\.spotify\.com/(track|album|playlist)/(\w+)", url)
        if url_match:
            return url_match.group(1), url_match.group(2)
        print(f"❌ Не удалось распарсить Spotify URL: {url}")
        sys.exit(1)

    def _format_track(self, track: dict) -> dict:
        """Форматирует данные трека."""
        artists = ", ".join(a["name"] for a in track["artists"])
        return {
            "title": track["name"],
            "artists": artists,
            "album": track.get("album", {}).get("name", ""),
            "duration": track["duration_ms"] // 1000,
            "query": f"{artists} - {track['name']}",
        }

    def get_tracks(self, url: str) -> list[dict]:
        """Возвращает список треков из Spotify URL (track/album/playlist)."""
        kind, item_id = self._parse_url(url)

        if kind == "track":
            data = self._get(f"tracks/{item_id}")
            return [self._format_track(data)]

        if kind == "album":
            album = self._get(f"albums/{item_id}")
            album_name = album["name"]
            tracks = []
            items = album["tracks"]["items"]
            next_url = album["tracks"].get("next")
            while next_url:
                endpoint = next_url.replace(self.API_BASE + "/", "")
                data = self._get(endpoint)
                items.extend(data["items"])
                next_url = data.get("next")
            for t in items:
                artists = ", ".join(a["name"] for a in t["artists"])
                tracks.append({
                    "title": t["name"],
                    "artists": artists,
                    "album": album_name,
                    "duration": t["duration_ms"] // 1000,
                    "query": f"{artists} - {t['name']}",
                })
            return tracks

        if kind == "playlist":
            tracks = []
            data = self._get(
                f"playlists/{item_id}",
                {"fields": "name,tracks(items(track(name,artists,album(name),duration_ms)),next)"},
            )
            items = data["tracks"]["items"]
            next_url = data["tracks"].get("next")
            while next_url:
                endpoint = next_url.replace(self.API_BASE + "/", "")
                page = self._get(endpoint)
                items.extend(page["items"])
                next_url = page.get("next")
            for item in items:
                t = item.get("track")
                if not t or not t.get("name"):
                    continue  # подкасты, удалённые треки
                tracks.append(self._format_track(t))
            return tracks

        print(f"❌ Неподдерживаемый тип: {kind}")
        sys.exit(1)

def search_youtube(query: str) -> str | None:
    """Ищет трек на YouTube через yt-dlp, возвращает URL."""
    try:
        result = subprocess.run(
            ["yt-dlp", f"ytsearch1:{query}", "--get-id", "--no-playlist", "--no-warnings"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            video_id = result.stdout.strip().split("\n")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        pass
    return None

def get_track_info(url: str) -> dict | None:
    """Получает метаданные трека (YouTube/SoundCloud)."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-download", "--print", "%(title)s\n%(duration)s\n%(id)s", url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        lines = result.stdout.strip().split("\n")
        duration = 0
        try:
            duration = int(float(lines[1] or 0))
        except (ValueError, IndexError):
            pass
        return {"title": lines[0], "duration": duration, "id": lines[2] if len(lines) > 2 else ""}
    except Exception:
        return None

def sanitize_filename(name: str) -> str:
    """Убирает недопустимые символы из имени файла."""
    forbidden = '<>:"/\\|?*'
    for ch in forbidden:
        name = name.replace(ch, "_")
    return name.strip(". ")

def format_duration(seconds: int) -> str:
    """Форматирует секунды в M:SS."""
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"

def build_cmd(
    url: str,
    output_dir: Path,
    stem: str,
    fmt: str,
    sample_rate: int,
) -> list[str]:
    """Собирает команду yt-dlp."""
    cmd = ["yt-dlp", "-x", "--no-playlist", "--no-part", "--quiet"]

    if fmt == "wav":
        cmd += ["--audio-format", "wav",
                "--postprocessor-args", f"ffmpeg:-ar {sample_rate} -ac 2"]
    else:
        cmd += ["--audio-format", "mp3",
                "--postprocessor-args", "ffmpeg:-b:a 320k -ac 2"]

    cmd += ["-o", str(output_dir / f"{stem}.%(ext)s")]
    cmd.append(url)
    return cmd

def download_single(
    url: str,
    output_dir: Path,
    filename: str | None,
    fmt: str,
    sample_rate: int,
    quiet: bool,
) -> bool:
    """Скачивает один трек. Возвращает True при успехе."""
    info = get_track_info(url)
    if not info:
        print(f"  ❌ Не удалось получить информацию: {url}")
        return False

    stem = sanitize_filename(filename) if filename else sanitize_filename(info["title"])
    output_path = output_dir / f"{stem}.{fmt}"

    if output_path.exists():
        if quiet:
            return True
        answer = input(f"  ⚠️  {output_path.name} существует. Перезаписать? [y/N] ").strip().lower()
        if answer != "y":
            return True

    if not quiet:
        fmt_label = f"WAV {sample_rate}Hz" if fmt == "wav" else "MP3 320kbps"
        print(f"  📥 {fmt_label} → {stem}.{fmt}")

    cmd = build_cmd(url, output_dir, stem, fmt, sample_rate)
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0:
        print(f"  ❌ Ошибка загрузки: {stem}")
        return False

    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        if not quiet:
            print(f"  ✅ {output_path.name} ({size_mb:.1f} MB)")
    return True

def handle_spotify(
    url: str,
    output_dir: Path,
    filename: str | None,
    fmt: str,
    sample_rate: int,
    quiet: bool,
):
    """Обрабатывает Spotify URL: track / album / playlist."""
    client = SpotifyClient()
    tracks = client.get_tracks(url)

    if not tracks:
        print("❌ Не удалось получить треки.")
        sys.exit(1)

    total = len(tracks)
    is_single = total == 1

    if is_single:
        t = tracks[0]
        if not quiet:
            print(f"🎵 {t['artists']} — {t['title']}")
            if t["album"]:
                print(f"💿 {t['album']}")
            print(f"⏱  {format_duration(t['duration'])}")
            print(f"🔍 Ищу на YouTube...")

        yt_url = search_youtube(t["query"])
        if not yt_url:
            print(f"❌ Не найдено на YouTube: {t['query']}")
            sys.exit(1)

        if not quiet:
            print(f"🔗 {yt_url}")

        name = filename or f"{t['artists']} - {t['title']}"
        download_single(yt_url, output_dir, name, fmt, sample_rate, quiet)
        return

    # Playlist / Album 
    if not quiet:
        total_dur = sum(t["duration"] for t in tracks)
        fmt_label = f"WAV {sample_rate}Hz" if fmt == "wav" else "MP3 320kbps"
        print(f"📋 {total} треков, ~{format_duration(total_dur)}")
        print(f"🎧 {fmt_label}")
        print(f"📂 {output_dir}")
        print()

    ok = 0
    fail = 0

    for i, t in enumerate(tracks, 1):
        tag = f"[{i}/{total}]"
        if not quiet:
            print(f"{tag} 🔍 {t['artists']} — {t['title']}")

        yt_url = search_youtube(t["query"])
        if not yt_url:
            if not quiet:
                print(f"  ❌ Не найдено на YouTube")
            fail += 1
            continue

        name = f"{t['artists']} - {t['title']}"
        if download_single(yt_url, output_dir, name, fmt, sample_rate, quiet):
            ok += 1
        else:
            fail += 1

    print()
    print(f"📊 Итого: ✅ {ok} загружено, ❌ {fail} ошибок из {total}")

def handle_direct(
    url: str,
    output_dir: Path,
    filename: str | None,
    fmt: str,
    sample_rate: int,
    quiet: bool,
):
    """Прямая загрузка с YouTube / SoundCloud."""
    source = detect_source(url)
    source_label = {"youtube": "YouTube", "soundcloud": "SoundCloud"}.get(source, "URL")

    info = get_track_info(url)
    if not info:
        print("❌ Не удалось получить информацию о треке. Проверь ссылку.")
        sys.exit(1)

    if not quiet:
        print(f"🎵 {info['title']}")
        print(f"📡 {source_label}")
        print(f"⏱  {format_duration(info['duration'])}")

    download_single(url, output_dir, filename, fmt, sample_rate, quiet)
    
def main():
    parser = argparse.ArgumentParser(
        prog="download",
        description="Загрузка аудио с YouTube / SoundCloud / Spotify → WAV или MP3",
        epilog="Примеры:\n"
               '  python3 download.py "https://youtube.com/watch?v=VIDEO_ID"\n'
               '  python3 download.py "https://soundcloud.com/artist/track" -f mp3\n'
               '  python3 download.py "https://open.spotify.com/track/ID"\n'
               '  python3 download.py "https://open.spotify.com/playlist/ID" -f mp3 -o ~/Music\n'
               '  python3 download.py "https://open.spotify.com/album/ID" -f wav -r 48000\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="YouTube / SoundCloud / Spotify (track, album, playlist)")
    parser.add_argument("-f", "--format", dest="fmt", default="wav", choices=["wav", "mp3"],
                        help="wav (lossless) или mp3 (320kbps). По умолчанию: wav")
    parser.add_argument("-o", "--output", default=".",
                        help="Директория для сохранения (по умолчанию: текущая)")
    parser.add_argument("-n", "--name", default=None,
                        help="Имя файла без расширения (только для одного трека)")
    parser.add_argument("-r", "--rate", type=int, default=44100,
                        choices=[22050, 44100, 48000, 96000],
                        help="Sample rate для WAV (по умолчанию: 44100)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Минимальный вывод")

    args = parser.parse_args()
    load_env()
    check_dependencies()

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source = detect_source(args.url)

    if source == "spotify":
        handle_spotify(args.url, output_dir, args.name, args.fmt, args.rate, args.quiet)
    else:
        handle_direct(args.url, output_dir, args.name, args.fmt, args.rate, args.quiet)


if __name__ == "__main__":
    main()
