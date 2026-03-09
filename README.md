# download.py

CLI-утилита для загрузки аудио с YouTube и SoundCloud в формате WAV или MP3.

## Требования

- Python 3.10+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)

### Установка зависимостей (macOS)

```bash
brew install yt-dlp ffmpeg
```

## Использование

```bash
python3 download.py "URL"
```

> **Важно:** всегда оборачивай URL в кавычки — zsh интерпретирует `?` как wildcard.

Источник (YouTube / SoundCloud) определяется автоматически по URL.

### Форматы

| Формат | Флаг | Описание |
|--------|------|----------|
| WAV | `-f wav` (по умолчанию) | Lossless, stereo, настраиваемый sample rate |
| MP3 | `-f mp3` | 320kbps CBR, stereo |

### Все параметры

| Флаг | Описание | По умолчанию |
|------|----------|--------------|
| `-f`, `--format` | `wav` или `mp3` | `wav` |
| `-o`, `--output` | Директория для сохранения | `.` (текущая) |
| `-n`, `--name` | Имя файла (без расширения) | название трека |
| `-r`, `--rate` | Sample rate для WAV: 22050, 44100, 48000, 96000 | 44100 |
| `-q`, `--quiet` | Минимальный вывод | выключено |

### Примеры

```bash
# YouTube → WAV (по умолчанию)
python3 download.py "https://youtu.be/dQw4w9WgXcQ"

# SoundCloud → MP3 320kbps
python3 download.py "https://soundcloud.com/artist/track" -f mp3

# WAV 48kHz в конкретную папку
python3 download.py "https://youtu.be/dQw4w9WgXcQ" -f wav -r 48000 -o ~/Music

# Кастомное имя файла
python3 download.py "https://soundcloud.com/artist/track" -n mysong -f mp3

# Тихий режим
python3 download.py "URL" -q
```

## Установка как глобальная команда

```bash
chmod +x download.py
cp download.py /usr/local/bin/dl
```

После этого:

```bash
dl "https://youtu.be/VIDEO_ID" -f mp3
dl "https://soundcloud.com/artist/track"
```

## Как это работает

1. Автодетект источника по URL
2. `yt-dlp` получает метаданные (название, длительность)
3. `yt-dlp` скачивает лучший аудиопоток
4. `ffmpeg` конвертирует в WAV (lossless, stereo) или MP3 (320kbps CBR)

## Лицензия

MIT
