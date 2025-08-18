# Google Calendar Integration Setup

This guide walks you through setting up Google Calendar API integration for your MCP server.

## Prerequisites

- Google account with Calendar access
- Google Cloud Platform project (free tier is sufficient)

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project" or select an existing project
3. Give your project a name (e.g., "Daily Agent Calendar")
4. Note your project ID

## Step 2: Enable Google Calendar API

1. In Google Cloud Console, go to **APIs & Services > Library**
2. Search for "Google Calendar API"
3. Click on it and press **Enable**

## Step 3: Create Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (unless you have a Google Workspace)
   - Fill in required fields (App name, User support email, Developer email)
   - Add your email to test users
4. For Application type, choose **Desktop application**
5. Give it a name (e.g., "Daily Agent Calendar Client")
6. Click **Create**

## Step 4: Download Credentials

1. Click the download icon next to your newly created OAuth client
2. Save the JSON file as `google_calendar_credentials.json`
3. Place this file in your MCP server root directory (same level as `.env`)

## Step 5: Update Environment Variables

1. Copy `.env.example` to `.env` if you haven't already:

   ```bash
   cp .env.example .env
   ```

2. Update the Google Calendar credentials path in `.env`:
   ```bash
   GOOGLE_CALENDAR_CREDENTIALS_PATH=./google_calendar_credentials.json
   ```

## Step 6: First Time Authentication

1. Start your MCP server:

   ```bash
   uv run python run.py
   ```

2. The first time you make a calendar request, it will:

   - Open a web browser for OAuth authorization
   - Ask you to sign in to Google and authorize the app
   - Save a `token.pickle` file for future use

3. Test the calendar endpoint:
   ```bash
   curl -X POST http://localhost:8000/tools/calendar.list_events \
        -H "Content-Type: application/json" \
        -d '{"date": "2024-12-18"}'
   ```

## Step 7: Verify Integration

- Check the server logs for "Google Calendar client initialized successfully"
- The calendar widget in your UI should now show real events
- Ask your AI assistant about calendar events: `/calendar` or "What's on my calendar today?"

## Troubleshooting

### Common Issues:

1. **"Credentials file not found"**

   - Verify the file path in `.env`
   - Ensure the JSON file is in the correct location

2. **"OAuth consent screen not configured"**

   - Complete Step 3 above
   - Add your email as a test user

3. **"Access blocked: This app's request is invalid"**

   - Ensure you selected "Desktop application" not "Web application"
   - Try recreating the OAuth client

4. **"Calendar API has not been used"**
   - Enable the Google Calendar API in Step 2
   - Wait a few minutes for propagation

### Security Notes:

- Keep your `google_calendar_credentials.json` file secure
- Never commit it to version control (it's in `.gitignore`)
- The `token.pickle` file contains your access tokens - also keep secure
- Tokens automatically refresh, but may need re-authorization periodically

### Permissions:

The integration requests **read-only** access to your calendars:

- `https://www.googleapis.com/auth/calendar.readonly`
- This allows listing events but not creating/modifying them

## Production Deployment

For production deployment (Railway, etc.):

1. Store credentials as environment variables instead of files
2. Consider using service account authentication for server-to-server access
3. Set up proper OAuth redirect URLs if using web-based authentication

The current implementation works great for development and personal use!
