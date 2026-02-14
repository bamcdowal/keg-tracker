# Keg Tracker

A self-hosted web app for tracking homebrew kegs. Built with FastAPI, SQLite, and vanilla JavaScript.

## Features

- Track keg status (empty, full, on tap)
- Sync batches from [Brewfather](https://brewfather.app)
- Assign batches to kegs with conditioning day counters
- Usage stats and event history
- Grid and board views
- Add and remove kegs

## Requirements

- Docker and Docker Compose

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/bamcdowal/keg-tracker.git
   cd keg-tracker
   ```

2. Create a `.env` file with your Brewfather API credentials:
   ```
   BREWFATHER_USER_ID=your_user_id
   BREWFATHER_API_KEY=your_api_key
   ```

3. Start the app:
   ```bash
   docker compose up -d --build
   ```

4. Open `http://localhost:5000` in your browser.

## Updating

SSH into the server, then:

```bash
cd /path/to/keg-tracker
git pull
docker compose up -d --build
```

The `keg-data` volume persists your database across restarts so no data is lost.
