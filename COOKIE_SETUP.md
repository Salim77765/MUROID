# YouTube Cookie Setup Guide

YouTube is blocking requests without authentication. You need to provide cookies to fix this.

## Option 1: Local Development (Easiest)

Set environment variable:
```bash
USE_BROWSER_COOKIES=true
```

This will use cookies directly from your Chrome browser.

## Option 2: Production Deployment (Recommended)

### Step 1: Export YouTube Cookies (IMPORTANT - Follow Exactly)

⚠️ **WARNING**: YouTube rotates cookies frequently. Follow this exact process to avoid rotation:

1. **Install a browser extension:**
   - Chrome: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. **Export cookies using incognito/private window:**
   - Open a **NEW incognito/private browsing window**
   - Log into YouTube (consider using a throwaway account - see warning below)
   - In the **SAME tab**, navigate to: `https://www.youtube.com/robots.txt`
   - Click the cookie extension icon
   - Export cookies for `youtube.com`
   - Save as `youtube_cookies.txt`
   - **IMMEDIATELY close the incognito window** (don't browse anywhere else)

3. **Why this matters:**
   - This prevents YouTube from rotating your cookies
   - Cookies exported from regular browsing sessions expire quickly
   - The `/robots.txt` page prevents cookie rotation

### Step 2: Upload Cookie File to Deployment

**For Render/Railway/Similar:**

1. Create a `cookies` directory in your backend:
   ```bash
   mkdir -p backend/cookies
   ```

2. Copy your `youtube_cookies.txt` to `backend/cookies/`

3. Add to `.gitignore`:
   ```
   backend/cookies/youtube_cookies.txt
   ```

4. Upload the file manually to your deployment platform or use their file upload feature

5. Set environment variable:
   ```
   YOUTUBE_COOKIE_FILE=/app/backend/cookies/youtube_cookies.txt
   ```
   
   (Adjust path based on your deployment structure)

### Step 3: Alternative - Use Secrets/Volume

Some platforms support secret files or persistent volumes. Check your platform's documentation for:
- Render: Use "Secret Files"
- Railway: Use "Volumes"
- Heroku: Use buildpacks or config vars (not recommended for large files)

## Cookie Priority

The app checks for cookies in this order:

1. **`USE_BROWSER_COOKIES=true`** - Uses Chrome browser (local dev only)
2. **`YOUTUBE_COOKIE_FILE=/path/to/cookies.txt`** - Uses cookie file path (recommended for production)
3. **`YOUTUBE_COOKIES=<content>`** - Uses cookie content from env var (legacy, causes deployment issues)

## Troubleshooting

### Error: "Sign in to confirm you're not a bot"
- Your cookies are missing or expired
- Re-export cookies from a logged-in YouTube session

### Error: "HTTP Error 429: Too Many Requests"
- YouTube is rate-limiting you
- The `sleep_interval` settings should help
- Make sure cookies are properly loaded

### Error: "exec /bin/bash: argument list too long"
- Don't use `YOUTUBE_COOKIES` environment variable
- Use `YOUTUBE_COOKIE_FILE` instead with a file path

## Important Warnings & Rate Limits

### Account Ban Risk
⚠️ **Using your YouTube account with yt-dlp may result in temporary or permanent bans.**
- Use a throwaway/secondary account
- Don't use your primary Google account
- Be mindful of request rates

### Rate Limits (per hour)
- **Without cookies (guest)**: ~300 videos/hour (~1000 requests/hour)
- **With account cookies**: ~2000 videos/hour (~4000 requests/hour)
- **Recommended delay**: 5-10 seconds between downloads

The app is configured with:
- `sleep_interval: 5` seconds
- `max_sleep_interval: 10` seconds

## Security Notes

- **Never commit cookie files to git**
- Cookies contain authentication tokens
- Rotate cookies periodically (re-export every few weeks)
- Use environment-specific cookies (don't share production cookies)
- Consider using a throwaway YouTube account
