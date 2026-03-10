#!/usr/bin/env python3

import argparse
import sys
import os
import subprocess
import shutil
import json
import re
import time
import threading
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError
from base64 import b64encode


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SPOTIFY API — вставь свои ключи сюда                                      ║
# ║  Получить: https://developer.spotify.com/dashboard                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""

class C:
    """Цвета и эффекты для терминала."""
    RST       = "\033[0m"
    BOLD      = "\033[1m"
    DIM       = "\033[2m"
    # Greens
    GREEN     = "\033[38;5;46m"
    LIME      = "\033[38;5;118m"
    MINT      = "\033[38;5;48m"
    # Purples
    PURPLE    = "\033[38;5;135m"
    VIOLET    = "\033[38;5;99m"
    MAGENTA   = "\033[38;5;201m"
    PINK      = "\033[38;5;213m"
    # Neon accents
    CYAN      = "\033[38;5;51m"
    WHITE     = "\033[38;5;255m"
    GRAY      = "\033[38;5;240m"
    RED       = "\033[38;5;196m"
    YELLOW    = "\033[38;5;226m"
    # Backgrounds
    BG_PURPLE = "\033[48;5;53m"
    BG_GREEN  = "\033[48;5;22m"

    @staticmethod
    def neon_green(text):  return f"{C.BOLD}{C.GREEN}{text}{C.RST}"
    @staticmethod
    def neon_purple(text): return f"{C.BOLD}{C.PURPLE}{text}{C.RST}"
    @staticmethod
    def neon_violet(text): return f"{C.BOLD}{C.VIOLET}{text}{C.RST}"
    @staticmethod
    def neon_cyan(text):   return f"{C.BOLD}{C.CYAN}{text}{C.RST}"
    @staticmethod
    def neon_mag(text):    return f"{C.BOLD}{C.MAGENTA}{text}{C.RST}"
    @staticmethod
    def dim(text):         return f"{C.DIM}{text}{C.RST}"
    @staticmethod
    def err(text):         return f"{C.BOLD}{C.RED}{text}{C.RST}"
    @staticmethod
    def ok(text):          return f"{C.BOLD}{C.LIME}{text}{C.RST}"
    @staticmethod
    def warn(text):        return f"{C.BOLD}{C.YELLOW}{text}{C.RST}"

LOGO_LINES = [
    "██████╗  ██╗      ",
    "██╔══██╗ ██║      ",
    "██║  ██║ ██║      ",
    "██║  ██║ ██║      ",
    "██████╔╝ ███████╗ ",
    "╚═════╝  ╚══════╝ ",
]

TITLE_LINES = [
    "█████╗ ██╗   ██╗██████╗ ██╗ ██████╗ ",
    "██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗",
    "███████║██║   ██║██║  ██║██║██║   ██║",
    "██╔══██║██║   ██║██║  ██║██║██║   ██║",
    "██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝",
    "╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝ ",
]

# Gradient palette: green → cyan → purple → magenta
GRADIENT = [
    "\033[38;5;46m",   # green
    "\033[38;5;48m",   # mint
    "\033[38;5;50m",   # cyan-green
    "\033[38;5;51m",   # cyan
    "\033[38;5;93m",   # blue-purple
    "\033[38;5;99m",   # violet
    "\033[38;5;135m",  # purple
    "\033[38;5;171m",  # magenta-purple
    "\033[38;5;201m",  # magenta
    "\033[38;5;213m",  # pink
]

def print_splash(quiet: bool = False):
    """Анимированный splash screen с neon-градиентом."""
    if quiet:
        return

    cols = shutil.get_terminal_size().columns
    total_lines = LOGO_LINES

    # Объединяем DL + AUDIO
    combined = []
    for i in range(len(LOGO_LINES)):
        left = LOGO_LINES[i] if i < len(LOGO_LINES) else ""
        right = TITLE_LINES[i] if i < len(TITLE_LINES) else ""
        combined.append(left + right)

    # Neon wave animation
    frames = 8
    try:
        for frame in range(frames):
            sys.stdout.write("\033[?25l")  # скрыть курсор
            if frame > 0:
                sys.stdout.write(f"\033[{len(combined) + 2}A")  # вверх

            print()
            for i, line in enumerate(combined):
                color_idx = (i + frame) % len(GRADIENT)
                color = GRADIENT[color_idx]
                padded = line.center(cols)
                sys.stdout.write(f"{color}{C.BOLD}{padded}{C.RST}\n")
            print()

            time.sleep(0.07)

        sys.stdout.write("\033[?25h")  # вернуть курсор
    except (KeyboardInterrupt, BrokenPipeError):
        sys.stdout.write("\033[?25h")

    # Tagline
    tag = "⚡ YouTube · SoundCloud · Spotify → WAV / MP3 ⚡"
    print(f"{C.BOLD}{C.VIOLET}{tag.center(cols)}{C.RST}")

    sep = "─" * min(60, cols - 4)
    print(f"{C.PURPLE}{sep.center(cols)}{C.RST}")
    print()

