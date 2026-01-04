# IMDB to Plex Watchlist Sync

Automatically sync your IMDB watchlist to Plex, but only add movies/shows that aren't available on your streaming services.

## Features

- 🎬 Syncs IMDB watchlist to Plex automatically
- 🔍 Checks streaming availability before adding
- 🌍 Supports multiple regions and streaming services
- 🖥️ Web UI for easy configuration
- 🐳 Docker container for easy deployment
- ⏰ Automatic syncing every 6 hours

## Prerequisites

You'll need:
- **TMDB API Key** (free): https://www.themoviedb.org/settings/api
- **Plex Token**: Settings → Account → "Get Token"
- **IMDB Watchlist URL**: Copy from your IMDB watchlist page

## Quick Start

1. Clone this repository:
```bash
git clone https://github.com/aaronhorv/imdb-plex-sync.git
cd imdb-plex-sync
```

2. Start the container:
```bash
docker-compose up -d
```

3. Open http://localhost:5000 in your browser

4. Configure your settings:
   - Add your IMDB watchlist URL
   - Add your Plex token
   - Add your TMDB API key
   - Select your region
   - Select your streaming services

5. Click "Sync Now" to test!

## Configuration

The web UI allows you to configure:
- IMDB watchlist URL
- Plex authentication token
- TMDB API key
- Your region (for streaming availability)
- Your streaming services (Netflix, Apple TV+, HBO Max, etc.)

## How It Works

1. Fetches your IMDB watchlist via RSS feed
2. For each item, checks if it's available on your selected streaming services using TMDB
3. If NOT available on streaming, adds it to your Plex watchlist
4. Runs automatically every 6 hours (configurable)

## Manual Sync

You can trigger a manual sync anytime through the web UI by clicking "Sync Now".

## Logs

View sync activity and any errors in the "Logs" tab of the web UI.

## Troubleshooting

**Container won't start:**
- Make sure port 5000 isn't already in use
- Check Docker logs: `docker logs imdb-plex-sync`

**Items not syncing:**
- Verify your API keys are correct
- Check the logs for specific errors
- Make sure your IMDB watchlist is public

## License

MIT License - feel free to modify and use as you wish!

## Contributing

Pull requests welcome! Feel free to open issues for bugs or feature requests.
