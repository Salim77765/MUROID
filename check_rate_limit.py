"""
Check if you're currently rate-limited by YouTube
"""
import yt_dlp
import os
import time

cookie_file = os.path.join(os.path.dirname(__file__), 'youtube_cookies.txt')

print("=" * 60)
print("YouTube Rate Limit Check")
print("=" * 60)
print(f"Cookie file: {cookie_file}")
print(f"Exists: {os.path.exists(cookie_file)}")
print(f"Size: {os.path.getsize(cookie_file) if os.path.exists(cookie_file) else 0} bytes")
print("=" * 60)

# Simple test video
test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video

ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'cookiefile': cookie_file,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
}

print("\nAttempting to fetch video info...")
print("(This will show if you're rate-limited)\n")

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(test_url, download=False)
        print("✅ SUCCESS! Not rate-limited.")
        print(f"   Video: {info.get('title')}")
        print(f"   Duration: {info.get('duration')}s")
        
except Exception as e:
    error_msg = str(e)
    if "429" in error_msg or "Too Many Requests" in error_msg:
        print("❌ RATE LIMITED!")
        print("\nYou've exceeded YouTube's request limit.")
        print("\nSolutions:")
        print("1. Wait 30-60 minutes before trying again")
        print("2. Your IP has been temporarily blocked")
        print("3. The cookies are working, but you've made too many requests")
        print("\nRate limits:")
        print("  - Guest: ~300 videos/hour")
        print("  - With cookies: ~2000 videos/hour")
        print("\nRecommendation: Wait before testing again.")
    elif "Sign in" in error_msg or "bot" in error_msg:
        print("❌ COOKIE ISSUE!")
        print("\nCookies may be expired or invalid.")
        print("Re-export cookies using the incognito method.")
    else:
        print(f"❌ ERROR: {error_msg}")

print("\n" + "=" * 60)
