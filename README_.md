# yt2wav

CLI-утилита для загрузки аудио с YouTube в формате WAV.

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
python3 download.py "https://youtube.com/watch?v=VIDEO_ID"
```

> **Важно:** всегда оборачивай URL в кавычки — zsh интерпретирует `?` как wildcard.

### Параметры

| Флаг | Описание | По умолчанию |
|------|----------|--------------|
| `-o`, `--output` | Директория для сохранения | `.` (текущая) |
| `-n`, `--name` | Имя выходного файла (без `.wav`) | название видео |
| `-r`, `--rate` | Sample rate: 22050, 44100, 48000, 96000 | 44100 |
| `-q`, `--quiet` | Минимальный вывод | выключено |

### Примеры

```bash
# Базовая загрузка
python3 download.py "https://youtu.be/dQw4w9WgXcQ"

# В конкретную папку с кастомным именем
python3 download.py "https://youtu.be/dQw4w9WgXcQ" -o ~/Music -n mysong

# Sample rate 48kHz
python3 download.py "https://youtu.be/dQw4w9WgXcQ" -r 48000

# Тихий режим
python3 download.py "https://youtu.be/dQw4w9WgXcQ" -q
```

## Установка как глобальная команда

```bash
chmod +x download.py
cp download.py /usr/local/bin/yt2wav
```

После этого можно вызывать из любой директории:

```bash
yt2wav "https://youtu.be/VIDEO_ID"
```

## Как это работает

1. `yt-dlp` получает метаданные видео (название, длительность)
2. `yt-dlp` скачивает лучший доступный аудиопоток
3. `ffmpeg` конвертирует в WAV (стерео, выбранный sample rate)

## Лицензия

MIT
