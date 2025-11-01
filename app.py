from flask import Flask, jsonify, request
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp
import logging
import time
import os
from threading import Lock

app = Flask(__name__)
CORS(app)

# Initialize YTMusic
ytmusic = YTMusic()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting for YouTube requests
# Only needed in production (Render) due to shared IP and higher scrutiny
last_youtube_request_time = 0
youtube_request_lock = Lock()
# Check if running in production (Render sets PORT env var)
IS_PRODUCTION = os.environ.get('PORT') is not None
MIN_REQUEST_INTERVAL = 10 if IS_PRODUCTION else 0  # 10s in production (increased from 3s), 0s locally

# Log startup mode
if IS_PRODUCTION:
    logger.info(f"🚀 Running in PRODUCTION mode - Rate limiting ENABLED ({MIN_REQUEST_INTERVAL}s interval)")
else:
    logger.info("💻 Running in LOCAL mode - Rate limiting DISABLED")

@app.route('/api/search', methods=['GET'])
def search():
    """Search for songs, albums, or artists"""
    try:
        query = request.args.get('query', '')
        filter_type = request.args.get('filter', None)
        limit = int(request.args.get('limit', 20))
        
        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        results = ytmusic.search(query, filter=filter_type, limit=limit)
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/song/<video_id>', methods=['GET'])
def get_song(video_id):
    """Get song details and streaming URL"""
    try:
        song_info = ytmusic.get_song(video_id)
        return jsonify({'song': song_info})
    except Exception as e:
        logger.error(f"Get song error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream/<video_id>', methods=['GET'])
def stream_audio(video_id):
    """Download and stream audio directly from backend"""
    global last_youtube_request_time
    
    try:
        import requests
        from flask import Response
        
        logger.info(f"Streaming request for video: {video_id}")
        
        # Rate limiting: ensure minimum time between requests
        # This blocks ALL concurrent requests to prevent rate limiting
        with youtube_request_lock:
            current_time = time.time()
            time_since_last_request = current_time - last_youtube_request_time
            
            if time_since_last_request < MIN_REQUEST_INTERVAL:
                wait_time = MIN_REQUEST_INTERVAL - time_since_last_request
                logger.info(f"⏱️ Rate limiting: waiting {wait_time:.1f}s before YouTube request (queue protection)")
                time.sleep(wait_time)
            
            # Update timestamp BEFORE releasing the lock to ensure next request waits
            last_youtube_request_time = time.time()
        
        # Configure yt-dlp to get audio URL
        import os
        import tempfile

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False,  # Show errors for debugging
            'no_warnings': False,
            'extract_flat': False,
            'sleep_interval': 5,                 # Sleep between requests (recommended: 5-10s)
            'max_sleep_interval': 10,            # Maximum sleep interval
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        
        # Cookie handling priority:
        # 1. Use browser cookies in local dev (if USE_BROWSER_COOKIES=true)
        # 2. Use cookie file path (if YOUTUBE_COOKIE_FILE is set)
        # 3. Use cookie content from env var (if YOUTUBE_COOKIES is set) - legacy support
        
        cookie_filepath = None
        
        if os.environ.get('USE_BROWSER_COOKIES') == 'true':
            # Local development: use Chrome browser cookies directly
            ydl_opts['cookiesfrombrowser'] = ('chrome',)
            logger.info("Using cookies from Chrome browser")
        elif os.environ.get('YOUTUBE_COOKIE_FILE'):
            # Production: use cookie file path from environment variable
            cookie_file = os.environ.get('YOUTUBE_COOKIE_FILE')
            if os.path.exists(cookie_file):
                ydl_opts['cookiefile'] = cookie_file
                logger.info(f"Using cookie file: {cookie_file}")
            else:
                logger.warning(f"Cookie file not found: {cookie_file}")
        elif os.environ.get('YOUTUBE_COOKIES'):
            # Legacy: use cookie content from environment variable
            youtube_cookies = os.environ.get('YOUTUBE_COOKIES')
            try:
                # Create a temporary file to store cookies
                fd, cookie_filepath = tempfile.mkstemp(suffix='.txt')
                with os.fdopen(fd, 'w') as tmp:
                    tmp.write(youtube_cookies)
                ydl_opts['cookiefile'] = cookie_filepath
                logger.info("Using YouTube cookies from environment variable.")
            except Exception as e:
                logger.error(f"Error creating temporary cookie file: {e}")
                cookie_filepath = None
        else:
            # Fallback: check for youtube_cookies.txt in the same directory
            default_cookie_file = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')
            if os.path.exists(default_cookie_file):
                ydl_opts['cookiefile'] = default_cookie_file
                logger.info(f"✅ Using default cookie file: {default_cookie_file}")
                logger.info(f"Cookie file size: {os.path.getsize(default_cookie_file)} bytes")
            else:
                logger.warning("⚠️ No cookies found. YouTube may block requests.")
        
        # Log final yt-dlp configuration
        logger.info(f"yt-dlp config: format={ydl_opts.get('format')}, "
                   f"sleep={ydl_opts.get('sleep_interval')}-{ydl_opts.get('max_sleep_interval')}s, "
                   f"cookies={'YES' if 'cookiefile' in ydl_opts or 'cookiesfrombrowser' in ydl_opts else 'NO'}")
        
        youtube_url = f'https://www.youtube.com/watch?v={video_id}'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            # Get the audio URL - yt-dlp already selected the best format
            audio_url = info.get('url')
            
            # Validate URL - reject image URLs
            if audio_url and ('i.ytimg.com' in audio_url or 'storyboard' in audio_url):
                logger.warning(f"Rejecting image URL: {audio_url[:100]}")
                audio_url = None
            
            # If URL not in main info, check requested_formats or formats
            if not audio_url:
                if 'requested_formats' in info and len(info['requested_formats']) > 0:
                    # Get audio from requested formats
                    for fmt in info['requested_formats']:
                        if fmt.get('acodec') != 'none':
                            url = fmt.get('url')
                            if url and 'i.ytimg.com' not in url:
                                audio_url = url
                                logger.info(f"Using requested format: {fmt.get('format_id')}")
                                break
                
                # Fallback to formats list
                if not audio_url and 'formats' in info:
                    for fmt in info['formats']:
                        if (fmt.get('acodec') != 'none' and 
                            'url' in fmt and 
                            'i.ytimg.com' not in fmt.get('url', '')):
                            audio_url = fmt.get('url')
                            logger.info(f"Using format: {fmt.get('format_id')} - {fmt.get('ext')}")
                            break
            
            if not audio_url:
                logger.error("No valid audio URL found - signature extraction may have failed")
                logger.error("Please update yt-dlp: pip install --upgrade yt-dlp")
                return jsonify({'error': 'No audio URL found. yt-dlp may need updating.'}), 404
            
            logger.info(f"Proxying audio from: {audio_url[:100]}...")
            
            # Stream the audio through our backend (proxy)
            def generate():
                try:
                    with requests.get(audio_url, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                yield chunk
                except Exception as e:
                    logger.error(f"Error while streaming: {str(e)}")
                    raise
            
            return Response(
                generate(),
                mimetype='audio/webm',
                headers={
                    'Content-Type': 'audio/webm',
                    'Accept-Ranges': 'bytes',
                    'Cache-Control': 'no-cache'
                }
            )
                
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cookie_filepath and os.path.exists(cookie_filepath):
            try:
                os.remove(cookie_filepath)
                logger.info(f"Removed temporary cookie file: {cookie_filepath}")
            except Exception as e:
                logger.error(f"Error removing temporary cookie file {cookie_filepath}: {e}")

@app.route('/api/artist/<browse_id>', methods=['GET'])
def get_artist(browse_id):
    """Get artist information"""
    try:
        artist_info = ytmusic.get_artist(browse_id)
        return jsonify({'artist': artist_info})
    except Exception as e:
        logger.error(f"Get artist error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/album/<browse_id>', methods=['GET'])
def get_album(browse_id):
    """Get album information"""
    try:
        album_info = ytmusic.get_album(browse_id)
        return jsonify({'album': album_info})
    except Exception as e:
        logger.error(f"Get album error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charts', methods=['GET'])
def get_charts():
    """Get music charts"""
    try:
        country = request.args.get('country', 'US')
        charts = ytmusic.get_charts(country=country)
        return jsonify({'charts': charts})
    except Exception as e:
        logger.error(f"Get charts error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/home', methods=['GET'])
def get_home():
    """Get home feed recommendations"""
    try:
        home = ytmusic.get_home()
        return jsonify({'home': home})
    except Exception as e:
        logger.error(f"Get home error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/watch/<video_id>', methods=['GET'])
def get_watch_playlist(video_id):
    """Get watch playlist (similar songs)"""
    global last_youtube_request_time
    
    try:
        logger.info(f"Fetching watch playlist for video: {video_id}")
        
        # Rate limiting: ensure minimum time between YouTube API requests
        with youtube_request_lock:
            current_time = time.time()
            time_since_last_request = current_time - last_youtube_request_time
            
            if time_since_last_request < MIN_REQUEST_INTERVAL:
                wait_time = MIN_REQUEST_INTERVAL - time_since_last_request
                logger.info(f"⏱️ Rate limiting: waiting {wait_time:.1f}s before watch playlist request")
                time.sleep(wait_time)
            
            last_youtube_request_time = time.time()
        
        # Add retry mechanism for ytmusicapi call
        max_retries = 3
        retry_count = 0
        watch_playlist = None
        
        while retry_count < max_retries:
            try:
                watch_playlist = ytmusic.get_watch_playlist(videoId=video_id, limit=25)
                break
            except Exception as retry_error:
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} failed: {str(retry_error)}")
                if retry_count >= max_retries:
                    raise
        
        # If we still don't have a watch playlist, return a fallback empty response
        if not watch_playlist:
            logger.error("Failed to get watch playlist after retries")
            return jsonify({
                'playlist': {
                    'tracks': [],
                    'lyrics': None
                }
            })
        
        # Extract and transform tracks to match Android model
        raw_tracks = watch_playlist.get('tracks', [])
        logger.info(f"Found {len(raw_tracks)} related tracks")
        
        # Transform tracks to match SearchResult model
        transformed_tracks = []
        for track in raw_tracks:
            try:
                # Get videoId - try multiple possible fields
                video_id = track.get('videoId') or track.get('id')
                if not video_id:
                    logger.warning(f"Skipping track without videoId: {track.get('title')}")
                    continue
                    
                transformed_track = {
                    'videoId': video_id,
                    'title': track.get('title', 'Unknown'),
                    'artists': track.get('artists', []),
                    'album': track.get('album'),
                    'duration': track.get('length', '0:00'),  # Map 'length' to 'duration'
                    'thumbnails': track.get('thumbnail', []),  # Map 'thumbnail' to 'thumbnails'
                    'category': 'song',
                    'resultType': 'song',
                    'browseId': track.get('album', {}).get('id') if track.get('album') else None,
                    'year': track.get('year')
                }
                transformed_tracks.append(transformed_track)
            except Exception as track_error:
                logger.error(f"Error transforming track: {track_error}")
                continue
        
        logger.info(f"Transformed {len(transformed_tracks)} tracks")
        
        # Return a simplified response to avoid potential serialization issues
        return jsonify({
            'playlist': {
                'tracks': transformed_tracks,
                'lyrics': watch_playlist.get('lyrics')
            }
        })
    except Exception as e:
        logger.error(f"Get watch playlist error: {str(e)}")
        logger.exception(e)
        # Return a valid response even on error to prevent client crashes
        return jsonify({
            'playlist': {
                'tracks': [],
                'lyrics': None
            }
        }), 200  # Return 200 with empty data instead of 500

@app.route('/api/lyrics/<browse_id>', methods=['GET'])
def get_lyrics(browse_id):
    """Get song lyrics"""
    try:
        lyrics = ytmusic.get_lyrics(browse_id)
        return jsonify({'lyrics': lyrics})
    except Exception as e:
        logger.error(f"Get lyrics error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    # Get port from environment variable (for Render compatibility)
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
