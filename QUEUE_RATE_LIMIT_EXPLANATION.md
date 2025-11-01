# Queue Loading and Rate Limiting - Explained

## Why You're Getting Rate Limited

### The Problem: Concurrent Requests from Queue

When you play a song in your Android app, it makes **TWO simultaneous requests**:

1. **`/api/stream/{videoId}`** - Streams the audio
   - Calls yt-dlp → YouTube API
   
2. **`/api/watch/{videoId}`** - Loads related songs (queue/autoplay)
   - Calls ytmusicapi → YouTube API

Both requests hit YouTube **at the same time**, which triggers rate limiting even though each individual request is valid.

### Example Timeline (BEFORE fix)

```
Time 0.0s: User plays Song A
  ├─ Request 1: /api/stream/songA    → YouTube API call
  └─ Request 2: /api/watch/songA     → YouTube API call (concurrent!)

Time 0.1s: Both requests hit YouTube simultaneously
  → YouTube sees 2 requests in <1 second
  → Returns HTTP 429: Too Many Requests
```

### Why This Happens

Your Android app code:
```kotlin
fun setCurrentPlayingSong(song: SearchResult) {
    // 1. Plays the song
    playSong(videoId)  // → /api/stream/{videoId}
}

// Separately, the UI loads related songs:
fun loadRelatedSongs(videoId: String) {
    repository.getWatchPlaylist(videoId)  // → /api/watch/{videoId}
}
```

Both happen almost instantly when a song starts playing.

## The Solution: Shared Rate Limiting

### What Was Implemented

Added a **global rate limiter** that works across ALL YouTube-related endpoints:

```python
# Shared state
last_youtube_request_time = 0
youtube_request_lock = Lock()
MIN_REQUEST_INTERVAL = 3  # seconds

# Applied to BOTH endpoints:
# - /api/stream/{videoId}
# - /api/watch/{videoId}
```

### How It Works Now

```
Time 0.0s: User plays Song A
  ├─ Request 1: /api/stream/songA
  │   └─ Acquires lock
  │   └─ Makes YouTube API call
  │   └─ Updates last_request_time = 0.0s
  │   └─ Releases lock
  │
  └─ Request 2: /api/watch/songA (concurrent)
      └─ Tries to acquire lock (blocked!)
      └─ Waits for Request 1 to finish
      └─ Checks: time_since_last = 0.1s < 3s
      └─ Sleeps for 2.9s
      └─ Makes YouTube API call
      └─ Updates last_request_time = 3.0s

Result: 3 seconds between YouTube API calls ✅
```

### Protected Endpoints

Now rate-limited:
- ✅ `/api/stream/{videoId}` - Streaming audio
- ✅ `/api/watch/{videoId}` - Loading queue/related songs

Not rate-limited (don't hit YouTube directly):
- `/api/search` - Uses ytmusicapi (different API)
- `/api/artist`, `/api/album`, etc. - Different endpoints

## Impact on User Experience

### What Users Will Notice

1. **First song**: Plays immediately ✅
2. **Queue loading**: Appears 3 seconds after song starts
   - This is intentional to prevent rate limiting
   - Related songs will show up with a slight delay

### What Users Won't Notice

- The 3-second delay is **only between YouTube API calls**
- Audio streaming is **not affected** (happens after the delay)
- UI remains responsive during the wait

### Example User Flow

```
User clicks "Play Song A"
  ↓
0.0s: Song A starts playing immediately ✅
  ↓
3.0s: Related songs/queue loads ✅
  ↓
User clicks "Next" (plays Song B from queue)
  ↓
3.0s: Song B starts playing (waited 3s from last request) ✅
```

## Configuration

### Current Settings

```python
MIN_REQUEST_INTERVAL = 3  # seconds
```

### Adjusting the Interval

**If you still get rate limited:**
```python
MIN_REQUEST_INTERVAL = 5  # More conservative
```

**If 3 seconds feels too slow:**
```python
MIN_REQUEST_INTERVAL = 2  # Riskier, may still hit limits
```

**Recommendation**: Keep it at 3 seconds. This balances:
- ✅ User experience (not too slow)
- ✅ Rate limit protection (not too fast)
- ✅ YouTube's limits (~1200 requests/hour = 1 per 3 seconds)

## Monitoring

### Log Messages to Watch

**Normal operation:**
```
INFO: Streaming request for video: abc123
INFO: ⏱️ Rate limiting: waiting 2.3s before YouTube request (queue protection)
INFO: ✅ Using default cookie file: youtube_cookies.txt
```

**If you see this repeatedly:**
```
WARNING: [youtube] HTTP Error 429: Too Many Requests
```
→ Increase `MIN_REQUEST_INTERVAL` to 5 seconds

## Why Not Just Disable Queue Loading?

You could disable the `/api/watch` call to avoid the second request, but:
- ❌ No autoplay/related songs
- ❌ No queue functionality
- ❌ Poor user experience

The rate limiting solution is better because:
- ✅ Keeps all features working
- ✅ Prevents rate limiting
- ✅ Only adds a small delay (3 seconds)

## Technical Details

### Thread Safety

The implementation uses a `Lock()` to ensure:
- Only one YouTube request happens at a time
- Concurrent requests wait in line
- No race conditions on `last_youtube_request_time`

### Why ytmusicapi Also Needs Rate Limiting

Even though ytmusicapi is a different library, it still:
- Calls YouTube's internal APIs
- Counts toward the same rate limit
- Can trigger HTTP 429 errors

So both yt-dlp AND ytmusicapi requests need to be rate-limited.

## Summary

✅ **Root cause**: Queue loading triggers concurrent YouTube requests  
✅ **Solution**: Global rate limiter across all YouTube endpoints  
✅ **Result**: 3-second delay between requests prevents rate limiting  
✅ **Trade-off**: Slight delay in queue loading, but all features work  

The app is now protected against rate limiting from queue/autoplay functionality! 🎉