class Spinner:
    """Анимированный спиннер для долгих операций."""
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    COLORS = [C.GREEN, C.LIME, C.MINT, C.CYAN, C.VIOLET, C.PURPLE, C.MAGENTA, C.PINK]

    def __init__(self, message: str):
        self.message = message
        self._stop = threading.Event()
        self._thread = None

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            color = self.COLORS[i % len(self.COLORS)]
            sys.stdout.write(f"\r  {color}{C.BOLD}{frame}{C.RST} {C.WHITE}{self.message}{C.RST} ")
            sys.stdout.flush()
            i += 1
            time.sleep(0.08)
        sys.stdout.write(f"\r{' ' * (len(self.message) + 10)}\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()
        
def progress_bar(current: int, total: int, width: int = 30) -> str:
    """Красивый прогресс-бар с градиентом."""
    pct = current / total if total else 0
    filled = int(width * pct)
    empty = width - filled

    bar = ""
    for i in range(filled):
        color_idx = int(i / width * (len(GRADIENT) - 1))
        bar += f"{GRADIENT[color_idx]}█"
    bar += f"{C.GRAY}{'░' * empty}{C.RST}"

    return f"{bar} {C.WHITE}{C.BOLD}{current}{C.RST}{C.GRAY}/{total}{C.RST}"

def check_dependencies():
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if missing:
        print(f"  {C.err('✘')} Не найдены: {C.BOLD}{', '.join(missing)}{C.RST}")
        print(f"    {C.dim('brew install yt-dlp ffmpeg')}")
        sys.exit(1)

def detect_source(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "soundcloud.com" in url:
        return "soundcloud"
    if "spotify.com" in url or "spotify:" in url:
        return "spotify"
    return "unknown"


SOURCE_ICONS = {
    "youtube":    f"{C.RED}▶{C.RST}  YouTube",
    "soundcloud": f"{C.YELLOW}☁{C.RST}  SoundCloud",
    "spotify":    f"{C.GREEN}●{C.RST}  Spotify",
    "unknown":    f"{C.GRAY}?{C.RST}  URL",
}

class SpotifyClient:
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    API_BASE = "https://api.spotify.com/v1"

    def __init__(self):
        cid = SPOTIFY_CLIENT_ID or os.environ.get("SPOTIFY_CLIENT_ID", "")
        csec = SPOTIFY_CLIENT_SECRET or os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        if not cid or not csec:
            print()
            print(f"  {C.err('✘')} Для Spotify нужны API credentials.")
            print()
            print(f"    {C.neon_cyan('1.')} Зайди на {C.BOLD}https://developer.spotify.com/dashboard{C.RST}")
            print(f"    {C.neon_cyan('2.')} Создай приложение")
            print(f"    {C.neon_cyan('3.')} Открой {C.neon_green('download.py')} и заполни:")
            print()
            print(f"    {C.neon_purple('SPOTIFY_CLIENT_ID')}     = {C.dim('\"твой_client_id\"')}")
            print(f"    {C.neon_purple('SPOTIFY_CLIENT_SECRET')} = {C.dim('\"твой_client_secret\"')}")
            print()
            sys.exit(1)
        self._token = self._auth(cid, csec)

    def _auth(self, client_id, client_secret):
        creds = b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req = Request(
            self.TOKEN_URL,
            data=urlencode({"grant_type": "client_credentials"}).encode(),
            headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())["access_token"]
        except Exception as e:
            print(f"  {C.err('✘')} Spotify auth: {e}")
            sys.exit(1)

    def _get(self, endpoint, params=None):
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
                print(f"  {C.warn('⏳')} Rate limit, жду {retry}с...")
                time.sleep(retry)
                return self._get(endpoint, params)
            raise

    def _parse_url(self, url):
        m = re.match(r"spotify:(track|album|playlist):(\w+)", url)
        if m:
            return m.group(1), m.group(2)
        m = re.search(r"open\.spotify\.com/(track|album|playlist)/(\w+)", url)
        if m:
            return m.group(1), m.group(2)
        print(f"  {C.err('✘')} Не удалось распарсить: {url}")
        sys.exit(1)

    def _fmt_track(self, t):
        artists = ", ".join(a["name"] for a in t["artists"])
        return {
            "title": t["name"],
            "artists": artists,
            "album": t.get("album", {}).get("name", ""),
            "duration": t["duration_ms"] // 1000,
            "query": f"{artists} - {t['name']}",
        }

    def _paginate(self, items, next_url):
        while next_url:
            ep = next_url.replace(self.API_BASE + "/", "")
            data = self._get(ep)
            items.extend(data["items"])
            next_url = data.get("next")
        return items

    def get_tracks(self, url):
        kind, item_id = self._parse_url(url)

        if kind == "track":
            return [self._fmt_track(self._get(f"tracks/{item_id}"))]

        if kind == "album":
            album = self._get(f"albums/{item_id}")
            items = self._paginate(album["tracks"]["items"], album["tracks"].get("next"))
            return [{
                "title": t["name"],
                "artists": ", ".join(a["name"] for a in t["artists"]),
                "album": album["name"],
                "duration": t["duration_ms"] // 1000,
                "query": f"{', '.join(a['name'] for a in t['artists'])} - {t['name']}",
            } for t in items]

        if kind == "playlist":
            data = self._get(f"playlists/{item_id}",
                {"fields": "name,tracks(items(track(name,artists,album(name),duration_ms)),next)"})
            items = self._paginate(data["tracks"]["items"], data["tracks"].get("next"))
            tracks = []
            for item in items:
                t = item.get("track")
                if t and t.get("name"):
                    tracks.append(self._fmt_track(t))
            return tracks

        print(f"  {C.err('✘')} Неподдерживаемый тип: {kind}")
        sys.exit(1)

def search_youtube(query):
    try:
        r = subprocess.run(
            ["yt-dlp", f"ytsearch1:{query}", "--get-id", "--no-playlist", "--no-warnings"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and r.stdout.strip():
            return f"https://www.youtube.com/watch?v={r.stdout.strip().split(chr(10))[0]}"
    except Exception:
        pass
    return None

def get_track_info(url):
    try:
        r = subprocess.run(
            ["yt-dlp", "--no-download", "--print", "%(title)s\n%(duration)s\n%(id)s", url],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return None
        lines = r.stdout.strip().split("\n")
        dur = 0
        try:
            dur = int(float(lines[1] or 0))
        except (ValueError, IndexError):
            pass
        return {"title": lines[0], "duration": dur}
    except Exception:
        return None

def sanitize(name):
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "_")
    return name.strip(". ")


def fmt_dur(s):
    m, sec = divmod(s, 60)
    return f"{m}:{sec:02d}"


def fmt_size(bytes_):
    mb = bytes_ / (1024 * 1024)
    return f"{mb:.1f} MB"


def build_cmd(url, output_dir, stem, fmt, sample_rate):
    cmd = ["yt-dlp", "-x", "--no-playlist", "--no-part", "--quiet"]
    if fmt == "wav":
        cmd += ["--audio-format", "wav", "--postprocessor-args", f"ffmpeg:-ar {sample_rate} -ac 2"]
    else:
        cmd += ["--audio-format", "mp3", "--postprocessor-args", "ffmpeg:-b:a 320k -ac 2"]
    cmd += ["-o", str(output_dir / f"{stem}.%(ext)s"), url]
    return cmd

def download_single(url, output_dir, filename, fmt, sample_rate, quiet):
    info = get_track_info(url)
    if not info:
        print(f"  {C.err('✘')} Не удалось получить информацию")
        return False

    stem = sanitize(filename) if filename else sanitize(info["title"])
    output_path = output_dir / f"{stem}.{fmt}"

    if output_path.exists():
        if quiet:
            return True
        a = input(f"  {C.warn('!')} {output_path.name} существует. Перезаписать? [y/N] ").strip().lower()
        if a != "y":
            return True

    fmt_label = f"WAV {sample_rate}Hz" if fmt == "wav" else "MP3 320kbps"

    if not quiet:
        with Spinner(f"{fmt_label} → {stem}.{fmt}"):
            result = subprocess.run(build_cmd(url, output_dir, stem, fmt, sample_rate), capture_output=True)
    else:
        result = subprocess.run(build_cmd(url, output_dir, stem, fmt, sample_rate), capture_output=True)

    if result.returncode != 0:
        print(f"  {C.err('✘')} Ошибка загрузки: {stem}")
        return False

    if output_path.exists():
        size = fmt_size(output_path.stat().st_size)
        if not quiet:
            print(f"  {C.ok('✔')} {C.neon_green(stem)}.{fmt}  {C.dim(size)}")
    return True

def handle_spotify(url, output_dir, filename, fmt, sample_rate, quiet):
    with Spinner("Получаю данные из Spotify..."):
        client = SpotifyClient()
        tracks = client.get_tracks(url)

    if not tracks:
        print(f"  {C.err('✘')} Не удалось получить треки")
        sys.exit(1)

    total = len(tracks)

    if total == 1:
        t = tracks[0]
        if not quiet:
            print(f"  {C.neon_purple('♫')} {C.BOLD}{t['artists']}{C.RST} {C.dim('—')} {C.WHITE}{t['title']}{C.RST}")
            if t["album"]:
                print(f"  {C.neon_violet('◉')} {t['album']}")
            print(f"  {C.neon_cyan('⏱')} {fmt_dur(t['duration'])}")
            print()

        with Spinner("Ищу на YouTube..."):
            yt_url = search_youtube(t["query"])

        if not yt_url:
            print(f"  {C.err('✘')} Не найдено на YouTube: {t['query']}")
            sys.exit(1)

        if not quiet:
            print(f"  {C.neon_green('⇢')} {C.dim(yt_url)}")

        name = filename or f"{t['artists']} - {t['title']}"
        download_single(yt_url, output_dir, name, fmt, sample_rate, quiet)
        return

    # ── Playlist / Album ──
    if not quiet:
        total_dur = sum(t["duration"] for t in tracks)
        fmt_label = f"{C.neon_green('WAV')} {sample_rate}Hz" if fmt == "wav" else f"{C.neon_purple('MP3')} 320kbps"
        print(f"  {C.neon_purple('◉')} {C.BOLD}{total} треков{C.RST}  {C.dim('•')}  {fmt_dur(total_dur)}  {C.dim('•')}  {fmt_label}")
        print(f"  {C.neon_cyan('⇣')} {output_dir}")
        print()

    ok = fail = 0

    for i, t in enumerate(tracks, 1):
        if not quiet:
            bar = progress_bar(i, total)
            print(f"  {bar}  {C.neon_purple('♫')} {t['artists']} — {t['title']}")

        yt_url = search_youtube(t["query"])
        if not yt_url:
            if not quiet:
                print(f"    {C.err('✘')} Не найдено на YouTube")
            fail += 1
            continue

        name = f"{t['artists']} - {t['title']}"
        if download_single(yt_url, output_dir, name, fmt, sample_rate, quiet):
            ok += 1
        else:
            fail += 1

    # Summary
    print()
    sep = f"{C.PURPLE}{'─' * 40}{C.RST}"
    print(f"  {sep}")
    print(f"  {C.ok('✔')} {ok} загружено   {C.err('✘')} {fail} ошибок   {C.dim(f'из {total}')}")
    print()

def handle_direct(url, output_dir, filename, fmt, sample_rate, quiet):
    source = detect_source(url)

    if not quiet:
        with Spinner("Получаю информацию..."):
            info = get_track_info(url)
    else:
        info = get_track_info(url)

    if not info:
        print(f"  {C.err('✘')} Не удалось получить информацию. Проверь ссылку.")
        sys.exit(1)

    if not quiet:
        icon = SOURCE_ICONS.get(source, SOURCE_ICONS["unknown"])
        print(f"  {C.neon_purple('♫')} {C.BOLD}{info['title']}{C.RST}")
        print(f"  {icon}")
        print(f"  {C.neon_cyan('⏱')} {fmt_dur(info['duration'])}")
        print()

    download_single(url, output_dir, filename, fmt, sample_rate, quiet)

def main():
    parser = argparse.ArgumentParser(
        prog="download",
        description="Загрузка аудио: YouTube / SoundCloud / Spotify → WAV или MP3",
        epilog="Примеры:\n"
               '  python3 download.py "https://youtube.com/watch?v=VIDEO_ID"\n'
               '  python3 download.py "https://soundcloud.com/artist/track" -f mp3\n'
               '  python3 download.py "https://open.spotify.com/track/ID"\n'
               '  python3 download.py "https://open.spotify.com/playlist/ID" -f mp3 -o ~/Music\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="YouTube / SoundCloud / Spotify (track, album, playlist)")
    parser.add_argument("-f", "--format", dest="fmt", default="wav", choices=["wav", "mp3"],
                        help="wav (lossless) или mp3 (320kbps). По умолчанию: wav")
    parser.add_argument("-o", "--output", default=".",
                        help="Директория для сохранения")
    parser.add_argument("-n", "--name", default=None,
                        help="Имя файла без расширения (один трек)")
    parser.add_argument("-r", "--rate", type=int, default=44100,
                        choices=[22050, 44100, 48000, 96000],
                        help="Sample rate для WAV (по умолчанию: 44100)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Без анимаций и лишнего вывода")

    args = parser.parse_args()

    print_splash(args.quiet)
    check_dependencies()

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source = detect_source(args.url)

    if source == "spotify":
        handle_spotify(args.url, output_dir, args.name, args.fmt, args.rate, args.quiet)
    else:
        handle_direct(args.url, output_dir, args.name, args.fmt, args.rate, args.quiet)

    if not args.quiet:
        print()


if __name__ == "__main__":
    main()
