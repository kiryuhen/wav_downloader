#!/usr/bin/env python3
"""download.py — CLI утилита для загрузки аудио с YouTube и SoundCloud в WAV/MP3."""

import argparse
import sys
import subprocess
import shutil
from pathlib import Path


def check_dependencies():
    """Проверяет наличие yt-dlp и ffmpeg."""
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if missing:
        print(f"❌ Не найдены зависимости: {', '.join(missing)}")
        print("\nУстановка:")
        print("  brew install yt-dlp ffmpeg")
        sys.exit(1)


def detect_source(url: str) -> str:
    """Определяет источник по URL."""
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "soundcloud.com" in url:
        return "soundcloud"
    return "unknown"


def get_track_info(url: str) -> dict | None:
    """Получает метаданные трека."""
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


def build_cmd(
    url: str,
    output_dir: Path,
    stem: str,
    fmt: str,
    sample_rate: int,
    quiet: bool,
) -> list[str]:
    """Собирает команду yt-dlp в зависимости от формата."""
    cmd = ["yt-dlp", "-x", "--no-playlist", "--no-part"]

    if fmt == "wav":
        cmd += [
            "--audio-format", "wav",
            "--postprocessor-args", f"ffmpeg:-ar {sample_rate} -ac 2",
        ]
    else:  # mp3
        cmd += [
            "--audio-format", "mp3",
            "--postprocessor-args", "ffmpeg:-b:a 320k -ac 2",
        ]

    cmd += ["-o", str(output_dir / f"{stem}.%(ext)s")]

    if quiet:
        cmd.append("--quiet")
    else:
        cmd.append("--progress")

    cmd.append(url)
    return cmd


def download(
    url: str,
    output_dir: Path,
    filename: str | None = None,
    fmt: str = "wav",
    sample_rate: int = 44100,
    quiet: bool = False,
):
    """Скачивает аудио и конвертирует в нужный формат."""
    source = detect_source(url)
    source_label = {"youtube": "YouTube", "soundcloud": "SoundCloud"}.get(source, "Unknown")

    if source == "unknown":
        print("⚠️  Источник не распознан. Попробую загрузить через yt-dlp...")
        source_label = "URL"

    info = get_track_info(url)
    if not info:
        print("❌ Не удалось получить информацию о треке. Проверь ссылку.")
        sys.exit(1)

    if not quiet:
        duration_min = info["duration"] // 60
        duration_sec = info["duration"] % 60
        print(f"🎵 {info['title']}")
        print(f"📡 {source_label}")
        print(f"⏱  {duration_min}:{duration_sec:02d}")

    stem = sanitize_filename(filename) if filename else sanitize_filename(info["title"])
    ext = fmt
    output_path = output_dir / f"{stem}.{ext}"

    if output_path.exists():
        answer = input(f"⚠️  Файл {output_path.name} уже существует. Перезаписать? [y/N] ").strip().lower()
        if answer != "y":
            print("Отменено.")
            sys.exit(0)

    if not quiet:
        format_info = f"WAV {sample_rate}Hz Stereo" if fmt == "wav" else "MP3 320kbps Stereo"
        print(f"📥 {format_info} → {output_path.name}")
        print()

    cmd = build_cmd(url, output_dir, stem, fmt, sample_rate, quiet)
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("❌ Ошибка при загрузке.")
        sys.exit(1)

    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Готово: {output_path} ({size_mb:.1f} MB)")
    else:
        candidates = list(output_dir.glob(f"{stem}.*"))
        if candidates:
            size_mb = candidates[0].stat().st_size / (1024 * 1024)
            print(f"\n✅ Готово: {candidates[0]} ({size_mb:.1f} MB)")
        else:
            print("⚠️  Файл загружен, но не найден в ожидаемом месте.")


def main():
    parser = argparse.ArgumentParser(
        prog="download",
        description="Загрузка аудио с YouTube / SoundCloud в WAV или MP3",
        epilog="Примеры:\n"
               '  python3 download.py "https://youtube.com/watch?v=dQw4w9WgXcQ"\n'
               '  python3 download.py "https://soundcloud.com/artist/track" -f mp3\n'
               '  python3 download.py URL -f wav -r 48000 -o ~/Music -n mysong\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="Ссылка на YouTube или SoundCloud трек")
    parser.add_argument("-f", "--format", dest="fmt", default="wav", choices=["wav", "mp3"],
                        help="Формат: wav (lossless) или mp3 (320kbps). По умолчанию: wav")
    parser.add_argument("-o", "--output", default=".", help="Директория для сохранения (по умолчанию: текущая)")
    parser.add_argument("-n", "--name", default=None, help="Имя выходного файла (без расширения)")
    parser.add_argument("-r", "--rate", type=int, default=44100, choices=[22050, 44100, 48000, 96000],
                        help="Sample rate для WAV в Hz (по умолчанию: 44100). Игнорируется для MP3")
    parser.add_argument("-q", "--quiet", action="store_true", help="Минимальный вывод")

    args = parser.parse_args()

    check_dependencies()

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    download(
        url=args.url,
        output_dir=output_dir,
        filename=args.name,
        fmt=args.fmt,
        sample_rate=args.rate,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
