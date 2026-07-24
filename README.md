# VideoGrabberBot

A Telegram bot for downloading videos and audio from YouTube with format selection options.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.13%2B-blue" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/framework-aiogram-blue" alt="Aiogram">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT">
</p>

## Disclaimer

**This project is a personal educational initiative, created solely for learning purposes and is not intended for commercial use.** It was developed to practice modern Python development techniques, asynchronous programming, and Telegram API interactions. Please respect copyright laws and platforms' terms of service when using this software.

## Features

- **Video Downloads**: Get videos from YouTube in multiple formats:
  - SD (480p)
  - HD (720p)
  - Full HD (1080p)
  - Original (Maximum available quality)
- **Audio Extraction**: Extract high-quality MP3 (320kbps) audio from videos
- **Access Control**: Restrict bot usage through invitation links or admin approval
- **Queue System**: Asynchronous download queue for handling multiple requests
- **Error Handling**: Comprehensive error handling with admin notifications
- **Modern Architecture**: Built with asyncio, aiogram, and yt-dlp
- **File Size Limit**: Maximum 50MB per file (Telegram Bot API limitation)

## How It Works

1. **Send a YouTube link** to the bot
2. **Choose a format** from the provided options
3. **Wait for download** to complete
4. **Receive the file** directly in your Telegram chat (up to 50MB)

**Note**: For videos that exceed 50MB, choose a lower quality format (SD or HD).

## Quick Start

### Requirements

- Python 3.13+
- Telegram Bot API token (from [BotFather](https://t.me/botfather))
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AABur/VideoGrabberBot.git
   cd VideoGrabberBot
   ```

2. **Initialize the project**:
   ```bash
   make init
   ```

3. **Configure the bot**:
   Edit the `.env` file with your tokens:
   ```
   TELEGRAM_TOKEN=your_telegram_token
   ADMIN_USER_ID=your_telegram_user_id
   ```

4. **Run the bot**:
   ```bash
   make run
   ```

## Docker Deployment

If you prefer Docker:

1. **Clone and configure**:
   ```bash
   git clone https://github.com/AABur/VideoGrabberBot.git
   cd VideoGrabberBot
   ```

2. **Run with Docker**:
   ```bash
   make docker-start
   ```
   This will create a `.env` file from `.env.example` template. Edit it with your tokens.

3. **Stop when needed**:
   ```bash
   make docker-stop
   ```

## Technologies

- [aiogram](https://docs.aiogram.dev/) - Modern Telegram Bot framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Powerful YouTube downloader
- [aiosqlite](https://aiosqlite.omnilib.dev/) - Async SQLite database
- [loguru](https://loguru.readthedocs.io/) - Advanced logging
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

## Development

Interested in contributing? Check out [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding guidelines, and contribution workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
