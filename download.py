#!/usr/bin/env python3
"""yt2wav — CLI утилита для загрузки аудио с YouTube в формате WAV."""

import argparse
import sys
import os
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


def get_video_info(url: str) -> dict | None:
    """Получает метаданные видео."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-download", "--print", "%(title)s\n%(duration)s\n%(id)s", url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        lines = result.stdout.strip().split("\n")
        return {"title": lines[0], "duration": int(lines[1] or 0), "id": lines[2]}
    except Exception:
        return None


def sanitize_filename(name: str) -> str:
    """Убирает недопустимые символы из имени файла."""
    forbidden = '<>:"/\\|?*'
    for ch in forbidden:
        name = name.replace(ch, "_")
    return name.strip(". ")


def download_wav(url: str, output_dir: Path, filename: str | None = None, sample_rate: int = 44100, quiet: bool = False):
    """Скачивает аудио с YouTube и конвертирует в WAV."""
    info = get_video_info(url)
    if not info:
        print("❌ Не удалось получить информацию о видео. Проверь ссылку.")
        sys.exit(1)

    if not quiet:
        duration_min = info["duration"] // 60
        duration_sec = info["duration"] % 60
        print(f"🎵 {info['title']}")
        print(f"⏱  {duration_min}:{duration_sec:02d}")

    if filename:
        stem = Path(filename).stem
    else:
        stem = sanitize_filename(info["title"])

    output_path = output_dir / f"{stem}.wav"

    # Если файл уже существует — спрашиваем
    if output_path.exists():
        answer = input(f"⚠️  Файл {output_path.name} уже существует. Перезаписать? [y/N] ").strip().lower()
        if answer != "y":
            print("Отменено.")
            sys.exit(0)

    cmd = [
        "yt-dlp",
        "-x",                                   # extract audio
        "--audio-format", "wav",                # target format
        "--postprocessor-args",
        f"ffmpeg:-ar {sample_rate} -ac 2",      # sample rate + stereo
        "-o", str(output_dir / f"{stem}.%(ext)s"),
        "--no-playlist",                         # одно видео
        "--no-part",                             # без .part файлов
    ]

    if quiet:
        cmd.append("--quiet")
    else:
        cmd.append("--progress")

    cmd.append(url)

    if not quiet:
        print(f"📥 Загружаю → {output_path.name}")
        print(f"   Sample rate: {sample_rate} Hz, Stereo")
        print()

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("❌ Ошибка при загрузке.")
        sys.exit(1)

    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Готово: {output_path} ({size_mb:.1f} MB)")
    else:
        # yt-dlp мог сохранить с другим расширением — ищем
        candidates = list(output_dir.glob(f"{stem}.*"))
        if candidates:
            print(f"\n✅ Готово: {candidates[0]}")
        else:
            print("⚠️  Файл загружен, но не найден в ожидаемом месте.")


def main():
    parser = argparse.ArgumentParser(
        prog="yt2wav",
        description="Загрузка аудио с YouTube в WAV формате",
        epilog="Примеры:\n"
               "  yt2wav https://youtube.com/watch?v=dQw4w9WgXcQ\n"
               "  yt2wav URL -o ~/Music -n mysong --rate 48000\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="Ссылка на YouTube видео")
    parser.add_argument("-o", "--output", default=".", help="Директория для сохранения (по умолчанию: текущая)")
    parser.add_argument("-n", "--name", default=None, help="Имя выходного файла (без .wav)")
    parser.add_argument("-r", "--rate", type=int, default=44100, choices=[22050, 44100, 48000, 96000],
                        help="Sample rate в Hz (по умолчанию: 44100)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Минимальный вывод")

    args = parser.parse_args()

    check_dependencies()

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    download_wav(
        url=args.url,
        output_dir=output_dir,
        filename=args.name,
        sample_rate=args.rate,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
