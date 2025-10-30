
# YTMusic API Backend

This is the backend API service for the Android Music Application using ytmusicapi.

## Setup

1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python app.py
   ```

The server will run on `http://localhost:5000`

## API Endpoints

- `GET /api/search?query=<search_term>&filter=<songs|albums|artists>&limit=<number>` - Search for music
- `GET /api/song/<video_id>` - Get song details
- `GET /api/artist/<browse_id>` - Get artist information
- `GET /api/album/<browse_id>` - Get album information
- `GET /api/charts?country=<country_code>` - Get music charts
- `GET /api/home` - Get home feed recommendations
- `GET /api/watch/<video_id>` - Get similar songs playlist
- `GET /api/lyrics/<browse_id>` - Get song lyrics
- `GET /health` - Health check

## Note

Make sure to update the `BASE_URL` in the Android app to point to your backend server IP address.

# MUROID
0e0211b0bccd6a1b4ee3eb373208a40932ec13e4
