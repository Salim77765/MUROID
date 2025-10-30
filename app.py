from flask import Flask, jsonify, request
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp
import logging

app = Flask(__name__)
CORS(app)

# Initialize YTMusic
ytmusic = YTMusic()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        import requests
        from flask import Response
        
        logger.info(f"Streaming request for video: {video_id}")
        
        # Configure yt-dlp to get audio URL
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False,  # Show errors for debugging
            'no_warnings': False,
            'extract_flat': False,
        }
        
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
    try:
        logger.info(f"Fetching watch playlist for video: {video_id}")
        
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
