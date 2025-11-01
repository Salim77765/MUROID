"""
Quick test script to verify YouTube cookies are working with yt-dlp
"""
import yt_dlp
import os

# Test video ID (the one that was failing)
video_id = "fsiPzT50ZiM"
youtube_url = f'https://www.youtube.com/watch?v={video_id}'

# Get the absolute path to the cookie file
cookie_file = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')

print(f"Testing with video: {video_id}")
print(f"Cookie file: {cookie_file}")
print(f"Cookie file exists: {os.path.exists(cookie_file)}")
print("-" * 60)

ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': False,
    'no_warnings': False,
    'extract_flat': False,
    'cookiefile': cookie_file,
    'sleep_interval': 5,
    'max_sleep_interval': 10,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("Extracting video info...")
        info = ydl.extract_info(youtube_url, download=False)
        
        print("\n" + "=" * 60)
        print("SUCCESS! Video info extracted:")
        print("=" * 60)
        print(f"Title: {info.get('title')}")
        print(f"Duration: {info.get('duration')} seconds")
        print(f"Uploader: {info.get('uploader')}")
        
        # Check for audio URL
        audio_url = info.get('url')
        if audio_url:
            print(f"\nAudio URL found: {audio_url[:100]}...")
        else:
            print("\nNo direct audio URL, checking formats...")
            if 'formats' in info:
                audio_formats = [f for f in info['formats'] if f.get('acodec') != 'none']
                print(f"Found {len(audio_formats)} audio formats")
        
        print("\n✅ Cookies are working correctly!")
        
except Exception as e:
    print("\n" + "=" * 60)
    print("ERROR:")
    print("=" * 60)
    print(str(e))
    print("\n❌ Cookie test failed")
