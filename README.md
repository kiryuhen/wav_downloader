# download.py

CLI-утилита для загрузки аудио с **YouTube**, **SoundCloud** и **Spotify** в формате WAV или MP3.

Spotify-ссылки (треки, альбомы, плейлисты) автоматически матчатся с YouTube и скачиваются.

## Требования

- Python 3.10+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)

```bash
brew install yt-dlp ffmpeg
```

## Настройка Spotify (одноразово)

1. Зайди на [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Создай приложение (имя любое, Redirect URI: `http://localhost`)
3. Открой `download.py` и заполни ключи в начале файла:

```python
SPOTIFY_CLIENT_ID = "твой_client_id"
SPOTIFY_CLIENT_SECRET = "твой_client_secret"
```

YouTube и SoundCloud работают без настройки.

## Использование

```bash
python3 download.py "URL"
```

> **Важно:** всегда оборачивай URL в кавычки — zsh интерпретирует `?` как wildcard.

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
| `-n`, `--name` | Имя файла без расширения (один трек) | название трека |
| `-r`, `--rate` | Sample rate для WAV: 22050 / 44100 / 48000 / 96000 | 44100 |
| `-q`, `--quiet` | Без анимаций и лишнего вывода | выключено |

### Примеры

```bash
# YouTube → WAV
python3 download.py "https://youtu.be/dQw4w9WgXcQ"

# SoundCloud → MP3
python3 download.py "https://soundcloud.com/artist/track" -f mp3

# Spotify трек → WAV 48kHz
python3 download.py "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh" -r 48000

# Spotify плейлист → MP3 в папку
python3 download.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M" -f mp3 -o ~/Music

# Spotify альбом
python3 download.py "https://open.spotify.com/album/ID" -f wav

# Без анимаций
python3 download.py "URL" -q
```

## Установка как глобальная команда

```bash
chmod +x download.py
cp download.py /usr/local/bin/dl
```

```bash
dl "https://open.spotify.com/playlist/ID" -f mp3 -o ~/Music
```

## Лицензия

MIT
