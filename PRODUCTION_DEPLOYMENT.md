# Google Calendar Production Deployment Guide

## 🚀 **Railway Production Setup**

To deploy Google Calendar integration to Railway, follow these steps:

### **1. Environment Variables in Railway**

Add these environment variables in your Railway project dashboard:

```bash
# Core Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=your-super-secret-key-change-in-production

# External API Keys
WEATHER_API_KEY=your_openweathermap_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key

# Google Calendar Integration
GOOGLE_CALENDAR_CREDENTIALS_JSON={"type":"oauth2","client_id":"...","client_secret":"...","refresh_token":"..."}

# Security & CORS
ALLOWED_ORIGINS=["https://daily-agent-ui.vercel.app","https://web-production-66f9.up.railway.app"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
```

### **2. Google Calendar Credentials**

Since Railway has ephemeral storage, we need to store credentials as environment variables:

1. **Copy your local credentials**:

   ```bash
   # Your google_calendar_credentials.json content
   cat google_calendar_credentials.json
   ```

2. **Set GOOGLE_CALENDAR_CREDENTIALS_JSON** in Railway dashboard with the JSON content

3. **Get your refresh token from token.pickle**:
   ```python
   # Run this locally to extract refresh token
   import pickle
   with open('token.pickle', 'rb') as token:
       creds = pickle.load(token)
       print(f"Refresh token: {creds.refresh_token}")
   ```

### **3. Update Your Railway Environment**

1. **Go to Railway Dashboard** → Your MCP Server Project → Variables
2. **Add all the environment variables** listed above
3. **Deploy** the updated configuration

### **4. Verification**

Test the production deployment:

```bash
# Test Google Calendar endpoint
curl https://your-railway-url.up.railway.app/tools/calendar.list_events \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-08-18"}'

# Check health endpoint
curl https://your-railway-url.up.railway.app/health
```

## 🔒 **Security Notes**

- ✅ Credentials are stored as environment variables (secure)
- ✅ No sensitive files in git repository
- ✅ OAuth refresh tokens enable automatic token renewal
- ✅ CORS configured for production domains

## 🔄 **Token Refresh Handling**

The Google Calendar client automatically handles token refresh using the refresh token stored in environment variables. No manual intervention required.

## 🚨 **Important**

- Never commit `google_calendar_credentials.json` or `token.pickle` to git
- Store all sensitive data in Railway environment variables
- Test the deployment thoroughly before updating AI agent
